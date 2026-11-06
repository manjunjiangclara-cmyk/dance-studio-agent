"""Independent experiment safety checks use fake vectors, never semantic claims."""

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.retrieval.engine import RetrievalError
from studio_copilot.documents.retrieval.evaluation import evaluate
from studio_copilot.persistence.models import Document, DocumentRevision
from tests.integration.test_embeddings import unit_vector

pytestmark = pytest.mark.integration
CASES = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_cases.json"


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


class CountingFake:
    def __init__(self):
        self.calls = []

    def embed(self, texts, before_attempt=lambda: None):
        before_attempt()
        self.calls.append(list(texts))
        return [unit_vector() for _ in texts], 7 * len(texts)


def fixture_run(engine, tokenizer, *, effective_to=None):
    labels = json.loads(CASES.read_text())
    raw = (CASES.parent / labels["source_file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == labels["source_sha256"]
    with Session(engine) as session, session.begin():
        source = Document(
            title="Fictional retrieval fixture", filename="handbook.md", content=raw.decode()
        )
        session.add(source)
        session.flush()
        document_id = source.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title=source.title,
                filename=source.filename,
                content=source.content,
                byte_size=len(raw),
                sha256=labels["source_sha256"],
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_from=date.fromisoformat(labels["effective_from"]),
                effective_to=effective_to or date.fromisoformat(labels["effective_to"]),
            )
        )
    status = run(engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=CountingFake())
    return UUID(status["run_id"])


def test_injected_vectors_are_not_reported_as_measured_semantic_quality(
    db_engine, tokenizer, monkeypatch
):
    run_id = fixture_run(db_engine, tokenizer)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake = CountingFake()
    report = evaluate(
        db_engine, run_id, CASES, tokenizer, mode="vector", allow_api=True, embedder=fake
    )
    assert fake.calls
    assert report["semantic_quality_measured"] is False
    assert len(report["cases"]) == 40


def test_revision_date_change_is_rejected_before_query_provider_call(db_engine, tokenizer):
    run_id = fixture_run(db_engine, tokenizer, effective_to=date(2027, 12, 30))
    fake = CountingFake()
    with pytest.raises(RetrievalError, match="dates"):
        evaluate(db_engine, run_id, CASES, tokenizer, mode="vector", allow_api=True, embedder=fake)
    assert fake.calls == []


def test_prepare_permission_gate_does_not_touch_engine_or_provider(tokenizer):
    from studio_copilot.documents.retrieval import experiment

    class ForbiddenEngine:
        def connect(self, *args, **kwargs):
            raise AssertionError("Gate touched database")

    with pytest.raises(RetrievalError) as caught:
        experiment.prepare(ForbiddenEngine(), CASES, tokenizer, EmbeddingProfile())
    assert caught.value.code == "api_permission"


def test_prepare_reuses_fixture_and_preserves_unrelated_documents(db_engine, tokenizer):
    from studio_copilot.documents.retrieval import experiment
    from tests.integration.test_embeddings import create_source

    unrelated = create_source(db_engine, content="# Private source\n\nKeep exactly this content.")
    fake = CountingFake()
    first = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
    )
    original_calls = len(fake.calls)
    second = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
    )
    assert second["run_id"] == first["run_id"]
    assert len(fake.calls) == original_calls
    with Session(db_engine) as session:
        documents = session.query(Document).all()
        assert len(documents) == 2
        source = session.get(Document, unrelated)
        assert source.content == "# Private source\n\nKeep exactly this content."
        assert source.current_revision == 1


def test_compare_shares_only_invocation_vectors_and_never_writes(db_engine, tokenizer):
    from sqlalchemy import event

    from studio_copilot.documents.retrieval import experiment

    prepared = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )
    statements = []

    def observe(connection, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())

    fake = CountingFake()
    event.listen(db_engine, "before_cursor_execute", observe)
    try:
        first = experiment.compare(
            db_engine,
            prepared["run_id"],
            CASES,
            tokenizer,
            allow_api=True,
            embedder=fake,
            document_vectors_verified=True,
        )
        second = experiment.compare(
            db_engine,
            prepared["run_id"],
            CASES,
            tokenizer,
            allow_api=True,
            embedder=fake,
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", observe)
    assert len(fake.calls) == 76
    for report in (first, second):
        assert report["complete"] is True
        assert report["semantic_quality_measured"] is False
        assert report["question_embedding"]["requests"] == 38
        assert report["question_embedding"]["attempts"] == 38
        assert report["question_embedding"]["cache_hits"] == 38
        assert report["question_embedding"]["reported_tokens"] == 38 * 7
        assert report["modes"]["hybrid"]["target_met"] is False
        assert sum(c["reported_tokens"] for c in report["modes"]["hybrid"]["cases"]) == 0
        assert sum(c["reported_tokens"] for c in report["modes"]["vector"]["cases"]) == 38 * 7
    assert statements
    assert all(s.startswith(("SELECT", "WITH", "SET TRANSACTION READ ONLY")) for s in statements)
    assert "SET TRANSACTION READ ONLY" in statements


def test_compare_profile_mismatch_fails_before_any_question_requests(
    db_engine, tokenizer, monkeypatch
):
    from studio_copilot.documents.retrieval import experiment

    prepared = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )
    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://incompatible.example/v1")
    fake = CountingFake()
    with pytest.raises(RetrievalError) as caught:
        experiment.compare(
            db_engine,
            prepared["run_id"],
            CASES,
            tokenizer,
            allow_api=True,
            embedder=fake,
        )
    assert caught.value.code == "profile_mismatch"
    assert fake.calls == []


