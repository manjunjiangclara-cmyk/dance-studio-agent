"""Document updates and archival fence answer preparation without paid providers."""

from dataclasses import asdict
from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from studio_copilot.api.app import create_app
from studio_copilot.documents import activation, online
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.models import Document, DocumentActivation, EmbeddingRun
from tests.unit.test_documents import payload

pytestmark = pytest.mark.integration
ROOT = "/api/v1/documents"
ACTUAL_WORKER = activation.worker


@pytest.fixture
def update_client(db_engine, monkeypatch):
    monkeypatch.setattr(activation, "check_setup", lambda: None)
    calls = []
    monkeypatch.setattr(activation, "worker", lambda *args: calls.append(args))
    with TestClient(
        create_app(db_engine, admin_token="test"), headers={"Authorization": "Bearer test"}
    ) as client:
        yield client, calls


def create_document(client):
    response = client.post(ROOT, json=payload())
    assert response.status_code == 201, response.text
    return response.json()["id"]


def changed_save(client, document_id, kind, expected_revision=1):
    path = f"{ROOT}/{document_id}"
    if kind == "base64":
        return client.put(path, json=payload("Changed", expected_revision=expected_revision))
    if kind == "text":
        return client.put(
            path + "/text",
            json={
                "title": "Welcome",
                "filename": "welcome.md",
                "content": "Changed",
                "expected_revision": expected_revision,
            },
        )
    if kind == "metadata":
        return client.patch(
            path + "/metadata", json={"title": "Changed", "expected_revision": expected_revision}
        )
    return client.put(
        path + "/upload",
        data={"title": "Welcome", "expected_revision": str(expected_revision)},
        files={"file": ("welcome.md", b"Changed", "text/plain")},
    )


def completed_run(db_engine, document_id, revision):
    profile = EmbeddingProfile.from_env()
    with Session(db_engine) as db, db.begin():
        run = EmbeddingRun(
            document_id=UUID(document_id),
            revision=revision,
            chunker_hash="0" * 64,
            profile_hash=profile.key,
            profile=asdict(profile),
            source={},
            chunker_config={},
            headings=[],
            warnings=[],
            status="complete",
            prepared=True,
        )
        db.add(run)
        db.flush()
        return run.id


@pytest.mark.parametrize("kind", ["base64", "text", "metadata", "upload"])
def test_changed_saves_prepare_current_revision_but_initial_creation_does_not(
    update_client, db_engine, kind
):
    client, calls = update_client
    document_id = create_document(client)
    assert calls == []
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)) is None
    changed = changed_save(client, document_id, kind)
    assert changed.status_code == 200, changed.text
    assert changed.json()["current_revision"] == 2
    assert len(calls) == 1
    assert calls[0][1:3] == (UUID(document_id), 2)
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, UUID(document_id))
        assert row.status == "preparing" and row.revision == 2
        assert row.token == calls[0][3]
    assert client.get(f"{ROOT}/{document_id}/revisions/1/preview").json()["content"] == (
        "Studio information"
    )


def test_identical_save_does_not_create_a_revision_or_activation(update_client, db_engine):
    client, calls = update_client
    document_id = create_document(client)
    response = client.put(f"{ROOT}/{document_id}", json=payload(expected_revision=1))
    assert response.status_code == 200, response.text
    assert response.json()["current_revision"] == 1
    assert calls == []
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)) is None


def test_setup_failure_keeps_saved_revision_and_exposes_retryable_failure(
    update_client, db_engine, monkeypatch
):
    client, calls = update_client
    document_id = create_document(client)

    def unavailable():
        raise ValueError("private setup secret")

    monkeypatch.setattr(activation, "check_setup", unavailable)
    response = changed_save(client, document_id, "text")
    assert response.status_code == 200, response.text
    assert response.json()["current_revision"] == 2
    assert calls == []
    assert client.get(f"{ROOT}/{document_id}/revisions/2/preview").json()["content"] == "Changed"
    status = client.get(f"{ROOT}/{document_id}/answer-activation")
    assert status.json()["status"] == "failed"
    assert "private setup secret" not in status.text + response.text
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)).revision == 2


