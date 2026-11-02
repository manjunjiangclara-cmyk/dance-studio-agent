"""Exercise document ingestion against migrated PostgreSQL without external services."""

import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.schema import CreateSchema, DropSchema

from studio_copilot.api.app import create_app
from tests.support import migration_config

pytestmark = pytest.mark.integration

ROOT = "/api/v1/documents"
HEADERS = {"Authorization": "Bearer test"}


@pytest.fixture
def client(db_engine):
    with TestClient(create_app(db_engine, admin_token="test"), headers=HEADERS) as value:
        yield value


def upload(client, raw=b"# Handbook\n\nBring a water bottle.", *, document_id=None, **fields):
    filename = fields.pop("filename", "handbook.md")
    data = {"title": "Studio handbook", **fields}
    if document_id is None:
        return client.post(
            ROOT + "/upload", data=data, files={"file": (filename, raw, "text/plain")}
        )
    return client.put(
        f"{ROOT}/{document_id}/upload",
        data=data,
        files={"file": (filename, raw, "text/plain")},
    )


def metadata(client, document_id):
    response = client.get(f"{ROOT}/{document_id}/metadata")
    assert response.status_code == 200, response.text
    return response.json()


def revisions(client, document_id):
    response = client.get(f"{ROOT}/{document_id}/revisions")
    assert response.status_code == 200, response.text
    return response.json()


def preview(client, document_id, revision, *, offset=0, limit=20_000):
    response = client.get(
        f"{ROOT}/{document_id}/revisions/{revision}/preview",
        params={"offset": offset, "limit": limit},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_retains_raw_hash_and_preview_is_pinned_to_immutable_revision(client):
    raw = b"\xef\xbb\xbf# Handbook\r\n\r\nBring a water bottle.\r\n"
    response = upload(client, raw, effective_from="2027-01-01", effective_to="2027-12-31")
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    first = metadata(client, document_id)
    assert first["current_revision"] == 1
    assert first["sha256"] == hashlib.sha256(raw).hexdigest()
    assert first["byte_size"] == len(raw)
    assert first["hash_origin"] == "upload_bytes"
    assert first["ingestion_status"] == "ready"
    assert first["effective_from"] == "2027-01-01"
    assert first["effective_to"] == "2027-12-31"
    original_preview = preview(client, document_id, 1)

    changed = upload(
        client,
        b"# New handbook\nTrial classes cost $20.",
        document_id=document_id,
        expected_revision="1",
        title="New handbook",
    )
    assert changed.status_code == 200, changed.text
    assert metadata(client, document_id)["current_revision"] == 2
    assert preview(client, document_id, 1) == original_preview
    assert "Trial classes cost $20." in preview(client, document_id, 2)["content"]
    assert {item["revision"] for item in revisions(client, document_id)} == {1, 2}


def test_preview_pages_preserve_unicode_and_do_not_mix_revisions(client):
    text = "# Handbook\nCafé dancers bring water.\n" * 8
    response = upload(client, text.encode())
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    offset, parts = 0, []
    while True:
        page = preview(client, document_id, 1, offset=offset, limit=13)
        assert page["revision"] == 1
        assert page["total_characters"] == len(text)
        assert len(page["content"]) <= 13
        parts.append(page["content"])
        if page["next_offset"] is None:
            break
        assert page["next_offset"] > offset
        offset = page["next_offset"]
        if len(parts) == 1:
            replacement = upload(
                client, b"Completely different.", document_id=document_id, expected_revision="1"
            )
            assert replacement.status_code == 200, replacement.text
    assert "".join(parts) == text
    assert preview(client, document_id, 1, offset=len(text))["content"] == ""
    assert client.get(f"{ROOT}/{document_id}/revisions/999/preview").status_code == 404
    for parameters in ({"offset": -1}, {"limit": 0}, {"limit": 20_001}):
        assert (
            client.get(f"{ROOT}/{document_id}/revisions/1/preview", params=parameters).status_code
            == 422
        )


@pytest.mark.parametrize(
    "raw,fields",
    [
        (b"", {}),
        (b" \r\n\t", {}),
        (b"\xef\xbb\xbf", {}),
        (b"bad\x00text", {}),
        (b"\xff", {}),
        (b"Good text", {"filename": "handbook.pdf"}),
        (b"Good text", {"filename": "../handbook.md"}),
        (b"Good text", {"title": " "}),
        (b"Good text", {"effective_from": "2027-02-30"}),
        (b"Good text", {"effective_from": "2027-02-01", "effective_to": "2027-01-01"}),
    ],
)
def test_invalid_replacement_preserves_all_existing_content_and_metadata(client, raw, fields):
    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    before = metadata(client, document_id)
    response = upload(client, raw, document_id=document_id, expected_revision="1", **fields)
    assert response.status_code == 422, response.text
    assert metadata(client, document_id) == before
    assert len(revisions(client, document_id)) == 1


def test_two_simultaneous_replacements_have_one_winner(db_engine, client):
    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    barrier = Barrier(2)

    def replace(text):
        with TestClient(create_app(db_engine, admin_token="test"), headers=HEADERS) as other:
            barrier.wait(timeout=10)
            response = upload(other, text, document_id=document_id, expected_revision="1")
            return response.status_code, text

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(replace, [b"First contender", b"Second contender"]))
    assert sorted(status for status, _ in results) == [200, 409]
    winner = next(text for status, text in results if status == 200)
    assert metadata(client, document_id)["current_revision"] == 2
    assert preview(client, document_id, 2)["content"] == winner.decode()
    assert len(revisions(client, document_id)) == 2


