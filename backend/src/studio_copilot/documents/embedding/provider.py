"""Embedding profile, bounded OpenAI requests and strict response validation."""

import hashlib
import json
import math
import os
import random
import struct
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from openai import APIConnectionError, APIStatusError, OpenAI

from studio_copilot.documents.operations import current, instrument
from studio_copilot.documents.operations.runtime import estimate


class EmbeddingError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbeddingProfile:
    endpoint: str = "https://api.openai.com/v1"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    input_version: str = "passage-text-v1"

    def __post_init__(self):
        parts = urlsplit(self.endpoint)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            raise ValueError(
                "Embedding endpoint must be an HTTP(S) URL without credentials or query."
            )
        object.__setattr__(self, "endpoint", self.endpoint.rstrip("/"))
        if self.model != "text-embedding-3-small" or self.dimensions != 1536:
            raise ValueError(
                "This preparation version requires text-embedding-3-small, 1536 dimensions."
            )

    @classmethod
    def from_env(cls):
        return cls(
            endpoint=os.environ.get("OPENAI_EMBEDDING_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1",
            model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )

    @property
    def key(self):
        return sha256(json.dumps(asdict(self), sort_keys=True, separators=(",", ":")))

    def vector_key(self, input_sha):
        return sha256(self.key + ":" + input_sha)


def validate_vector(vector):
    if not isinstance(vector, (list, tuple)) or len(vector) != 1536:
        raise EmbeddingError("invalid_vectors", "Embedding dimensions do not match the profile.")
    try:
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError
        # Check the actual single-precision representation that PostgreSQL will store.
        values = struct.unpack("<1536f", struct.pack("<1536f", *vector))
        norm = math.sqrt(math.fsum(value * value for value in values))
        if not math.isfinite(norm) or abs(norm - 1.0) > 0.001:
            raise ValueError
    except (OverflowError, ValueError, struct.error) as error:
        raise EmbeddingError(
            "invalid_vectors", "Embedding values or unit norm are invalid."
        ) from error
    return list(values)


def retry_delay(error, attempt):
    response = getattr(error, "response", None)
    value = response.headers.get("retry-after", "") if response is not None else ""
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = 2**attempt + random.uniform(0, 1)
    if not math.isfinite(delay):
        delay = 2**attempt
    return min(60.0, max(0.0, delay))


class Embedder:
    def __init__(self, profile: EmbeddingProfile, *, client=None, sleeper=time.sleep):
        self.profile, self.sleeper = profile, sleeper
        if client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise EmbeddingError(
                    "configuration", "Configure OPENAI_API_KEY to generate vectors."
                )
            client = OpenAI(base_url=profile.endpoint, timeout=30.0, max_retries=0)
        self.client = client

    @instrument("embedding")
    def embed(self, texts, before_attempt=lambda: None):
        if not 1 <= len(texts) <= 64 or any(not isinstance(t, str) or not t.strip() for t in texts):
            raise EmbeddingError("invalid_input", "Embed 1–64 nonempty text passages per batch.")
        for attempt in range(3):
            control = current()
            ticket = control.budget.reserve(sum(estimate(t) for t in texts))
            # Denied budgets must not increment ownership/experiment attempt counters.
            # A failed ownership gate has sent nothing, so release only that reservation.
            try:
                before_attempt()
            except BaseException:
                ticket.cancel_before_send()
                raise
            ticket.mark_sent()
            started = time.perf_counter()
            control.event("embedding", "budget", attempts=1, retries=int(attempt > 0))
            try:
                response = self.client.embeddings.create(
                    model=self.profile.model,
                    dimensions=self.profile.dimensions,
                    encoding_format="float",
                    input=texts,
                )
            except (APIConnectionError, APIStatusError) as error:
                ticket.finish()
                control.event(
                    "embedding",
                    "api",
                    "failure",
                    seconds=time.perf_counter() - started,
                    error_code="provider_error",
                    unknown_usage_calls=1,
                )
                status = getattr(error, "status_code", None)
                code = getattr(error, "code", None)
                transient = status is None or status in {408, 409, 429} or status >= 500
                if not transient or code == "insufficient_quota" or attempt == 2:
                    raise EmbeddingError(
                        "provider_error", "The embedding request failed."
                    ) from None
                self.sleeper(retry_delay(error, attempt))
                continue
            except Exception:
                ticket.finish()
                control.event(
                    "embedding",
                    "api",
                    "failure",
                    seconds=time.perf_counter() - started,
                    error_code="provider_error",
                    unknown_usage_calls=1,
                )
                raise EmbeddingError("provider_error", "The embedding request failed.") from None
            usage_reported = getattr(getattr(response, "usage", None), "total_tokens", None)
            if type(usage_reported) is int and usage_reported >= 0:
                ticket.finish(input_tokens=usage_reported, output_tokens=0)
            try:
                if (
                    response.model != self.profile.model
                    or not isinstance(response.data, (list, tuple))
                    or len(response.data) != len(texts)
                ):
                    raise ValueError
                indexed = {}
                for item in response.data:
                    if (
                        type(item.index) is not int
                        or not 0 <= item.index < len(texts)
                        or item.index in indexed
                    ):
                        raise ValueError
                    indexed[item.index] = validate_vector(item.embedding)
                usage = response.usage.total_tokens
                if type(usage) is not int or usage < 0:
                    raise ValueError
            except (AttributeError, TypeError, ValueError) as error:
                raise EmbeddingError(
                    "invalid_vectors", "Embedding response shape is invalid."
                ) from error
            ticket.finish(input_tokens=usage, output_tokens=0)
            control.event(
                "embedding",
                "api",
                seconds=time.perf_counter() - started,
                input_tokens=usage,
                output_tokens=0,
            )
            return [indexed[index] for index in range(len(texts))], usage
        raise AssertionError("Unreachable retry state")
