"""Opt-in document answers for the existing, authenticated teacher-review workflow.

Configuration is a deployment allowlist, not a publication registry. Uploads and
completed indexing alone never enable a source. No provider runs inside a DB transaction.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from threading import Lock
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.agent.privacy import StudentPrivacy
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.embedding.provider import Embedder, EmbeddingProfile
from studio_copilot.documents.generation.engine import answer
from studio_copilot.documents.generation.evidence import (
    VERSION,
    make_block,
    seal_artifact,
    validate_artifact,
)
from studio_copilot.documents.generation.provider import GenerationProvider
from studio_copilot.documents.operations import Limits, instrument, task
from studio_copilot.documents.reranking.capture import capture
from studio_copilot.documents.reranking.runtime import LocalReranker
from studio_copilot.documents.retrieval.engine import pack_from_records
from studio_copilot.persistence.models import Document, DocumentRevision, EmbeddingRun

ZONE = ZoneInfo("Australia/Melbourne")
MAX_QUESTIONS = 8
L6 = "cross-encoder/ms-marco-MiniLM-L6-v2"
_inference_lock = Lock()
_resources_lock = Lock()
ERROR_CODES = {
    "configuration",
    "source_missing",
    "source_conflict",
    "source_changed",
    "source_revoked",
    "profile_mismatch",
    "invalid_evidence",
    "retrieval_failed",
    "reranking_failed",
    "generation_failed",
    "budget_exceeded",
    "question_limit",
    "provider_error",
}


def safe_error(error):
    code = getattr(error, "code", None)
    return code if isinstance(code, str) and code in ERROR_CODES else "document_answer_unavailable"


class Providers:
    """Lazy task-owned SDK clients; empty evidence requires neither key nor client."""

    real_provider = True

    def __init__(self):
        self.embedding = self.writer = None
        self.model = os.environ.get("OPENAI_MODEL")

    @property
    def calls(self):
        return self.writer.calls if self.writer else []

    def embed(self, texts):
        if self.embedding is None:
            self.embedding = Embedder(EmbeddingProfile.from_env())
        return self.embedding.embed(texts)

    def generate(self, payload):
        if self.writer is None:
            self.writer = GenerationProvider()
        return self.writer.generate(payload)

    def close(self):
        for provider in (self.embedding, self.writer):
            if provider is not None:
                try:
                    provider.client.close()
                except Exception:
                    pass  # Cleanup must not erase completed results or leak exception text.


@contextmanager
def providers(embedder, writer):
    owned = Providers()
    try:
        yield embedder if embedder is not None else owned, writer if writer is not None else owned
    finally:
        owned.close()


class OnlineError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__("Document answers are unavailable; teacher review is required.")


@dataclass(frozen=True)
class Configuration:
    run_ids: tuple[UUID, ...]
    tokenizer_cache: Path
    reranker_cache: Path

    @classmethod
    def from_env(cls):
        enabled = os.environ.get("STUDIO_DOCUMENT_ANSWERS", "false").lower()
        if enabled == "false":
            return None
        if enabled != "true":
            raise OnlineError("configuration")
        try:
            raw = os.environ["STUDIO_DOCUMENT_RUN_IDS"].split(",")
            runs = tuple(UUID(value.strip()) for value in raw)
            if not 1 <= len(runs) <= 100 or len(set(runs)) != len(runs):
                raise ValueError
            return cls(
                runs,
                Path(os.environ["STUDIO_TOKENIZER_CACHE"]),
                Path(os.environ["STUDIO_RERANKER_CACHE"]),
            )
        except (KeyError, ValueError):
            raise OnlineError("configuration") from None


@lru_cache(maxsize=1)
def _resources(tokenizer_cache, reranker_cache):
    # Both constructors verify prepared local assets; neither downloads anything.
    return Tokenizer(tokenizer_cache), LocalReranker(reranker_cache, L6)


def resources(tokenizer_cache, reranker_cache):
    with _resources_lock:
        return _resources(tokenizer_cache, reranker_cache)


@instrument("reranking")
def rank(reranker, question, candidates):
    with _inference_lock:
        return reranker.rank(question, candidates) if candidates else []


def source_rows(db, run_ids, as_of, *, lock=False):
    statement = (
        select(EmbeddingRun, Document, DocumentRevision)
        .join(Document, Document.id == EmbeddingRun.document_id)
        .join(
            DocumentRevision,
            (DocumentRevision.document_id == EmbeddingRun.document_id)
            & (DocumentRevision.revision == EmbeddingRun.revision),
        )
        .where(EmbeddingRun.id.in_(run_ids))
        .order_by(Document.id, EmbeddingRun.id)
    )
    if lock:
        # Approval holds these locks through response commit. Deletion/replacement
        # cannot invalidate a source in the check-to-commit interval.
        statement = statement.with_for_update(read=True, of=(Document, EmbeddingRun))
    rows = db.execute(statement).all()
    if len(rows) != len(run_ids):
        raise OnlineError("source_missing")
    if len({document.id for _, document, _ in rows}) != len(rows):
        raise OnlineError("source_conflict")
    if len({run.profile_hash for run, _, _ in rows}) > 1:
        raise OnlineError("profile_mismatch")
    for run, document, revision in rows:
        try:
            if EmbeddingProfile(**run.profile).key != run.profile_hash:
                raise ValueError
        except (TypeError, ValueError):
            raise OnlineError("profile_mismatch") from None
        if (
            run.status != "complete"
            or not run.prepared
            or revision.ingestion_status != "ready"
            or document.current_revision != revision.revision
        ):
            raise OnlineError("source_changed")
    return rows


def applicable(revision, as_of):
    return not (
        (revision.effective_from and as_of < revision.effective_from)
        or (revision.effective_to and as_of > revision.effective_to)
    )


def identity(run, revision):
    return dict(
        run_id=str(run.id),
        document_id=str(run.document_id),
        revision=run.revision,
        sha256=revision.sha256,
        profile_hash=run.profile_hash,
    )


def build_artifact(engine, config, question, case_id, as_of, packed, tokenizer):
    sources, by_run, identities = [], {}, []
    selected = {UUID(item["run_id"]) for item in packed}
    with Session(engine) as db:
        for run, _, revision in source_rows(db, config.run_ids, as_of):
            if run.id not in selected:
                continue
            if not applicable(revision, as_of):
                raise OnlineError("source_changed")
            source = dict(
                document_id=str(run.document_id),
                revision=run.revision,
                title=revision.title,
                filename=revision.filename,
                text=revision.content,
                sha256=revision.sha256,
                effective_from=revision.effective_from.isoformat()
                if revision.effective_from
                else None,
                effective_to=revision.effective_to.isoformat() if revision.effective_to else None,
            )
            sources.append(source)
            by_run[str(run.id)] = source
            identities.append(identity(run, revision))
    blocks = []
    for item in packed:
        block = make_block(
            by_run[item["run_id"]],
            item["chunk_id"],
            item["kind"],
            item["prefix"],
            item["source_spans"],
        )
        if block["text"] != item["text"]:
            raise OnlineError("invalid_evidence")
        blocks.append(block)
    artifact = seal_artifact(
        dict(
            version=VERSION,
            case_id=case_id,
            question=question,
            as_of=as_of.isoformat(),
            variant="actual",
            sources=sources,
            blocks=blocks,
        )
    )
    return validate_artifact(artifact, tokenizer), identities


def check_identities(db, config, identities, as_of, *, lock=False):
    ids = {UUID(item["run_id"]) for item in identities}
    if not ids <= set(config.run_ids):
        raise OnlineError("source_revoked")
    rows = source_rows(db, ids, as_of, lock=lock)
    actual = {str(run.id): identity(run, revision) for run, _, revision in rows}
    for expected in identities:
        if actual[expected["run_id"]] != expected:
            raise OnlineError("source_changed")
    if any(not applicable(revision, as_of) for _, _, revision in rows):
        raise OnlineError("source_changed")


def question_answer(
    engine, config, question, case_id, as_of, tokenizer, reranker, *, embedder=None, provider=None
):
    snapshot = capture(
        engine, config.run_ids, question, as_of, tokenizer, allow_api=True, embedder=embedder
    )
    if snapshot["degraded"]:
        raise OnlineError("retrieval_failed")
    candidates = snapshot["candidates"]
    # CPU inference is bounded and serialized within this process, not in a DB transaction.
    ranked = rank(reranker, question, candidates)
    if len(ranked) != len(candidates) or {r["text_sha256"] for r in ranked} != {
        c["text_sha256"] for c in candidates
    }:
        raise OnlineError("reranking_failed")
    packed, _, warnings = pack_from_records(ranked[:6], snapshot["parents"], tokenizer)
    artifact, identities = build_artifact(
        engine, config, question, case_id, as_of, packed, tokenizer
    )
    result = answer(artifact, tokenizer, allow_api=True, provider=provider)
    if result["execution_status"] != "completed":
        code = result.get("error_code")
        raise OnlineError(code if code in ERROR_CODES else "generation_failed")
    with Session(engine) as db:
        check_identities(db, config, identities, as_of)
    citations = [citation for claim in result["claims"] for citation in claim["citations"]]
    references = list(dict.fromkeys("document:" + c["evidence_id"] for c in citations))
    return dict(
        question_id=case_id,
        status=result["status"],
        answer=result["answer"],
        claims=result["claims"],
        missing_information=result["missing_information"],
        reason_code=result["reason_code"],
        references=references,
        sources=identities,
        as_of=as_of.isoformat(),
        artifact_sha256=artifact["artifact_sha256"],
        # Retain only the actual provided evidence, not entire source documents.
        evidence=[dict(block) for block in artifact["blocks"]],
        warnings=warnings,
        model=result["model"],
        verification_applied=False,
        prompt_version="grounded-generation-v1",
    )


def gather(
    engine, state, *, config=None, tokenizer=None, reranker=None, embedder=None, provider=None
):
    """None means disabled. Every enabled attempt returns reviewable evidence, including errors."""
    if state.get("flow") not in {"enquiry", "teacher_handoff"}:
        return None
    try:
        config = config or Configuration.from_env()
    except OnlineError:
        config = False
    if config is None:
        return None
    evidence, warnings = [], []
    questions = list(dict.fromkeys(state["interpretation"].get("questions", [])))
    as_of = (
        datetime.fromisoformat(state["context"]["source"]["occurred_at"]).astimezone(ZONE).date()
    )
    privacy = StudentPrivacy(state["context"].get("student", {}))
    resolved = {str(item["question_id"]) for item in state.get("question_resolutions", [])}
    # Eight questions, each with embedding attempts and one no-retry generation.
    # This budget covers document calls, not the pre-existing routing/interpreter.
    with (
        task(Limits(32, 1_000_000, 32_000)) as control,
        providers(embedder, provider) as (
            embedder,
            provider,
        ),
    ):
        initialization_error = "configuration" if config is False else None
        if not initialization_error and any(
            state["interpretation"]["question_ids"][q] not in resolved for q in questions
        ):
            try:
                with Session(engine) as db:
                    source_rows(db, config.run_ids, as_of)
                if tokenizer is None or reranker is None:
                    tokenizer, reranker = resources(config.tokenizer_cache, config.reranker_cache)
            except Exception as error:
                initialization_error = safe_error(error)
        for index, question in enumerate(questions):
            question_id = state["interpretation"]["question_ids"][question]
            if question_id in resolved:
                continue
            try:
                if initialization_error:
                    raise OnlineError(initialization_error)
                if control.budget.exhausted:
                    raise OnlineError("budget_exceeded")
                if index >= MAX_QUESTIONS:
                    raise OnlineError("question_limit")
                result = question_answer(
                    engine,
                    config,
                    privacy.redact(question),
                    question_id,
                    as_of,
                    tokenizer,
                    reranker,
                    embedder=embedder,
                    provider=provider,
                )
                # Quotes and their ranges remain byte-for-byte source text. Identity
                # aliases in answers stay neutral rather than restoring facts from a model.
            except Exception as error:
                code = safe_error(error)
                control.event(
                    "generation",
                    "operation",
                    "failure",
                    error_code="budget_exceeded"
                    if code == "budget_exceeded"
                    else "operation_failed",
                )
                result = dict(
                    question_id=question_id,
                    status="failed",
                    answer="",
                    references=[],
                    claims=[],
                    sources=[],
                    error_code=code,
                )
                warnings.append(
                    "Document answers could not be verified; teacher review is required."
                )
            evidence.append(
                dict(
                    tool="document_answer",
                    arguments={},
                    finding=question,
                    result=dict(result, question=question),
                )
            )
        if evidence:
            evidence[-1]["result"]["operations"] = control.budget.snapshot()
    return dict(evidence=evidence, warnings=list(dict.fromkeys(warnings)))


def require_current_sources(db, run):
    """Approval guard also runs when the feature was disabled after creating a draft."""
    entries = [item["result"] for item in run.evidence if item.get("tool") == "document_answer"]
    used = set(run.draft_details.get("references", []))
    entries = [item for item in entries if used.intersection(item.get("references", []))]
    if not entries:
        return
    config = Configuration.from_env()
    if config is None:
        raise OnlineError("source_revoked")
    today = datetime.now(ZONE).date()
    for item in entries:
        check_identities(db, config, item["sources"], today, lock=True)