def test_legacy_base64_and_streamed_upload_hash_the_bytes_supplied(client):
    raw = b"\xef\xbb\xbf# Handbook\r\nWater is required.\r\n"
    old = client.post(
        ROOT,
        json={
            "title": "Existing API",
            "filename": "legacy.md",
            "content_base64": base64.b64encode(raw).decode(),
        },
    )
    new = upload(client, raw)
    assert old.status_code == 201, old.text
    assert new.status_code == 201, new.text
    old_metadata = metadata(client, old.json()["id"])
    new_metadata = metadata(client, new.json()["id"])
    assert old_metadata["sha256"] == new_metadata["sha256"] == hashlib.sha256(raw).hexdigest()
    assert old_metadata["byte_size"] == new_metadata["byte_size"] == len(raw)
    assert old_metadata["hash_origin"] == "stored_text_utf8"
    assert new_metadata["hash_origin"] == "upload_bytes"
    same = upload(
        client,
        raw,
        document_id=old.json()["id"],
        filename="legacy.md",
        title="Existing API",
        expected_revision="1",
    )
    assert same.status_code == 200, same.text
    assert metadata(client, old.json()["id"])["current_revision"] == 1
    assert metadata(client, old.json()["id"])["hash_origin"] == "stored_text_utf8"
    normalized = upload(client, b"# Handbook\nWater is required.\n")
    assert normalized.status_code == 201, normalized.text
    assert metadata(client, normalized.json()["id"])["sha256"] != new_metadata["sha256"]


def test_duplicate_detection_does_not_merge_documents_and_identical_save_is_noop(client):
    first = upload(client, title="First copy")
    second = upload(client, title="Second copy")
    assert first.status_code == second.status_code == 201
    first_id, second_id = first.json()["id"], second.json()["id"]
    assert first_id != second_id
    assert metadata(client, first_id)["duplicates"] == [{"id": second_id, "title": "Second copy"}]
    assert metadata(client, second_id)["duplicates"] == [{"id": first_id, "title": "First copy"}]
    before = metadata(client, first_id)
    same = upload(client, document_id=first_id, title="First copy", expected_revision="1")
    assert same.status_code == 200, same.text
    assert metadata(client, first_id) == before
    assert len(revisions(client, first_id)) == 1
    assert client.delete(f"{ROOT}/{second_id}").status_code == 200
    assert metadata(client, first_id)["duplicates"] == []


