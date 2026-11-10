"""Teacher-facing activation uses durable state and protects owner mutations."""

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from studio_copilot.api.app import create_app
from studio_copilot.documents import activation
from studio_copilot.persistence.models import DocumentActivation
from tests.unit.test_documents import payload
from tests.unit.test_website_auth import session_cookie

pytestmark = pytest.mark.integration
ACTUAL_WORKER = activation.worker


@pytest.fixture
def activation_client(db_engine, monkeypatch):
    for name, value in {
        "OWNER_EMAIL": "owner@example.test",
        "GOOGLE_CLIENT_ID": "test",
        "GOOGLE_CLIENT_SECRET": "test",
        "SESSION_SECRET": "test-session-secret-which-is-longer-than-32-characters",
        "PUBLIC_BASE_URL": "https://studio.example.test",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(activation, "check_setup", lambda: None)
    calls = []
    monkeypatch.setattr(activation, "worker", lambda *args: calls.append(args))
    app = create_app(db_engine, admin_token="test")
    with TestClient(app, base_url="https://studio.example.test") as client:
        yield client, calls


def make_document(client):
    response = client.post(
        "/api/v1/documents", headers={"Authorization": "Bearer test"}, json=payload()
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_activation_requires_owner_and_csrf(activation_client):
    client, _ = activation_client
    document_id = make_document(client)
    path = f"/api/v1/documents/{document_id}/answer-activation"
    assert client.get(path).status_code == 401
    assert client.post(path).status_code == 401
    assert client.delete(path).status_code == 401
    client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
    assert client.get(path).json()["status"] == "disabled"
    for headers in [
        {},
        {"origin": "https://evil.test", "x-csrf-token": "csrf-for-test"},
        {"origin": "https://studio.example.test", "x-csrf-token": "wrong"},
    ]:
        assert client.post(path, headers=headers).status_code == 403
        assert client.delete(path, headers=headers).status_code == 403
    valid = {"origin": "https://studio.example.test", "x-csrf-token": "csrf-for-test"}
    assert client.post(path, headers=valid).status_code == 200
    assert client.delete(path, headers=valid).status_code == 200


def test_preparing_is_idempotent_and_retry_claims_new_token(activation_client, db_engine):
    client, calls = activation_client
    document_id = make_document(client)
    path = f"/api/v1/documents/{document_id}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    assert client.get(path, headers=auth).json()["status"] == "disabled"
    first = client.post(path, headers=auth)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "preparing"
    assert len(calls) == 1
    with Session(db_engine) as db:
        first_token = db.get(DocumentActivation, UUID(document_id)).token
    assert client.post(path, headers=auth).json()["status"] == "preparing"
    assert len(calls) == 1
    with Session(db_engine) as db, db.begin():
        record = db.get(DocumentActivation, UUID(document_id))
        record.status = "failed"
        record.error = "Preparation failed"
    assert client.get(path, headers=auth).json()["status"] == "failed"
    retried = client.post(path, headers=auth)
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "preparing"
    assert len(calls) == 2
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)).token != first_token
    assert client.delete(path, headers=auth).json()["status"] == "disabled"
    assert client.get(path, headers=auth).json()["status"] == "disabled"


def test_unknown_document_does_not_create_activation(activation_client):
    client, calls = activation_client
    path = f"/api/v1/documents/{uuid4()}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    for method in (client.get, client.post, client.delete):
        assert method(path, headers=auth).status_code == 404
    assert calls == []


