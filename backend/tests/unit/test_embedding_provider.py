"""Embedding batches use fake providers; these tests make no paid model calls."""

import hashlib
import math
import struct
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIConnectionError, APIStatusError

from studio_copilot.documents.embedding import provider
from studio_copilot.documents.embedding.provider import (
    Embedder,
    EmbeddingError,
    EmbeddingProfile,
    retry_delay,
    validate_vector,
)


def vector(index=0, magnitude=1.0):
    values = [0.0] * 1536
    values[index] = magnitude
    return values


def response(*vectors, indices=None, model="text-embedding-3-small", usage=17):
    indices = list(range(len(vectors))) if indices is None else indices
    return SimpleNamespace(
        model=model,
        data=[
            SimpleNamespace(index=index, embedding=value) for index, value in zip(indices, vectors)
        ],
        usage=SimpleNamespace(total_tokens=usage),
    )


def embedder(*results, sleeper=None):
    create = Mock(side_effect=results)
    client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    return Embedder(EmbeddingProfile(), client=client, sleeper=sleeper or Mock()), create


def status_error(status, headers=None, code=None):
    request = httpx.Request("POST", "https://embedding.invalid/v1/embeddings")
    result = httpx.Response(status, request=request, headers=headers)
    return APIStatusError("private provider error", response=result, body={"code": code})


def test_profile_identity_covers_endpoint_input_version_and_exact_input_hash():
    profile = EmbeddingProfile(endpoint="https://api.openai.com/v1/")
    assert profile.endpoint == "https://api.openai.com/v1"
    assert profile.key == EmbeddingProfile().key
    for changed in (
        replace(profile, endpoint="https://other.example/v1"),
        replace(profile, input_version="passage-text-v2"),
    ):
        assert changed.key != profile.key
        assert changed.vector_key("a" * 64) != profile.vector_key("a" * 64)
    raw_hash = hashlib.sha256("Café\r\n".encode()).hexdigest()
    changed_hash = hashlib.sha256("Café\n".encode()).hexdigest()
    assert profile.vector_key(raw_hash) == profile.vector_key(raw_hash)
    assert profile.vector_key(raw_hash) != profile.vector_key(changed_hash)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"endpoint": "file:///tmp/provider"},
        {"endpoint": "https://secret:password@provider.example/v1"},
        {"endpoint": "https://provider.example/v1?api_key=secret"},
        {"endpoint": "https://provider.example/v1#secret"},
        {"model": "different-model"},
        {"dimensions": 3072},
    ],
)
def test_unsupported_or_credential_bearing_profiles_are_rejected(kwargs):
    with pytest.raises(ValueError):
        EmbeddingProfile(**kwargs)


def test_environment_endpoint_precedence_is_part_of_profile_identity(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://general.example/v1")
    monkeypatch.delenv("OPENAI_EMBEDDING_BASE_URL", raising=False)
    assert EmbeddingProfile.from_env().endpoint == "https://general.example/v1"
    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://specific.example/v1")
    assert EmbeddingProfile.from_env().endpoint == "https://specific.example/v1"


def test_actual_client_uses_profile_endpoint_timeout_and_disables_sdk_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    constructor = Mock()
    monkeypatch.setattr(provider, "OpenAI", constructor)
    profile = EmbeddingProfile(endpoint="https://specific.example/v1")
    Embedder(profile)
    constructor.assert_called_once_with(base_url=profile.endpoint, timeout=30.0, max_retries=0)


def test_missing_api_key_fails_before_constructing_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    constructor = Mock()
    monkeypatch.setattr(provider, "OpenAI", constructor)
    with pytest.raises(EmbeddingError) as caught:
        Embedder(EmbeddingProfile())
    assert caught.value.code == "configuration"
    constructor.assert_not_called()


def test_response_indices_restore_input_order_and_text_is_sent_exactly():
    texts = ["Title\nHeading\nCafé\r\n", "<|endoftext|> is literal source text."]
    subject, create = embedder(response(vector(1), vector(0), indices=[1, 0], usage=31))
    before = Mock()
    vectors, usage = subject.embed(texts, before_attempt=before)
    assert vectors == [vector(0), vector(1)]
    assert usage == 31
    before.assert_called_once_with()
    create.assert_called_once_with(
        model="text-embedding-3-small",
        dimensions=1536,
        encoding_format="float",
        input=texts,
    )


@pytest.mark.parametrize("texts", [[], ["text"] * 65, [""], [" \t\n"], [None], [42]])
def test_invalid_inputs_fail_before_callback_or_paid_request(texts):
    subject, create = embedder()
    before = Mock()
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(texts, before_attempt=before)
    assert caught.value.code == "invalid_input"
    before.assert_not_called()
    create.assert_not_called()


def test_sixty_four_passages_are_allowed():
    subject, create = embedder(response(*[vector()] * 64))
    vectors, _ = subject.embed(["text"] * 64)
    assert len(vectors) == 64 and create.call_count == 1


@pytest.mark.parametrize("indices", [[0, 0], [-1, 1], [0, 2], [0, True], [0, 1.0], [0, None]])
def test_invalid_indices_are_not_silently_zipped_to_inputs(indices):
    subject, create = embedder(response(vector(), vector(1), indices=indices))
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(["one", "two"])
    assert caught.value.code == "invalid_vectors" and create.call_count == 1


@pytest.mark.parametrize(
    "result",
    [
        response(vector(), model="unexpected-model"),
        response(),
        response(vector(), vector(1)),
        response(vector(), usage=-1),
        response(vector(), usage=True),
        response(vector(), usage=1.0),
    ],
)
def test_model_count_or_usage_mismatch_is_rejected_without_retry(result):
    subject, create = embedder(result)
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(["one"])
    assert caught.value.code == "invalid_vectors" and create.call_count == 1


@pytest.mark.parametrize(
    "result",
    [
        None,
        SimpleNamespace(),
        SimpleNamespace(model="text-embedding-3-small", data=None),
        SimpleNamespace(model="text-embedding-3-small", data=[None]),
        SimpleNamespace(model="text-embedding-3-small", data=[SimpleNamespace()]),
        SimpleNamespace(model="text-embedding-3-small", data=response(vector()).data, usage=None),
        SimpleNamespace(
            model="text-embedding-3-small", data=response(vector()).data, usage=SimpleNamespace()
        ),
    ],
)
def test_malformed_response_shapes_use_sanitized_embedding_errors(result):
    subject, create = embedder(result)
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(["private source text"])
    assert caught.value.code == "invalid_vectors"
    assert "private source text" not in str(caught.value)
    assert create.call_count == 1


@pytest.mark.parametrize(
    "values",
    [
        None,
        [1.0] * 1535,
        [1.0] * 1537,
        vector(magnitude=0),
        vector(magnitude=0.998),
        vector(magnitude=1.002),
    ],
)
def test_wrong_dimensions_zero_or_off_unit_vectors_are_rejected(values):
    with pytest.raises(EmbeddingError) as caught:
        validate_vector(values)
    assert caught.value.code == "invalid_vectors"


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 1e39, True, "1", None])
def test_invalid_numeric_values_cannot_reach_pgvector_storage(bad):
    values = vector()
    values[10] = bad
    with pytest.raises(EmbeddingError) as caught:
        validate_vector(values)
    assert caught.value.code == "invalid_vectors"


