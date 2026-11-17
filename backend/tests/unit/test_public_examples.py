"""Published fixtures must stay fictional, linked, and aligned with the schema."""

import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import Base

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "frontend" / "src" / "data"


def test_public_manifest_matches_application_tables_and_foreign_keys():
    manifest = json.loads((DATA / "schema.v1.json").read_text())
    tables = {
        name: table
        for name, table in Base.metadata.tables.items()
        if table.info.get("database_browser", True)
    }
    assert {row["name"] for row in manifest["tables"]} == set(tables)
    actual = {
        (name, fk.parent.name, fk.column.table.name)
        for name, table in tables.items()
        for fk in table.foreign_keys
    }
    published = {(row["table"], row["field"], row["target"]) for row in manifest["relationships"]}
    assert published == actual
    for table in manifest["tables"]:
        assert set(table["fields"]) | {"id", "created_at", "updated_at"} == set(
            tables[table["name"]].columns.keys()
        )


def test_fixtures_have_consistent_links_and_only_published_fictional_identities():
    data = json.loads((DATA / "examples.v1.json").read_text())
    manifest = json.loads((DATA / "schema.v1.json").read_text())
    assert data["version"] == 1 and "predefined" in data["notice"].lower()
    assert date.fromisoformat(data["as_of"])
    for student in data["students"]:
        assert student["email"].endswith("@example.test")
    for table in manifest["tables"]:
        for row in data[table["name"]]:
            assert set(row) == set(Base.metadata.tables[table["name"]].columns.keys())
    for relation in manifest["relationships"]:
        ids = {row["id"] for row in data[relation["target"]]}
        for row in data[relation["table"]]:
            assert row[relation["field"]] is None or row[relation["field"]] in ids
    for run in data["agent_runs"]:
        source = next(row for row in data["messages"] if row["id"] == run["source_message_id"])
        assert source["conversation_id"] == run["conversation_id"]
        assert source["kind"] == "student_email"
        if run["approved_response_id"]:
            response = next(
                row for row in data["messages"] if row["id"] == run["approved_response_id"]
            )
            assert response["kind"] == "teacher_response"
    assert {run["status"] for run in data["agent_runs"]} >= {
        "awaiting_review",
        "approved",
        "failed",
        "superseded",
    }
    assert any(run["interpretation"].get("missing_details") for run in data["agent_runs"])
    assert any(run["interpretation"].get("flow") == "teacher_handoff" for run in data["agent_runs"])


def test_static_website_serves_no_backend_or_workspace_records(monkeypatch, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Public shell only</title>")
    (tmp_path / "assets" / "example.js").write_text("console.log('fictional');")
    monkeypatch.setenv("WEBSITE_DIST", str(tmp_path))
    app = create_app(create_engine("sqlite://"), admin_token="must-never-be-public")
    with TestClient(app) as client:
        for path in ["/", "/demo", "/demo/students/example", "/workspace/reviews/example"]:
            response = client.get(path)
            assert response.status_code == 200 and "Public shell only" in response.text
            assert "must-never-be-public" not in response.text
        assert client.get("/assets/example.js").status_code == 200
        assert client.get("/.env").status_code == 404
        assert client.get("/backend/.env").status_code == 404
        assert client.get("/api/v1/unknown").status_code == 404
        assert client.get("/api/v1/students").status_code == 401
        for path in ["/api/v1/database", "/api/v1/database/students"]:
            response = client.get(path)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
            assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
