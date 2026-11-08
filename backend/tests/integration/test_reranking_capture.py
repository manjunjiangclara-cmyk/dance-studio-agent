"""Independent PostgreSQL capture consistency tests, with fake embeddings only."""

import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, text, update
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.retrieval.engine import RetrievalError, search
from studio_copilot.persistence.models import Document, DocumentRevision
from tests.integration.test_embeddings import create_source, unit_vector

pytestmark = pytest.mark.integration
AS_OF = date(2026, 6, 1)


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


class FakeEmbedder:
    def __init__(self, callback=lambda: None):
        self.calls = []
        self.callback = callback

    def embed(self, texts, before_attempt=lambda: None):
        self.callback()
        before_attempt()
        self.calls.append(list(texts))
        return [unit_vector() for _ in texts], len(texts)


@pytest.fixture
def prepared(db_engine, tokenizer):
    # Distinct short chapters produce >6 passages without excessive test cost.
    content = "\n\n".join(
        f"# Policy {number}\n\nAmber dancers use entrance {number}. "
        f"The numbered permit {number} is checked before class."
        for number in range(12)
    )
    document_id = create_source(db_engine, content=content)
    prepared = run(
        db_engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=FakeEmbedder()
    )
    assert prepared["status"] == "complete"
    return document_id, prepared["run_id"]


def test_capture_api_gate_does_not_touch_database(tokenizer):
    from studio_copilot.documents.reranking.capture import capture

    class ForbiddenEngine:
        def connect(self):
            pytest.fail("Database accessed before API authorization")

    with pytest.raises(RetrievalError) as caught:
        capture(ForbiddenEngine(), [uuid4()], "question", AS_OF, tokenizer)
    assert caught.value.code == "api_permission"


def test_capture_is_read_only_keeps_full_union_and_matches_default_top_six(
    db_engine, tokenizer, prepared
):
    from studio_copilot.documents.reranking.capture import capture

    document_id, run_id = prepared
    statements, transactions = [], set()

    def start(connection):
        transactions.add(id(connection))

    def finish(connection):
        transactions.discard(id(connection))

    def observe(connection, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())

    def outside_transaction():
        assert not transactions, "Query API called while capture held a database transaction"

    provider = FakeEmbedder(outside_transaction)
    event.listen(db_engine, "begin", start)
    event.listen(db_engine, "commit", finish)
    event.listen(db_engine, "rollback", finish)
    event.listen(db_engine, "before_cursor_execute", observe)
    try:
        result = capture(
            db_engine,
            [run_id],
            "Amber entrance permit",
            AS_OF,
            tokenizer,
            allow_api=True,
            embedder=provider,
        )
    finally:
        event.remove(db_engine, "begin", start)
        event.remove(db_engine, "commit", finish)
        event.remove(db_engine, "rollback", finish)
        event.remove(db_engine, "before_cursor_execute", observe)
    assert len(provider.calls) == 1
    assert 6 < len(result["candidates"]) <= 40
    assert all(s.startswith(("SELECT", "WITH", "SET TRANSACTION READ ONLY")) for s in statements)
    assert "SET TRANSACTION READ ONLY" in statements
    assert len({item["text_sha256"] for item in result["candidates"]}) == len(result["candidates"])
    for item in result["candidates"]:
        assert item["document_id"] == str(document_id)
        assert item["revision"] == 1
        assert item["source_spans"]
        key = f"{item['run_id']}:{item['parent_id']}"
        assert result["parents"][key]["kind"] == "parent"
    ordinary = search(
        db_engine,
        [run_id],
        "Amber entrance permit",
        AS_OF,
        tokenizer,
        allow_api=True,
        embedder=FakeEmbedder(),
    )
    assert len(ordinary["results"]) == 6
    assert [item["text_sha256"] for item in result["candidates"][:6]] == [
        item["text_sha256"] for item in ordinary["results"]
    ]


def test_capture_out_of_date_performs_no_query_embedding(db_engine, tokenizer, prepared):
    from studio_copilot.documents.reranking.capture import capture

    fake = FakeEmbedder()
    result = capture(
        db_engine,
        [prepared[1]],
        "Amber entrance permit",
        date(2029, 1, 1),
        tokenizer,
        allow_api=True,
        embedder=fake,
    )
    assert result["candidates"] == []
    assert result["parents"] == {}
    assert fake.calls == []


def test_deletion_during_query_embedding_cannot_return_stale_capture(
    db_engine, tokenizer, prepared
):
    from studio_copilot.documents.reranking.capture import capture

    def remove_source():
        with db_engine.begin() as connection:
            connection.execute(delete(Document).where(Document.id == prepared[0]))

    with pytest.raises(RetrievalError) as caught:
        capture(
            db_engine,
            [prepared[1]],
            "Amber permit",
            AS_OF,
            tokenizer,
            allow_api=True,
            embedder=FakeEmbedder(remove_source),
        )
    assert caught.value.code == "source_missing"


def test_replacement_during_query_embedding_keeps_explicit_immutable_revision(
    db_engine, tokenizer, prepared
):
    import hashlib

    from studio_copilot.documents.reranking.capture import capture

    def replace_source():
        raw = "# Changed\n\nDifferent policy after replacement."
        with Session(db_engine) as session:
            session.add(
                DocumentRevision(
                    document_id=prepared[0],
                    revision=2,
                    title="Updated",
                    filename="policy.md",
                    content=raw,
                    byte_size=len(raw.encode()),
                    sha256=hashlib.sha256(raw.encode()).hexdigest(),
                    hash_origin="upload_bytes",
                    ingestion_status="ready",
                )
            )
            session.flush()
            session.execute(
                update(Document)
                .where(Document.id == prepared[0])
                .values(
                    current_revision=2,
                    content=raw,
                )
            )
            session.commit()

    result = capture(
        db_engine,
        [prepared[1]],
        "Amber permit",
        AS_OF,
        tokenizer,
        allow_api=True,
        embedder=FakeEmbedder(replace_source),
    )
    assert result["candidates"]
    assert all(item["revision"] == 1 for item in result["candidates"])
    assert all(
        "Different policy after replacement" not in item["text"] for item in result["candidates"]
    )
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT current_revision FROM documents WHERE id=:id"), {"id": prepared[0]}
            )
            == 2
        )


def test_concurrent_delete_after_candidate_read_keeps_snapshot_and_parent_consistent(
    db_engine, tokenizer, prepared
):
    from studio_copilot.documents.reranking.capture import capture

    deleted = False

    def remove_after_candidates(connection, cursor, statement, parameters, context, many):
        nonlocal deleted
        if not deleted and "embedding <=>" in statement:
            deleted = True
            with db_engine.begin() as other:
                other.execute(delete(Document).where(Document.id == prepared[0]))

    event.listen(db_engine, "after_cursor_execute", remove_after_candidates)
    try:
        result = capture(
            db_engine,
            [prepared[1]],
            "Amber permit",
            AS_OF,
            tokenizer,
            allow_api=True,
            embedder=FakeEmbedder(),
        )
    finally:
        event.remove(db_engine, "after_cursor_execute", remove_after_candidates)
    assert deleted is True
    assert result["candidates"]
    assert all(
        f"{item['run_id']}:{item['parent_id']}" in result["parents"]
        for item in result["candidates"]
    )
    # The finished snapshot is usable offline; a new capture sees the deletion.
    with pytest.raises(RetrievalError) as caught:
        capture(
            db_engine,
            [prepared[1]],
            "Amber permit",
            AS_OF,
            tokenizer,
            allow_api=True,
            embedder=FakeEmbedder(),
        )
    assert caught.value.code == "source_missing"