def test_provider_failure_does_not_publish_successful_hybrid_quality(db_engine, tokenizer):
    from studio_copilot.documents.embedding.provider import EmbeddingError
    from studio_copilot.documents.retrieval import experiment

    prepared = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )

    class Unavailable:
        def embed(self, texts, before_attempt=lambda: None):
            before_attempt()
            raise EmbeddingError("provider_error", "Unavailable test provider")

    report = experiment.compare(
        db_engine,
        prepared["run_id"],
        CASES,
        tokenizer,
        allow_api=True,
        embedder=Unavailable(),
        document_vectors_verified=True,
    )
    assert report["complete"] is False
    assert report["semantic_quality_measured"] is False
    hybrid = report["modes"]["hybrid"]
    assert hybrid["complete"] is False
    assert hybrid["target_met"] is False
    assert any(c.get("failed") for c in hybrid["cases"])


def test_one_failed_question_retains_denominator_and_does_not_poison_other_cache_entries(
    db_engine, tokenizer
):
    from studio_copilot.documents.embedding.provider import EmbeddingError
    from studio_copilot.documents.retrieval import experiment

    prepared = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )
    failed_case = json.loads(CASES.read_text())["cases"][0]

    class OneQuestionFails(CountingFake):
        def embed(self, texts, before_attempt=lambda: None):
            if texts == [failed_case["query"]]:
                before_attempt()
                self.calls.append(list(texts))
                raise EmbeddingError("provider_error", "Question unavailable")
            return super().embed(texts, before_attempt)

    provider = OneQuestionFails()
    report = experiment.compare(
        db_engine, prepared["run_id"], CASES, tokenizer, allow_api=True, embedder=provider
    )
    assert report["complete"] is False
    assert report["semantic_quality_measured"] is False
    # Failed vectors are retried in hybrid; only successful query vectors are reused.
    assert report["question_embedding"]["requests"] == 39
    assert report["question_embedding"]["attempts"] == 39
    assert report["question_embedding"]["cache_hits"] == 37
    assert report["question_embedding"]["reported_tokens"] == 37 * 7
    for mode in ("vector", "hybrid"):
        result = report["modes"][mode]
        failures = [case for case in result["cases"] if case.get("failed")]
        assert len(failures) == 1
        assert failures[0]["id"] == failed_case["id"]
        assert failures[0]["final_at_6"]["recall"] == 0
        tuning = [c for c in result["cases"] if c["split"] == "tuning" and c["answerable"]]
        assert result["summaries"]["tuning"]["answerable"] == len(tuning)
        assert result["summaries"]["tuning"]["final_at_6"]["recall"] == pytest.approx(
            sum(c["final_at_6"]["recall"] for c in tuning) / len(tuning)
        )


def test_prepare_refuses_changed_document_without_overwriting_it(db_engine, tokenizer):
    from studio_copilot.documents.retrieval import experiment
    from tests.integration.test_embeddings import create_source

    unrelated = create_source(db_engine, content="# Existing teacher notes\n\nPreserve me.")
    first = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )
    with Session(db_engine) as session, session.begin():
        document = session.get(Document, UUID(first["document_id"]))
        document.current_revision = 2
        document.content = "Teacher has replaced this document."
    fake = CountingFake()
    with pytest.raises(RetrievalError) as caught:
        experiment.prepare(
            db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
        )
    assert caught.value.code == "fixture_conflict"
    assert fake.calls == []
    with Session(db_engine) as session:
        document = session.get(Document, UUID(first["document_id"]))
        assert document.current_revision == 2
        assert document.content == "Teacher has replaced this document."
        assert (
            session.get(Document, unrelated).content == "# Existing teacher notes\n\nPreserve me."
        )