def test_stale_save_does_not_replace_preparation_claim(update_client, db_engine):
    client, calls = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    with Session(db_engine) as db:
        token = db.get(DocumentActivation, UUID(document_id)).token
    assert changed_save(client, document_id, "metadata").status_code == 409
    assert len(calls) == 1
    with Session(db_engine) as db:
        assert db.get(DocumentActivation, UUID(document_id)).token == token
        assert db.get(Document, UUID(document_id)).current_revision == 2


@pytest.mark.parametrize("legacy_delete", [False, True])
def test_archive_preserves_sources_and_cancels_preparation(update_client, db_engine, legacy_delete):
    client, calls = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    path = f"{ROOT}/{document_id}"
    response = (
        client.delete(path)
        if legacy_delete
        else client.post(path + "/archive", json={"expected_revision": 2})
    )
    assert response.status_code == 200, response.text
    if legacy_delete:
        assert response.json()["deleted"] is True
    assert client.get(ROOT).json() == []
    archived = client.get(ROOT, params={"archived": "true"}).json()
    assert len(archived) == 1 and archived[0]["id"] == document_id
    assert archived[0]["archived_at"] is not None
    assert client.get(path + "/revisions/1/preview").json()["content"] == "Studio information"
    assert client.get(path + "/revisions/2/preview").json()["content"] == "Changed"
    with Session(db_engine) as db:
        document = db.get(Document, UUID(document_id))
        assert document.archived_at is not None
        row = db.get(DocumentActivation, UUID(document_id))
        assert row.status == "disabled" and row.token is None and row.run_id is None
    assert len(calls) == 1


def test_archive_conflict_leaves_document_active(update_client):
    client, _ = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    response = client.post(f"{ROOT}/{document_id}/archive", json={"expected_revision": 1})
    assert response.status_code == 409
    assert [item["id"] for item in client.get(ROOT).json()] == [document_id]
    assert client.get(ROOT, params={"archived": "true"}).json() == []


@pytest.mark.parametrize("kind", ["base64", "text", "metadata", "upload"])
def test_archived_documents_reject_edits_and_answer_activation(update_client, kind):
    client, calls = update_client
    document_id = create_document(client)
    path = f"{ROOT}/{document_id}"
    archived = client.post(path + "/archive", json={"expected_revision": 1})
    assert archived.status_code == 200, archived.text
    assert changed_save(client, document_id, kind).status_code == 409
    assert client.post(path + "/answer-activation").status_code == 409
    assert client.get(path + "/metadata").json()["current_revision"] == 1
    assert calls == []


def test_archive_during_worker_completion_cannot_reenable_source(
    update_client, db_engine, monkeypatch
):
    client, calls = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    run_id = completed_run(db_engine, document_id, 2)
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setattr(activation, "Tokenizer", lambda *args: object())

    def archive_during_preparation(*args, **kwargs):
        response = client.post(f"{ROOT}/{document_id}/archive", json={"expected_revision": 2})
        assert response.status_code == 200, response.text
        return {"run_id": str(run_id), "status": "complete", "prepared": True}

    monkeypatch.setattr(activation, "run", archive_during_preparation)
    ACTUAL_WORKER(*calls[0])
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, UUID(document_id))
        assert row.status == "disabled" and row.run_id is None and row.token is None
        with pytest.raises(online.OnlineError):
            online.source_rows(db, [run_id], date(2027, 1, 1))


def test_newer_update_during_worker_completion_keeps_new_claim(
    update_client, db_engine, monkeypatch
):
    client, calls = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    run_id = completed_run(db_engine, document_id, 2)
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setattr(activation, "Tokenizer", lambda *args: object())

    def replace_during_preparation(*args, **kwargs):
        response = changed_save(client, document_id, "metadata", expected_revision=2)
        assert response.status_code == 200, response.text
        return {"run_id": str(run_id), "status": "complete", "prepared": True}

    monkeypatch.setattr(activation, "run", replace_during_preparation)
    ACTUAL_WORKER(*calls[0])
    assert len(calls) == 2
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, UUID(document_id))
        assert row.status == "preparing" and row.revision == 3
        assert row.token == calls[1][3] and row.run_id is None


