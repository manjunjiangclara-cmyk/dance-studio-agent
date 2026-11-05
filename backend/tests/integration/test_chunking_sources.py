"""Read immutable chunking inputs from PostgreSQL without retaining transactions."""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import delete, event, select, text
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking.sources import load_revision
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.persistence.models import Document, DocumentRevision

pytestmark = pytest.mark.integration


@pytest.fixture
def saved_source(db_engine):
    original = "\ufeff# Handbook\r\n\r\nCafé dancers 👩🏽‍🦰 bring water.\r\n"
    created_at = datetime(2026, 11, 2, 3, 4, 5, tzinfo=UTC)
    raw = original.encode("utf-8")
    with Session(db_engine) as session:
        document = Document(title="First title", filename="first.md", content=original)
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title="First title",
                filename="first.md",
                content=original,
                sha256=hashlib.sha256(raw).hexdigest(),
                byte_size=len(raw),
                hash_origin="stored_text_utf8",
                ingestion_status="ready",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 12, 31),
                created_at=created_at,
            )
        )
        session.commit()
    return (
        document_id,
        original,
        {
            "title": "First title",
            "filename": "first.md",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_size": len(raw),
            "document_id": str(document_id),
            "revision": 1,
            "hash_origin": "stored_text_utf8",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "created_at": created_at.isoformat(),
        },
    )


def replace_source(engine, document_id):
    """Commit a genuinely different immutable revision in another transaction."""
    changed = "# Replacement\nCompletely different policy."
    raw = changed.encode()
    with Session(engine) as session:
        session.execute(text("SET LOCAL lock_timeout = '2s'"))
        document = session.get(Document, document_id)
        document.title = "Second title"
        document.filename = "second.txt"
        document.content = changed
        document.current_revision = 2
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=2,
                title=document.title,
                filename=document.filename,
                content=changed,
                sha256=hashlib.sha256(raw).hexdigest(),
                byte_size=len(raw),
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_from=date(2027, 1, 1),
                effective_to=None,
            )
        )
        session.commit()


def test_explicit_revision_loads_all_fields_from_one_immutable_snapshot(db_engine, saved_source):
    document_id, original, expected = saved_source
    replace_source(db_engine, document_id)

    source = load_revision(db_engine, document_id, 1)

    assert source.text == original
    assert source.metadata() == expected
    current = load_revision(db_engine, document_id, 2)
    assert current.revision == 2
    assert current.title == "Second title"
    assert current.filename == "second.txt"
    assert current.effective_from == "2027-01-01"
    assert current.effective_to is None
    assert current.hash_origin == "upload_bytes"
    assert current.sha256 != source.sha256


@pytest.mark.parametrize("change", ["replace", "delete"])
def test_source_select_remains_consistent_if_source_changes_before_fetch(
    db_engine, saved_source, change
):
    document_id, original, expected = saved_source
    changed = False

    def after_select(connection, cursor, statement, parameters, context, executemany):
        nonlocal changed
        if changed or not statement.lstrip().upper().startswith("SELECT"):
            return
        if "FROM document_revisions" not in statement:
            return
        # PostgreSQL has executed the read but the adapter has not fetched/materialized
        # the row. A separate committed writer must never alter any snapshot fields.
        changed = True
        if change == "replace":
            replace_source(db_engine, document_id)
        else:
            with Session(db_engine) as writer:
                writer.execute(text("SET LOCAL lock_timeout = '2s'"))
                writer.execute(delete(Document).where(Document.id == document_id))
                writer.commit()

    event.listen(db_engine, "after_cursor_execute", after_select)
    try:
        source = load_revision(db_engine, document_id, 1)
    finally:
        event.remove(db_engine, "after_cursor_execute", after_select)

    assert changed
    assert source.text == original
    assert source.metadata() == expected
    assert source.validate() is source
    with Session(db_engine) as verifier:
        document = verifier.get(Document, document_id)
        if change == "replace":
            assert document.current_revision == 2
        else:
            assert document is None
            assert verifier.scalar(select(DocumentRevision.id)) is None