def test_metadata_and_inline_edits_snapshot_revisions_and_reject_stale_edits(client):
    created = upload(client, effective_from="2027-01-01", effective_to="2027-12-31")
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    first = metadata(client, document_id)
    changed = client.patch(
        f"{ROOT}/{document_id}/metadata",
        json={
            "title": "Updated title",
            "effective_to": None,
            "expected_revision": 1,
        },
    )
    assert changed.status_code == 200, changed.text
    second = metadata(client, document_id)
    assert second["current_revision"] == 2
    assert second["effective_from"] == "2027-01-01"
    assert second["effective_to"] is None
    assert second["sha256"] == first["sha256"]
    history = {item["revision"]: item for item in revisions(client, document_id)}
    assert history[1]["title"] == "Studio handbook"
    assert history[1]["effective_to"] == "2027-12-31"

    inline = {
        "title": "Updated title",
        "filename": "handbook.md",
        "content": "# Updated handbook\nBring clean shoes.",
        "expected_revision": 1,
    }
    assert client.put(f"{ROOT}/{document_id}/text", json=inline).status_code == 409
    assert metadata(client, document_id) == second
    inline["expected_revision"] = 2
    saved = client.put(f"{ROOT}/{document_id}/text", json=inline)
    assert saved.status_code == 200, saved.text
    third = metadata(client, document_id)
    assert third["current_revision"] == 3
    assert third["hash_origin"] == "stored_text_utf8"
    assert third["sha256"] == hashlib.sha256(inline["content"].encode()).hexdigest()
    assert preview(client, document_id, 3)["content"] == inline["content"]
    assert preview(client, document_id, 1)["content"] != inline["content"]
    # Even identical content must not bypass an out-of-date expected revision.
    assert client.put(f"{ROOT}/{document_id}/text", json=inline).status_code == 409
    assert metadata(client, document_id) == third


def test_streaming_upload_accepts_10mb_and_rejects_one_byte_more(client):
    raw = b"A" * 10_000_000
    accepted = upload(client, raw, filename="large.txt")
    assert accepted.status_code == 201, accepted.text
    document_id = accepted.json()["id"]
    before = metadata(client, document_id)
    assert before["byte_size"] == len(raw)
    assert before["sha256"] == hashlib.sha256(raw).hexdigest()
    page = preview(client, document_id, 1)
    assert len(page["content"]) == 20_000
    assert page["next_offset"] == 20_000
    rejected = upload(client, raw + b"B", document_id=document_id, expected_revision="1")
    assert rejected.status_code == 413, rejected.text
    assert metadata(client, document_id) == before
    assert len(revisions(client, document_id)) == 1


def test_migration_backfills_legacy_hashes_and_preserves_invalid_blank_content(db_engine):
    schema = "legacy_document_" + uuid4().hex
    valid_id, blank_id, unicode_blank_id = uuid4(), uuid4(), uuid4()
    original = "\ufeff# Existing handbook\r\nBring water.\r\n"
    with db_engine.begin() as connection:
        connection.execute(CreateSchema(schema))
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "d30e61b4a8c2")
        for document_id, content in [
            (valid_id, original),
            (blank_id, " \n\t"),
            (unicode_blank_id, "\ufeff\u2003\u00a0"),
        ]:
            connection.execute(
                text(
                    "INSERT INTO documents (id, title, filename, content) "
                    "VALUES (:id, 'Legacy', 'legacy.md', :content)"
                ),
                {"id": document_id, "content": content},
            )
        command.upgrade(config, "head")
        # Use the existing connection so requests see the isolated migration schema.
        with TestClient(create_app(connection, admin_token="test"), headers=HEADERS) as legacy:
            valid = metadata(legacy, valid_id)
            assert valid["hash_origin"] == "stored_text_utf8"
            assert valid["sha256"] == hashlib.sha256(original.encode()).hexdigest()
            assert valid["ingestion_status"] == "ready"
            assert valid["current_revision"] == 1
            assert preview(legacy, valid_id, 1)["content"] == original
            blank = metadata(legacy, blank_id)
            assert blank["ingestion_status"] == "needs_correction"
            assert preview(legacy, blank_id, 1)["content"] == " \n\t"
            assert metadata(legacy, unicode_blank_id)["ingestion_status"] == "needs_correction"
        connection.execute(DropSchema(schema, cascade=True))


def test_database_rejects_changes_to_immutable_revision(db_engine, client):
    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    original = preview(client, document_id, 1)
    with pytest.raises(DBAPIError, match="Document revisions are immutable"):
        with db_engine.begin() as connection:
            connection.execute(
                text("UPDATE document_revisions SET content = 'Tampered' WHERE document_id = :id"),
                {"id": document_id},
            )
    assert preview(client, document_id, 1) == original
    assert metadata(client, document_id)["current_revision"] == 1


