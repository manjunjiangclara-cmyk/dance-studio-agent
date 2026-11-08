"""Cache hits never replace PostgreSQL source eligibility or explicit API opt-in."""

import pytest
from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from studio_copilot.documents.operations import task
from studio_copilot.documents.retrieval.engine import RetrievalError
from studio_copilot.persistence.models import Document, EmbeddingRun
from tests.integration.test_retrieval import (
    LocalVectors,
    prepared,
    retrieve,
)
from tests.integration.test_retrieval import (
    tokenizer as tokenizer,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_external_telemetry(monkeypatch):
    monkeypatch.setenv("STUDIO_LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


@pytest.mark.parametrize("mutation", ["delete", "incomplete"])
def test_cached_query_revalidates_source_before_returning_results(db_engine, tokenizer, mutation):
    document_id, run_id = prepared(db_engine, tokenizer, "# Attendance\nCancellations need notice.")
    provider = LocalVectors(db_engine)
    with task():
        first = retrieve(
            db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=provider
        )
        second = retrieve(
            db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=provider
        )
        assert first["results"] and second["results"]
        assert len(provider.calls) == 1
        with Session(db_engine) as session:
            if mutation == "delete":
                session.execute(delete(Document).where(Document.id == document_id))
            else:
                session.execute(
                    update(EmbeddingRun).where(EmbeddingRun.id == run_id).values(status="failed")
                )
            session.commit()
        with pytest.raises(RetrievalError) as caught:
            retrieve(
                db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=provider
            )
        assert caught.value.code == (
            "source_missing" if mutation == "delete" else "source_incomplete"
        )
        assert len(provider.calls) == 1


def test_cached_query_does_not_bypass_explicit_api_permission(db_engine, tokenizer):
    _, run_id = prepared(db_engine, tokenizer, "# Attendance\nCancellations need notice.")
    provider = LocalVectors(db_engine)
    with task():
        retrieve(db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=provider)
        with pytest.raises(RetrievalError) as caught:
            retrieve(
                db_engine, tokenizer, [run_id], mode="vector", allow_api=False, embedder=provider
            )
        assert caught.value.code == "api_permission"
        assert len(provider.calls) == 1


def test_embedding_preflight_uses_same_input_reservation_as_provider(db_engine, tokenizer):
    from studio_copilot.documents.chunking import Chunker, load_revision
    from studio_copilot.documents.embedding import pipeline
    from studio_copilot.documents.embedding.provider import EmbeddingProfile
    from studio_copilot.documents.operations import Limits, OperationsError
    from studio_copilot.documents.operations.runtime import Task, estimate
    from tests.integration.test_embeddings import create_source

    document_id = create_source(
        db_engine, "# Attendance\nCancellations require twenty-four hours notice.\n"
    )
    inputs = {
        record["text_sha256"]: record["text"]
        for record in Chunker(load_revision(db_engine, document_id, 1), tokenizer).records()
        if record["kind"] == "passage"
    }
    required = sum(estimate(text) for text in inputs.values())
    control = Task(limits=Limits(max_estimated_input_tokens=required - 1))
    with task(control=control), pytest.raises(OperationsError) as caught:
        pipeline.plan(db_engine, document_id, 1, tokenizer, EmbeddingProfile())
    assert caught.value.code == "budget_exceeded"
    assert control.budget.snapshot()["attempts"] == 0