def test_loader_is_read_only_and_source_needs_no_connection_after_return(db_engine, saved_source):
    document_id, original, expected = saved_source
    statements, released = [], []

    def before_execute(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def checked_in(connection, record):
        released.append(True)

    event.listen(db_engine, "before_cursor_execute", before_execute)
    event.listen(db_engine, "checkin", checked_in)
    try:
        source = load_revision(db_engine, document_id, 1)
        assert released, "The adapter retained its database connection."
        assert len(statements) == 2
        assert statements[0].strip().upper() == "SET TRANSACTION READ ONLY"
        assert statements[1].lstrip().upper().startswith("SELECT")
        assert "FROM document_revisions" in statements[1]
        assert "FROM documents" not in statements[1]
        assert "FOR UPDATE" not in statements[1].upper()

        # These operations model the CPU-only consumer. No lazy attribute or metadata
        # access may issue another query once the adapter's transaction has closed.
        assert source.text == original
        assert source.metadata() == expected
        assert source.validate() is source
        assert hashlib.sha256(source.text.encode()).hexdigest() == source.sha256
        assert len(statements) == 2
    finally:
        event.remove(db_engine, "before_cursor_execute", before_execute)
        event.remove(db_engine, "checkin", checked_in)


@pytest.mark.parametrize("revision", [99, 0, -1])
def test_missing_or_nonpositive_revision_never_falls_back_to_current(
    db_engine, saved_source, revision
):
    document_id, _, _ = saved_source
    with pytest.raises(ValueError, match="does not exist|positive revision"):
        load_revision(db_engine, document_id, revision)


def test_deleted_document_is_a_clear_missing_revision_error(db_engine, saved_source):
    document_id, _, _ = saved_source
    with Session(db_engine) as writer:
        writer.execute(delete(Document).where(Document.id == document_id))
        writer.commit()
    with pytest.raises(ValueError, match="does not exist or was deleted"):
        load_revision(db_engine, document_id, 1)


def test_cli_exports_pinned_database_revision_without_changing_database(
    db_engine, saved_source, tmp_path
):
    document_id, original, expected = saved_source
    replace_source(db_engine, document_id)
    with db_engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    assert re.fullmatch(r"test_[0-9a-f]{32}", schema)
    child_url = db_engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    child_env = {
        **os.environ,
        "DATABASE_URL": child_url.render_as_string(hide_password=False),
    }
    tokenizer_cache = Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache()))
    output = tmp_path / "export"
    args = [
        sys.executable,
        "-m",
        "studio_copilot.documents.chunking",
        "--document-id",
        str(document_id),
        "--revision",
        "1",
        "--output-dir",
        str(output),
        "--tokenizer-cache",
        str(tokenizer_cache),
    ]

    def database_snapshot():
        with db_engine.connect() as connection:
            return (
                connection.execute(text("SELECT * FROM documents ORDER BY id")).all(),
                connection.execute(
                    text("SELECT * FROM document_revisions ORDER BY document_id, revision")
                ).all(),
            )

    before = database_snapshot()
    result = subprocess.run(args, env=child_env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["statistics"]["passage"]["count"] > 0
    assert (output / "source.txt").read_bytes() == original.encode()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["complete"] is True
    assert manifest["source"] == expected
    assert manifest["coverage_characters"] == {"parent": len(original), "passage": len(original)}
    assert database_snapshot() == before

    files_before = {path.name: path.read_bytes() for path in output.iterdir()}
    repeated = subprocess.run(args, env=child_env, capture_output=True, text=True, timeout=30)
    assert repeated.returncode == 1
    assert "chunking:" in repeated.stderr
    assert {path.name: path.read_bytes() for path in output.iterdir()} == files_before
    assert database_snapshot() == before