@pytest.mark.parametrize(
    "changes",
    [{"effective_from": "2028-01-01"}, {"effective_to": "2026-12-31"}],
)
def test_partial_metadata_date_update_validates_merged_range_and_preserves_state(client, changes):
    created = upload(client, effective_from="2027-01-01", effective_to="2027-12-31")
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    before = metadata(client, document_id)
    response = client.patch(
        f"{ROOT}/{document_id}/metadata",
        json={"title": "Studio handbook", "expected_revision": 1, **changes},
    )
    assert response.status_code == 422, response.text
    assert metadata(client, document_id) == before
    assert len(revisions(client, document_id)) == 1


def test_document_deleted_while_receiving_replacement_is_not_recreated(
    db_engine, client, monkeypatch
):
    from studio_copilot.api import documents

    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    receive_upload = documents.receive_upload
    deletions = []

    async def receive_with_deletion(request):
        original_stream = request.stream

        async def interrupted_stream():
            async for chunk in original_stream():
                if chunk and not deletions:
                    middle = len(chunk) // 2
                    yield chunk[:middle]
                    with TestClient(
                        create_app(db_engine, admin_token="test"), headers=HEADERS
                    ) as other:
                        deletions.append(other.delete(f"{ROOT}/{document_id}").status_code)
                    yield chunk[middle:]
                else:
                    yield chunk

        request.stream = interrupted_stream
        return await receive_upload(request)

    monkeypatch.setattr(documents, "receive_upload", receive_with_deletion)
    response = upload(
        client, b"Replacement received later.", document_id=document_id, expected_revision="1"
    )
    assert deletions == [200]
    assert response.status_code == 404, response.text
    assert client.get(f"{ROOT}/{document_id}/metadata").status_code == 404
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM document_revisions WHERE document_id = :id"),
                {"id": document_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("replace_existing", [False, True])
def test_failed_revision_insert_rolls_back_document_creation_or_replacement(
    db_engine, client, replace_existing
):
    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    before = metadata(client, document_id)
    documents_before = client.get(ROOT).json()
    failures = []

    def fail_revision_insert(_connection, _cursor, statement, parameters, _context, _many):
        if "INSERT INTO document_revisions" in statement and not failures:
            failures.append(statement)
            raise OperationalError(
                statement, parameters, RuntimeError("Synthetic database failure")
            )

    event.listen(db_engine, "before_cursor_execute", fail_revision_insert)
    try:
        response = upload(
            client,
            b"A replacement that cannot be persisted.",
            **({"document_id": document_id, "expected_revision": "1"} if replace_existing else {}),
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", fail_revision_insert)
    assert len(failures) == 1
    assert response.status_code == 503, response.text
    assert "Synthetic database failure" not in response.text
    assert metadata(client, document_id) == before
    assert client.get(ROOT).json() == documents_before
    assert len(revisions(client, document_id)) == 1


def test_delete_removes_document_and_all_revision_previews(client):
    created = upload(client)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    assert client.delete(f"{ROOT}/{document_id}").status_code == 200
    for suffix in ("metadata", "revisions", "revisions/1/preview"):
        assert client.get(f"{ROOT}/{document_id}/{suffix}").status_code == 404


def test_legacy_read_remains_pinned_when_file_is_replaced_with_large_content(client, monkeypatch):
    from studio_copilot.api import documents

    original = b"A small original handbook."
    created = upload(client, original)
    assert created.status_code == 201
    document_id = created.json()["id"]
    original_revision_for = documents.revision_for
    replaced = False

    def replace_after_snapshot(db, document, revision=None):
        nonlocal replaced
        snapshot = original_revision_for(db, document, revision)
        if not replaced:
            replaced = True
            replacement = upload(
                client,
                b"X" * 1_000_001,
                document_id=document_id,
                expected_revision="1",
            )
            assert replacement.status_code == 200
        return snapshot

    monkeypatch.setattr(documents, "revision_for", replace_after_snapshot)
    response = client.get(f"{ROOT}/{document_id}")
    assert response.status_code == 200
    result = response.json()
    assert result["current_revision"] == 1
    assert len(result["content"]) == len(original)
    assert result["content"] == original.decode()
    assert result["sha256"] == hashlib.sha256(original).hexdigest()
    assert client.get(f"{ROOT}/{document_id}").status_code == 409