def test_float32_storage_representation_is_returned_without_normalizing():
    values = vector(magnitude=0.9995)
    values[1] = 1e-9
    actual = validate_vector(values)
    assert actual[0] == struct.unpack("<f", struct.pack("<f", 0.9995))[0]
    assert actual[1] == struct.unpack("<f", struct.pack("<f", 1e-9))[0]
    assert actual[0] != 1.0


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
def test_transient_errors_allow_exactly_three_total_attempts(status):
    sleeper = Mock()
    subject, create = embedder(*[status_error(status)] * 3, sleeper=sleeper)
    before = Mock()
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(["private input"], before_attempt=before)
    assert caught.value.code == "provider_error"
    assert "private" not in str(caught.value)
    assert create.call_count == before.call_count == 3
    assert sleeper.call_count == 2
    assert all(0 <= call.args[0] <= 60 for call in sleeper.call_args_list)


def test_connection_errors_retry_and_successful_usage_is_returned_once():
    request = httpx.Request("POST", "https://embedding.invalid/v1/embeddings")
    failure = APIConnectionError(request=request)
    sleeper = Mock()
    subject, create = embedder(failure, response(vector(), usage=29), sleeper=sleeper)
    before = Mock()
    assert subject.embed(["source"], before_attempt=before) == ([vector()], 29)
    assert create.call_count == before.call_count == 2
    sleeper.assert_called_once()


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_permanent_http_errors_fail_without_retry(status):
    sleeper = Mock()
    subject, create = embedder(status_error(status), sleeper=sleeper)
    with pytest.raises(EmbeddingError) as caught:
        subject.embed(["private source"])
    assert caught.value.code == "provider_error" and create.call_count == 1
    sleeper.assert_not_called()


def test_insufficient_quota_is_not_retried_even_with_http429():
    sleeper = Mock()
    subject, create = embedder(status_error(429, code="insufficient_quota"), sleeper=sleeper)
    with pytest.raises(EmbeddingError):
        subject.embed(["source"])
    assert create.call_count == 1
    sleeper.assert_not_called()


def test_ownership_callback_failure_prevents_initial_or_retried_paid_attempt():
    subject, create = embedder(response(vector()))
    failure = EmbeddingError("lease_lost", "Lease expired")
    before = Mock(side_effect=failure)
    with pytest.raises(EmbeddingError, match="Lease expired"):
        subject.embed(["source"], before_attempt=before)
    create.assert_not_called()

    subject, create = embedder(status_error(503), response(vector()))
    before = Mock(side_effect=[None, failure])
    with pytest.raises(EmbeddingError, match="Lease expired"):
        subject.embed(["source"], before_attempt=before)
    assert create.call_count == 1 and before.call_count == 2


@pytest.mark.parametrize("value,expected", [("12.5", 12.5), ("99999", 60.0), ("-2", 0.0)])
def test_retry_after_seconds_are_bounded(value, expected):
    assert retry_delay(status_error(429, {"Retry-After": value}), 0) == expected


@pytest.mark.parametrize("value", ["NaN", "Infinity", "bad header"])
def test_nonfinite_or_invalid_retry_after_uses_bounded_delay(value):
    assert 0 <= retry_delay(status_error(429, {"Retry-After": value}), 1) <= 60


def test_retry_after_http_date_is_supported():
    value = format_datetime(datetime.now(UTC) + timedelta(seconds=25), usegmt=True)
    assert 20 <= retry_delay(status_error(429, {"Retry-After": value}), 0) <= 25