def test_worker_publishes_only_a_current_completed_run(activation_client, db_engine, monkeypatch):
    from studio_copilot.documents.embedding.provider import EmbeddingProfile
    from studio_copilot.persistence.models import EmbeddingRun

    client, _ = activation_client
    document_id = UUID(make_document(client))
    token = uuid4()
    profile = EmbeddingProfile.from_env()
    with Session(db_engine) as db, db.begin():
        run = EmbeddingRun(
            document_id=document_id,
            revision=1,
            chunker_hash="0" * 64,
            profile_hash=profile.key,
            profile=profile.model_dump() if hasattr(profile, "model_dump") else vars(profile),
            source={},
            chunker_config={},
            headings=[],
            warnings=[],
            status="complete",
            prepared=True,
        )
        db.add(run)
        db.flush()
        run_id = run.id
        db.add(
            DocumentActivation(document_id=document_id, revision=1, status="preparing", token=token)
        )
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setattr(activation, "Tokenizer", lambda *args: object())
    monkeypatch.setattr(
        activation,
        "run",
        lambda *args, **kwargs: {"run_id": str(run_id), "status": "complete", "prepared": True},
    )
    ACTUAL_WORKER(db_engine, document_id, 1, token)
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, document_id)
        assert row.status == "enabled" and row.run_id == run_id


def test_worker_does_not_restore_disabled_or_replaced_claim(
    activation_client, db_engine, monkeypatch
):
    client, _ = activation_client
    document_id = UUID(make_document(client))
    token = uuid4()
    with Session(db_engine) as db, db.begin():
        db.add(
            DocumentActivation(document_id=document_id, revision=1, status="preparing", token=token)
        )
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setattr(activation, "Tokenizer", lambda *args: object())

    def disable_during_preparation(*args, **kwargs):
        with Session(db_engine) as db, db.begin():
            row = db.get(DocumentActivation, document_id)
            row.status, row.token = "disabled", None
        raise RuntimeError("private provider error")

    monkeypatch.setattr(activation, "run", disable_during_preparation)
    ACTUAL_WORKER(db_engine, document_id, 1, token)
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, document_id)
        assert row.status == "disabled" and row.error is None


def test_missing_setup_does_not_start_a_worker(activation_client, monkeypatch):
    client, calls = activation_client
    document_id = make_document(client)

    def unavailable():
        raise ValueError("private setup detail")

    monkeypatch.setattr(activation, "check_setup", unavailable)
    auth = {"Authorization": "Bearer test"}
    path = f"/api/v1/documents/{document_id}/answer-activation"
    response = client.post(path, headers=auth)
    assert response.status_code == 503
    assert "private setup detail" not in response.text
    assert client.get(path, headers=auth).json()["status"] == "disabled"
    assert calls == []


def test_interrupted_preparation_can_be_retried(activation_client, db_engine):
    from datetime import UTC, datetime, timedelta

    client, calls = activation_client
    document_id = make_document(client)
    path = f"/api/v1/documents/{document_id}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    assert client.post(path, headers=auth).status_code == 200
    with Session(db_engine) as db, db.begin():
        row = db.get(DocumentActivation, UUID(document_id))
        previous_token = row.token
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert client.get(path, headers=auth).json()["status"] == "failed"
    assert client.post(path, headers=auth).json()["status"] == "preparing"
    assert len(calls) == 2
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)).token != previous_token


def test_cancel_stops_embedding_batches_and_new_claim_resumes(
    activation_client, db_engine, monkeypatch
):
    from sqlalchemy import select

    from studio_copilot.documents.chunking.tokenizer import default_cache
    from studio_copilot.documents.embedding import pipeline
    from studio_copilot.persistence.models import EmbeddingRun
    from tests.integration.test_embeddings import FakeEmbedder, create_source, large_source

    client, calls = activation_client
    document_id = create_source(db_engine, large_source())
    path = f"/api/v1/documents/{document_id}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    monkeypatch.setenv(
        "STUDIO_TOKENIZER_CACHE", os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    )

    def cancel_and_reenable(attempt, texts):
        if attempt == 1:
            assert client.delete(path, headers=auth).json()["status"] == "disabled"
            assert client.post(path, headers=auth).json()["status"] == "preparing"

    fake = FakeEmbedder(db_engine, hook=cancel_and_reenable)
    monkeypatch.setattr(pipeline, "Embedder", lambda profile: fake)
    assert client.post(path, headers=auth).json()["status"] == "preparing"
    assert len(calls) == 1
    ACTUAL_WORKER(*calls[0])

    # Cancellation takes effect at the next checkpoint: no second paid batch,
    # the embedding lease is released, and the replacement activation stays pending.
    assert len(fake.calls) == 1
    assert len(calls) == 2
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, document_id)
        run = db.scalar(select(EmbeddingRun).where(EmbeddingRun.document_id == document_id))
        assert row.status == "preparing" and row.token == calls[1][3]
        assert run.status == "failed" and run.lease_token is None

    # Resuming uses the first committed batch and needs only the remaining passages.
    ACTUAL_WORKER(*calls[1])
    assert [len(batch) for batch in fake.calls] == [64, 16]
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, document_id)
        run = db.scalar(select(EmbeddingRun).where(EmbeddingRun.document_id == document_id))
        assert row.status == "enabled" and row.run_id == run.id
        assert run.status == "complete" and run.lease_token is None


