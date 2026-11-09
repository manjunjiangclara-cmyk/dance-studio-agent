"""Real PostgreSQL/pgvector preparation with fake providers and no paid calls."""

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Barrier, Thread

import pytest
from alembic import command
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Chunker, Tokenizer, load_revision
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import EmbeddingError, EmbeddingProfile, sha256
from studio_copilot.documents.embedding.store import LeaseLost, Store
from studio_copilot.persistence.models import (
    Document,
    DocumentChunk,
    DocumentRevision,
    EmbeddingRun,
    EmbeddingVector,
)
from tests.support import migration_config

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


def unit_vector(index=0):
    result = [0.0] * 1536
    result[index] = 1.0
    return result


def create_source(
    engine, content="\ufeff# Policy\r\n\r\nCafé dancers bring water.\r\n", title="Handbook"
):
    raw = content.encode()
    with Session(engine) as session:
        document = Document(title=title, filename="policy.md", content=content)
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title=title,
                filename="policy.md",
                content=content,
                byte_size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
            )
        )
        session.commit()
    return document_id


def source_chunker(engine, tokenizer, document_id, revision=1):
    return Chunker(load_revision(engine, document_id, revision), tokenizer)


def prepare(store, chunker):
    run_id, token = store.claim(chunker)
    records = list(chunker.records())
    store.save_chunks(run_id, token, list(enumerate(records)))
    store.prepared(
        run_id, token, len(records), sum(record["kind"] == "passage" for record in records)
    )
    return run_id, token, records


def counts(engine):
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                EmbeddingRun,
                DocumentChunk,
                EmbeddingVector,
            )
        )


class FakeEmbedder:
    def __init__(self, engine, *, fail_at=None, hook=None):
        self.engine, self.fail_at, self.hook = engine, fail_at, hook
        self.calls = []

    def embed(self, texts, before_attempt=lambda: None):
        # Paid calls must not retain a database transaction or connection.
        assert self.engine.pool.checkedout() == 0
        before_attempt()
        assert self.engine.pool.checkedout() == 0
        self.calls.append(list(texts))
        if self.hook:
            self.hook(len(self.calls), texts)
        if len(self.calls) == self.fail_at:
            raise EmbeddingError("provider_error", "Simulated unavailable provider")
        return [unit_vector(index % 1536) for index in range(len(texts))], len(texts) * 9


def large_source():
    return "".join(
        f"# Policy {i}\n\nCondition {i} requires teacher approval.\n\n" for i in range(80)
    )


def test_dry_run_is_read_only_and_never_constructs_a_provider(db_engine, tokenizer, monkeypatch):
    document_id = create_source(db_engine)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Dry-run constructed a paid provider")

    monkeypatch.setattr(pipeline, "Embedder", forbidden)
    before = counts(db_engine)
    result = pipeline.plan(db_engine, document_id, 1, tokenizer, EmbeddingProfile())
    assert result["dry_run"] is True and result["revision"] == 1
    assert result["passages"] == result["unique_inputs"] == 1
    assert result["cached_inputs"] == 0 and result["estimated_new_tokens"] > 0
    assert counts(db_engine) == before == (0, 0, 0)


def test_pipeline_stores_exact_chunks_and_bounded_batches_without_embedding_parents(
    db_engine, tokenizer
):
    document_id = create_source(db_engine, large_source())
    profile = EmbeddingProfile()
    expected = list(source_chunker(db_engine, tokenizer, document_id).records())
    fake = FakeEmbedder(db_engine)
    result = pipeline.run(db_engine, document_id, 1, tokenizer, profile, embedder=fake)
    assert result["status"] == "complete" and not result["lease_active"]
    assert result["passages"] == result["embedded_passages"] == 80
    assert result["chunks"] == len(expected)
    assert [len(call) for call in fake.calls] == [64, 16]
    expected_passages = [record["text"] for record in expected if record["kind"] == "passage"]
    assert [value for call in fake.calls for value in call] == expected_passages
    assert result["reported_tokens"] == 80 * 9 and result["attempts"] == 2
    with Session(db_engine) as session:
        chunks = session.scalars(select(DocumentChunk).order_by(DocumentChunk.ordinal)).all()
        for chunk, record in zip(chunks, expected):
            assert chunk.chunk_id == record["id"] and chunk.text == record["text"]
            assert chunk.text_sha256 == sha256(record["text"])
            assert chunk.provenance["source_spans"] == record["source_spans"]
            assert (chunk.vector_key is None) == (chunk.kind == "parent")
        dimensions = (
            session.execute(
                text("SELECT DISTINCT public.vector_dims(embedding) FROM embedding_vectors")
            )
            .scalars()
            .all()
        )
        assert dimensions == [1536]
        run = session.scalar(select(EmbeddingRun))
        assert run.source == source_chunker(db_engine, tokenizer, document_id).source.metadata()