@pytest.mark.parametrize("mutation", ["update", "archive"])
def test_document_mutation_blocks_approval_of_retained_cited_evidence(
    update_client, db_engine, monkeypatch, mutation
):
    client, _ = update_client
    document_id = create_document(client)
    run_id = completed_run(db_engine, document_id, 1)
    with Session(db_engine) as db, db.begin():
        db.add(
            DocumentActivation(
                document_id=UUID(document_id), revision=1, status="enabled", run_id=run_id
            )
        )
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake-tokenizer")
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/fake-reranker")
    reference = "document:retained-evidence"
    with Session(db_engine) as db:
        rows = online.source_rows(db, [run_id], date(2027, 1, 1))
        source_identity = online.identity(rows[0][0], rows[0][2])
    draft = SimpleNamespace(
        evidence=[
            {
                "tool": "document_answer",
                "result": {
                    "references": [reference],
                    "sources": [source_identity],
                    "supporting_excerpt": "Studio information",
                },
            }
        ],
        draft_details={"references": [reference]},
    )
    with Session(db_engine) as db:
        online.require_current_sources(db, draft)
    if mutation == "update":
        response = changed_save(client, document_id, "text")
    else:
        response = client.post(f"{ROOT}/{document_id}/archive", json={"expected_revision": 1})
    assert response.status_code == 200, response.text
    with Session(db_engine) as db:
        with pytest.raises(online.OnlineError):
            online.require_current_sources(db, draft)
    assert draft.evidence[0]["result"]["supporting_excerpt"] == "Studio information"
    assert client.get(f"{ROOT}/{document_id}/revisions/1/preview").json()["content"] == (
        "Studio information"
    )


def test_worker_failure_after_update_retains_saved_revision_and_allows_retry(
    update_client, db_engine, monkeypatch
):
    client, calls = update_client
    document_id = create_document(client)
    assert changed_save(client, document_id, "text").status_code == 200
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setattr(activation, "Tokenizer", lambda *args: object())

    def fail_provider(*args, **kwargs):
        raise RuntimeError("private provider secret")

    monkeypatch.setattr(activation, "run", fail_provider)
    ACTUAL_WORKER(*calls[0])
    path = f"{ROOT}/{document_id}"
    status = client.get(path + "/answer-activation")
    assert status.json()["status"] == "failed"
    assert "private provider secret" not in status.text
    assert client.get(path + "/revisions/2/preview").json()["content"] == "Changed"
    with Session(db_engine) as db:
        row = db.get(DocumentActivation, UUID(document_id))
        assert row.token is None and row.run_id is None and row.lease_expires_at is None
    retry = client.post(path + "/answer-activation")
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "preparing" and len(calls) == 2
    assert calls[0][3] != calls[1][3]


def test_approval_guard_blocks_concurrent_api_archive_until_commit(
    update_client, db_engine, monkeypatch
):
    client, _ = update_client
    document_id = create_document(client)
    run_id = completed_run(db_engine, document_id, 1)
    with Session(db_engine) as db, db.begin():
        db.add(
            DocumentActivation(
                document_id=UUID(document_id), revision=1, status="enabled", run_id=run_id
            )
        )
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake-tokenizer")
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/fake-reranker")
    with Session(db_engine) as db:
        rows = online.source_rows(db, [run_id], date(2027, 1, 1))
        source_identity = online.identity(rows[0][0], rows[0][2])
    reference = "document:retained-evidence"
    draft = SimpleNamespace(
        evidence=[
            {
                "tool": "document_answer",
                "result": {"references": [reference], "sources": [source_identity]},
            }
        ],
        draft_details={"references": [reference]},
    )

    def bound_archive_wait(_connection, cursor, statement, _parameters, _context, _many):
        if "FROM documents" in statement and "FOR UPDATE" in statement:
            cursor.execute("SET LOCAL lock_timeout = '100ms'")

    path = f"{ROOT}/{document_id}/archive"
    with Session(db_engine) as db, db.begin():
        online.require_current_sources(db, draft)
        event.listen(db_engine, "before_cursor_execute", bound_archive_wait)
        try:
            response = client.post(path, json={"expected_revision": 1})
        finally:
            event.remove(db_engine, "before_cursor_execute", bound_archive_wait)
        assert response.status_code == 503, response.text
    assert client.post(path, json={"expected_revision": 1}).status_code == 200