def test_cancel_prevents_provider_retry(activation_client, db_engine, monkeypatch):
    from studio_copilot.documents.chunking.tokenizer import default_cache
    from studio_copilot.documents.embedding import pipeline
    from tests.integration.test_embeddings import create_source

    client, calls = activation_client
    document_id = create_source(db_engine)
    path = f"/api/v1/documents/{document_id}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    monkeypatch.setenv(
        "STUDIO_TOKENIZER_CACHE", os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    )
    attempts = []

    class RetryingEmbedder:
        def embed(self, texts, before_attempt):
            before_attempt()
            attempts.append("first paid attempt")
            assert client.delete(path, headers=auth).json()["status"] == "disabled"
            before_attempt()
            attempts.append("retry")
            raise AssertionError("Cancellation should prevent a paid retry")

    monkeypatch.setattr(pipeline, "Embedder", lambda profile: RetryingEmbedder())
    assert client.post(path, headers=auth).json()["status"] == "preparing"
    ACTUAL_WORKER(*calls[0])
    assert attempts == ["first paid attempt"]
    assert client.get(path, headers=auth).json()["status"] == "disabled"


def test_reenabled_worker_waits_for_cancelled_worker_to_release_embedding_lease(
    activation_client, db_engine, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from studio_copilot.documents.chunking.tokenizer import default_cache
    from studio_copilot.documents.embedding import pipeline
    from studio_copilot.documents.embedding.provider import EmbeddingError
    from studio_copilot.documents.embedding.store import Store
    from tests.integration.test_embeddings import FakeEmbedder, create_source, large_source

    client, calls = activation_client
    document_id = create_source(db_engine, large_source())
    path = f"/api/v1/documents/{document_id}/answer-activation"
    auth = {"Authorization": "Bearer test"}
    monkeypatch.setenv(
        "STUDIO_TOKENIZER_CACHE", os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    )
    in_flight, release, busy_seen = Event(), Event(), Event()
    original_claim = Store.claim

    def observe_busy(store, chunker):
        try:
            return original_claim(store, chunker)
        except EmbeddingError as error:
            if error.code == "busy":
                busy_seen.set()
            raise

    def pause_first_batch(attempt, texts):
        if attempt == 1:
            in_flight.set()
            assert release.wait(20), "test did not release the first embedding call"

    fake = FakeEmbedder(db_engine, hook=pause_first_batch)
    monkeypatch.setattr(Store, "claim", observe_busy)
    monkeypatch.setattr(pipeline, "Embedder", lambda profile: fake)
    assert client.post(path, headers=auth).json()["status"] == "preparing"
    with ThreadPoolExecutor(max_workers=2) as pool:
        old = pool.submit(ACTUAL_WORKER, *calls[0])
        try:
            assert in_flight.wait(20), "first worker did not start embedding"
            assert client.delete(path, headers=auth).json()["status"] == "disabled"
            assert client.post(path, headers=auth).json()["status"] == "preparing"
            new = pool.submit(ACTUAL_WORKER, *calls[1])
            assert busy_seen.wait(20), "new worker never encountered the existing lease"
        finally:
            release.set()
        old.result(timeout=30)
        new.result(timeout=30)
    assert [len(batch) for batch in fake.calls] == [64, 16]
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, document_id)
        assert row.status == "enabled" and row.run_id is not None