def test_complete_run_and_identical_other_document_reuse_cache_without_api_key(
    db_engine, tokenizer, monkeypatch
):
    first_id = create_source(db_engine)
    second_id = create_source(db_engine)
    profile = EmbeddingProfile()
    first = pipeline.run(
        db_engine, first_id, 1, tokenizer, profile, embedder=FakeEmbedder(db_engine)
    )
    cache_count = counts(db_engine)[2]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("A complete/cache-only run constructed a provider")

    monkeypatch.setattr(pipeline, "Embedder", forbidden)
    again = pipeline.run(db_engine, first_id, 1, tokenizer, profile)
    second = pipeline.run(db_engine, second_id, 1, tokenizer, profile)
    assert again == first
    assert second["run_id"] != first["run_id"] and second["status"] == "complete"
    assert second["reported_tokens"] == second["attempts"] == 0
    assert counts(db_engine)[2] == cache_count
    estimate = pipeline.plan(db_engine, second_id, 1, tokenizer, profile)
    assert estimate["cached_inputs"] == estimate["unique_inputs"] == 1
    assert estimate["estimated_new_tokens"] == 0


def test_profile_changes_never_reuse_an_incompatible_cached_vector(db_engine, tokenizer):
    document_id = create_source(db_engine)
    first_profile = EmbeddingProfile()
    first = pipeline.run(
        db_engine, document_id, 1, tokenizer, first_profile, embedder=FakeEmbedder(db_engine)
    )
    different = replace(first_profile, endpoint="https://different-provider.example/v1")
    fake = FakeEmbedder(db_engine)
    second = pipeline.run(db_engine, document_id, 1, tokenizer, different, embedder=fake)
    assert second["run_id"] != first["run_id"] and len(fake.calls) == 1
    assert counts(db_engine)[2] == 2
    with Session(db_engine) as session:
        assert set(session.scalars(select(EmbeddingVector.profile_hash))) == {
            first_profile.key,
            different.key,
        }


def test_failed_batch_resumes_checkpoint_and_does_not_repeat_committed_inputs(db_engine, tokenizer):
    document_id = create_source(db_engine, large_source())
    profile, fake = EmbeddingProfile(), FakeEmbedder(db_engine, fail_at=2)
    with pytest.raises(EmbeddingError, match="unavailable"):
        pipeline.run(db_engine, document_id, 1, tokenizer, profile, embedder=fake)
    with Session(db_engine) as session:
        run = session.scalar(select(EmbeddingRun))
        run_id = run.id
    status = Store(db_engine, profile).status(run_id)
    assert status["status"] == "failed" and status["embedded_passages"] == 64
    assert status["reported_tokens"] == 64 * 9
    resumed = FakeEmbedder(db_engine)
    result = pipeline.run(db_engine, document_id, 1, tokenizer, profile, embedder=resumed)
    assert result["run_id"] == str(run_id) and result["status"] == "complete"
    assert [len(call) for call in resumed.calls] == [16]
    assert set(resumed.calls[0]).isdisjoint(fake.calls[0])
    assert result["reported_tokens"] == 80 * 9 and result["attempts"] == 3


def test_partial_chunk_preparation_is_idempotently_resumed(db_engine, tokenizer):
    document_id = create_source(db_engine, large_source())
    profile = EmbeddingProfile()
    chunker = source_chunker(db_engine, tokenizer, document_id)
    records = list(chunker.records())
    store = Store(db_engine, profile)
    run_id, token = store.claim(chunker)
    store.save_chunks(run_id, token, list(enumerate(records[:64])))
    store.fail(run_id, token, "processing_failed")
    result = pipeline.run(
        db_engine, document_id, 1, tokenizer, profile, embedder=FakeEmbedder(db_engine)
    )
    assert result["run_id"] == str(run_id) and result["status"] == "complete"
    assert result["chunks"] == len(records)


