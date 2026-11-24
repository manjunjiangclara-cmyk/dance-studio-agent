"""Public demo indexing uses its own published source set and fails closed on drift."""

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.documents import online
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.models import Document, DocumentActivation
from studio_copilot.public_demo import document_index
from tests.integration.test_retrieval import LocalVectors, prepared

pytestmark = pytest.mark.integration


@pytest.fixture
def assets(monkeypatch):
    cache = Path(default_cache())
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", str(cache))
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/fake-reranker-for-tests")
    return Tokenizer(cache), EmbeddingProfile()


def test_prepare_publishes_every_demo_document_and_is_idempotent(db_engine, assets):
    tokenizer, profile = assets
    vectors = LocalVectors(db_engine)
    document_index.prepare(db_engine, tokenizer, profile, embedder=vectors)
    config = document_index.configuration(db_engine)
    with Session(db_engine) as db:
        rows = online.source_rows(db, config.run_ids, date(2027, 2, 10))
        actual = {revision.filename: revision.content for _, _, revision in rows}
    expected = {item["filename"]: item["content"] for item in document_index.PUBLIC_DOCUMENTS}
    assert actual == expected
    first_ids = set(config.run_ids)
    document_index.prepare(db_engine, tokenizer, profile, embedder=vectors)
    assert set(document_index.configuration(db_engine).run_ids) == first_ids


def test_missing_or_changed_sources_are_not_used_until_prepared(db_engine, assets, monkeypatch):
    tokenizer, profile = assets
    with pytest.raises(online.OnlineError):
        document_index.configuration(db_engine)
    document_index.prepare(db_engine, tokenizer, profile, embedder=LocalVectors(db_engine))
    old_ids = set(document_index.configuration(db_engine).run_ids)
    changed = deepcopy(document_index.PUBLIC_DOCUMENTS)
    changed[0]["content"] += "\nA new demo policy sentence.\n"
    monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", changed)
    with pytest.raises(online.OnlineError):
        document_index.configuration(db_engine)
    document_index.prepare(db_engine, tokenizer, profile, embedder=LocalVectors(db_engine))
    new_config = document_index.configuration(db_engine)
    assert set(new_config.run_ids) != old_ids
    with Session(db_engine) as db:
        rows = online.source_rows(db, new_config.run_ids, date(2027, 2, 10))
        contents = {revision.filename: revision.content for _, _, revision in rows}
    assert contents[changed[0]["filename"]] == changed[0]["content"]


def test_unrelated_documents_never_join_public_selection(db_engine, assets):
    tokenizer, profile = assets
    private_id, private_run = prepared(db_engine, tokenizer, "# Private\n\nSecret owner note.")
    with Session(db_engine) as db, db.begin():
        db.add(
            DocumentActivation(
                document_id=private_id, revision=1, status="enabled", run_id=private_run
            )
        )
    document_index.prepare(db_engine, tokenizer, profile, embedder=LocalVectors(db_engine))
    config = document_index.configuration(db_engine)
    with Session(db_engine) as db:
        selected = set(db.scalars(select(Document.id).where(Document.id == private_id)).all())
        assert selected == {private_id}
        assert db.get(DocumentActivation, private_id).status == "enabled"
        assert db.get(DocumentActivation, private_id).run_id == private_run
        rows = online.source_rows(db, config.run_ids, date(2027, 2, 10))
    assert private_id not in {document.id for _, document, _ in rows}


def test_failed_rebuild_does_not_publish_partial_new_set(db_engine, assets, monkeypatch):
    tokenizer, profile = assets
    document_index.prepare(db_engine, tokenizer, profile, embedder=LocalVectors(db_engine))
    old = deepcopy(document_index.PUBLIC_DOCUMENTS)
    old_ids = set(document_index.configuration(db_engine).run_ids)
    changed = deepcopy(old)
    changed[0]["content"] += "\nNew policy text requiring a fresh embedding.\n"
    monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", changed)
    with pytest.raises(RuntimeError):
        document_index.prepare(
            db_engine,
            tokenizer,
            profile,
            embedder=LocalVectors(db_engine, error=RuntimeError("provider unavailable")),
        )
    with pytest.raises(online.OnlineError):
        document_index.configuration(db_engine)
    monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", old)
    assert set(document_index.configuration(db_engine).run_ids) == old_ids


def test_changed_embedding_profile_requires_repreparation(db_engine, assets, monkeypatch):
    tokenizer, profile = assets
    document_index.prepare(db_engine, tokenizer, profile, embedder=LocalVectors(db_engine))
    document_index.configuration(db_engine)
    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://embedding.example.test/v1")
    with pytest.raises(online.OnlineError):
        document_index.configuration(db_engine)


def test_owner_database_cannot_be_used_as_demo_via_loopback_alias(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://copilot:demo@localhost:5433/studio_copilot"
    )
    monkeypatch.setenv(
        "STUDIO_PUBLIC_DOCUMENT_DATABASE_URL",
        "postgresql+psycopg://copilot:demo@127.0.0.1:5433/studio_copilot",
    )
    with pytest.raises(online.OnlineError):
        document_index.engine_from_env()