def test_expired_owner_cannot_renew_checkpoint_or_finish_even_before_takeover(db_engine, tokenizer):
    document_id = create_source(db_engine)
    profile = EmbeddingProfile()
    store = Store(db_engine, profile)
    chunker = source_chunker(db_engine, tokenizer, document_id)
    run_id, token, records = prepare(store, chunker)
    pending = store.missing(run_id, token)
    with pytest.raises(EmbeddingError) as caught:
        store.claim(chunker)
    assert caught.value.code == "busy"
    with db_engine.begin() as connection:
        connection.execute(
            update(EmbeddingRun)
            .where(EmbeddingRun.id == run_id)
            .values(lease_expires_at=text("clock_timestamp() - interval '1 second'"))
        )
    before = counts(db_engine)
    for action in (
        lambda: store.heartbeat(run_id, token, attempt=True),
        lambda: store.save_chunks(run_id, token, list(enumerate(records))),
        lambda: store.save_vectors(run_id, token, pending, [unit_vector()] * len(pending), 9),
        lambda: store.complete(run_id, token),
    ):
        with pytest.raises(LeaseLost):
            action()
    store.fail(run_id, token, "late_error")
    assert counts(db_engine) == before
    assert store.status(run_id)["status"] == "running"
    reclaimed_id, new_token = store.claim(chunker)
    assert reclaimed_id == run_id and new_token != token
    with pytest.raises(LeaseLost):
        store.heartbeat(run_id, token)
    store.heartbeat(run_id, new_token)


def test_simultaneous_claims_create_one_run_with_exactly_one_owner(db_engine, tokenizer):
    document_id = create_source(db_engine)
    profile = EmbeddingProfile()
    chunker = source_chunker(db_engine, tokenizer, document_id)
    barrier = Barrier(2)

    def claim():
        barrier.wait(timeout=10)
        try:
            return Store(db_engine, profile).claim(chunker)
        except EmbeddingError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(), range(2)))
    assert sum(isinstance(result, tuple) for result in results) == 1
    assert results.count("busy") == 1
    assert counts(db_engine) == (1, 0, 0)


def test_source_deletion_during_provider_call_discards_all_late_vectors(db_engine, tokenizer):
    document_id = create_source(db_engine)

    def deleted_during_call(attempt, texts):
        with Session(db_engine) as session:
            session.execute(delete(Document).where(Document.id == document_id))
            session.commit()

    fake = FakeEmbedder(db_engine, hook=deleted_during_call)
    with pytest.raises(LeaseLost):
        pipeline.run(db_engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=fake)
    assert len(fake.calls) == 1
    assert counts(db_engine) == (0, 0, 0)


def test_deletion_after_checkpoint_retains_old_cache_but_discards_new_late_batch(
    db_engine, tokenizer
):
    document_id = create_source(db_engine, large_source())

    def deleted_on_second_call(attempt, texts):
        if attempt == 2:
            assert counts(db_engine)[2] == 64
            with Session(db_engine) as session:
                session.execute(delete(Document).where(Document.id == document_id))
                session.commit()

    with pytest.raises(LeaseLost):
        pipeline.run(
            db_engine,
            document_id,
            1,
            tokenizer,
            EmbeddingProfile(),
            embedder=FakeEmbedder(db_engine, hook=deleted_on_second_call),
        )
    assert counts(db_engine) == (0, 0, 64)


def test_completion_requires_all_vectors_and_mismatched_input_rolls_back(db_engine, tokenizer):
    document_id = create_source(db_engine)
    store = Store(db_engine, EmbeddingProfile())
    run_id, token, _ = prepare(store, source_chunker(db_engine, tokenizer, document_id))
    with pytest.raises(EmbeddingError) as caught:
        store.complete(run_id, token)
    assert caught.value.code == "incomplete"
    with pytest.raises(EmbeddingError) as caught:
        store.save_vectors(run_id, token, ["Unrelated input"], [unit_vector()], 9)
    assert caught.value.code == "invalid_chunks"
    assert counts(db_engine)[2] == 0
    assert store.status(run_id)["status"] == "running"


def test_competing_cache_writers_preserve_first_committed_vector(db_engine, tokenizer):
    profile = EmbeddingProfile()
    store = Store(db_engine, profile)
    first_id, second_id = create_source(db_engine), create_source(db_engine)
    first_run, first_token, _ = prepare(store, source_chunker(db_engine, tokenizer, first_id))
    second_run, second_token, _ = prepare(store, source_chunker(db_engine, tokenizer, second_id))
    first_inputs = store.missing(first_run, first_token)
    second_inputs = store.missing(second_run, second_token)
    assert first_inputs == second_inputs
    store.save_vectors(first_run, first_token, first_inputs, [unit_vector(0)], 9)
    store.save_vectors(second_run, second_token, second_inputs, [unit_vector(1)], 9)
    assert counts(db_engine)[2] == 1
    with Session(db_engine) as session:
        value = session.scalar(select(EmbeddingVector.embedding))
        assert list(value) == unit_vector(0)
    store.complete(first_run, first_token)
    store.complete(second_run, second_token)


@pytest.mark.parametrize("invalid", [[0.0] * 1536, [1.0] * 1535, [float("nan")] * 1536])
def test_database_rejects_invalid_cached_vectors_even_if_provider_validation_is_bypassed(
    db_engine, invalid
):
    profile = EmbeddingProfile()
    input_sha = sha256("Input")
    with pytest.raises(StatementError), Session(db_engine) as session:
        session.add(
            EmbeddingVector(
                key=profile.vector_key(input_sha),
                profile_hash=profile.key,
                input_sha256=input_sha,
                embedding=invalid,
            )
        )
        session.commit()
    assert counts(db_engine) == (0, 0, 0)


def test_database_foreign_key_prevents_cross_profile_vector_attachment(db_engine, tokenizer):
    document_id = create_source(db_engine)
    first_profile = EmbeddingProfile()
    second_profile = replace(first_profile, endpoint="https://other.example/v1")
    pipeline.run(
        db_engine, document_id, 1, tokenizer, first_profile, embedder=FakeEmbedder(db_engine)
    )
    pipeline.run(
        db_engine, document_id, 1, tokenizer, second_profile, embedder=FakeEmbedder(db_engine)
    )
    with Session(db_engine) as session:
        wrong_key = session.scalar(
            select(EmbeddingVector.key).where(EmbeddingVector.profile_hash == second_profile.key)
        )
        original_key = session.scalar(
            select(DocumentChunk.vector_key).where(
                DocumentChunk.profile_hash == first_profile.key, DocumentChunk.kind == "passage"
            )
        )
    with pytest.raises(StatementError), Session(db_engine) as session:
        session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.profile_hash == first_profile.key, DocumentChunk.kind == "passage")
            .values(vector_key=wrong_key)
        )
        session.commit()
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(DocumentChunk.vector_key).where(
                    DocumentChunk.profile_hash == first_profile.key, DocumentChunk.kind == "passage"
                )
            )
            == original_key
        )


def test_renamed_revision_embeds_changed_prefix_despite_identical_raw_source_hash(
    db_engine, tokenizer
):
    document_id = create_source(db_engine)
    profile = EmbeddingProfile()
    first = pipeline.run(
        db_engine, document_id, 1, tokenizer, profile, embedder=FakeEmbedder(db_engine)
    )
    original = load_revision(db_engine, document_id, 1)
    with Session(db_engine) as session:
        current = session.get(Document, document_id)
        current.title, current.current_revision = "Renamed handbook", 2
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=2,
                title=current.title,
                filename=original.filename,
                content=original.text,
                sha256=original.sha256,
                byte_size=original.byte_size,
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_from=None,
                effective_to=None,
            )
        )
        session.commit()
    fake = FakeEmbedder(db_engine)
    second = pipeline.run(db_engine, document_id, 2, tokenizer, profile, embedder=fake)
    assert second["run_id"] != first["run_id"] and len(fake.calls) == 1
    assert fake.calls[0][0].startswith("Renamed handbook")
    assert counts(db_engine)[2] == 2
    pinned = pipeline.run(db_engine, document_id, 1, tokenizer, profile)
    assert pinned["run_id"] == first["run_id"]


def test_migration_downgrade_preserves_shared_extension_and_existing_source(db_engine):
    document_id = create_source(db_engine)
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "e71b309a4c82")
        assert connection.scalar(text("SELECT to_regclass('embedding_runs')")) is None
        assert connection.scalar(text("SELECT count(*) FROM documents")) == 1
        assert (
            connection.scalar(
                text(
                    "SELECT extnamespace::regnamespace::text "
                    "FROM pg_extension WHERE extname='vector'"
                )
            )
            == "public"
        )
        command.upgrade(config, "head")
    assert load_revision(db_engine, document_id, 1).title == "Handbook"
    assert counts(db_engine) == (0, 0, 0)


@contextmanager
def fake_http_provider():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(request)
            payload = json.dumps(
                {
                    "object": "list",
                    "model": request["model"],
                    "data": [
                        {"object": "embedding", "index": index, "embedding": unit_vector()}
                        for index in reversed(range(len(request["input"])))
                    ],
                    "usage": {"prompt_tokens": 23, "total_tokens": 23},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_real_cli_plan_run_and_status_use_isolated_database_and_fake_http_provider(
    db_engine, tokenizer
):
    document_id = create_source(db_engine)
    with db_engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    assert schema.startswith("test_")
    url = db_engine.url.update_query_dict({"options": f"-csearch_path={schema},public"})
    cache = str(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))
    with fake_http_provider() as (endpoint, received):
        child_env = {
            **os.environ,
            "DATABASE_URL": url.render_as_string(hide_password=False),
            "OPENAI_EMBEDDING_BASE_URL": endpoint,
            "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
            "NO_PROXY": "127.0.0.1,localhost",
        }
        child_env.pop("OPENAI_API_KEY", None)
        common = ["--document-id", str(document_id), "--revision", "1", "--tokenizer-cache", cache]

        def invoke(command_name, args):
            result = subprocess.run(
                [sys.executable, "-m", "studio_copilot.documents.embedding", command_name, *args],
                env=child_env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)

        planned = invoke("plan", common)
        assert planned["dry_run"] is True and received == [] and counts(db_engine) == (0, 0, 0)
        child_env["OPENAI_API_KEY"] = "fake-local-test-key"
        completed = invoke("run", common)
        assert completed["status"] == "complete" and completed["reported_tokens"] == 23
        assert len(received) == 1
        assert received[0]["dimensions"] == 1536 and received[0]["encoding_format"] == "float"
        child_env.pop("OPENAI_API_KEY")
        # Persisted run state is stable; operations describes this CLI invocation.
        completed_operations = completed.pop("operations")
        assert completed_operations["attempts"] == 1
        assert completed_operations["input_tokens"] == 23
        assert completed_operations["unknown_usage_calls"] == 0
        status = invoke("status", ["--run-id", completed["run_id"]])
        status_operations = status.pop("operations")
        assert status_operations["attempts"] == 0
        assert status_operations["input_tokens"] == status_operations["output_tokens"] == 0
        assert status_operations["limits"] == completed_operations["limits"]
        assert status == completed
        resumed = invoke("run", common)
        resumed_operations = resumed.pop("operations")
        assert resumed_operations["attempts"] == 0
        assert resumed_operations["input_tokens"] == resumed_operations["output_tokens"] == 0
        assert resumed_operations["unknown_usage_calls"] == 0
        assert resumed_operations["limits"] == completed_operations["limits"]
        assert resumed == completed and len(received) == 1


def test_failure_rechecks_expiry_after_acquiring_ownership(db_engine, tokenizer, monkeypatch):
    document_id = create_source(db_engine)
    store = Store(db_engine, EmbeddingProfile())
    run_id, token = store.claim(source_chunker(db_engine, tokenizer, document_id))
    with db_engine.begin() as connection:
        connection.execute(
            update(EmbeddingRun)
            .where(EmbeddingRun.id == run_id)
            .values(lease_expires_at=func.clock_timestamp() + text("interval '0.2 seconds'"))
        )
    original = store._owned

    def delay_after_ownership(session, *args):
        run = original(session, *args)
        session.execute(text("SELECT pg_sleep(0.3)"))
        return run

    monkeypatch.setattr(store, "_owned", delay_after_ownership)
    store.fail(run_id, token, "provider_error")
    with Session(db_engine) as session:
        row = session.get(EmbeddingRun, run_id)
        assert row.status == "preparing"
        assert row.lease_token == token
        assert row.error_code is None
