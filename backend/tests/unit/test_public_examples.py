"""Published fixtures must stay fictional, linked, and aligned with the schema."""

import json
from datetime import date, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import Base
from studio_copilot.public_demo.fixtures import SATURDAY_TRIAL_CLASSES
from studio_copilot.public_demo.records import FictionalMakeupReader, FictionalRecords

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
        "superseded",
    }
    riley_run = next(
        run
        for run in data["agent_runs"]
        if run["source_message_id"] == "e7006165-a655-507c-815c-2ead33050f7f"
    )
    assert riley_run["status"] == "awaiting_review"
    assert riley_run["approved_response_id"] is None and riley_run["error"] is None
    assert any(
        row["id"] == riley_run["draft_message_id"] and row["kind"] == "assistant_draft"
        for row in data["messages"]
    )
    assert any(run["interpretation"].get("missing_details") for run in data["agent_runs"])
    assert any(run["interpretation"].get("flow") == "teacher_handoff" for run in data["agent_runs"])


def test_trial_classes_match_the_public_database_and_timetable():
    data = json.loads((DATA / "examples.v1.json").read_text())
    classes = {row["id"]: row for row in data["classes"]}
    locations = {row["id"]: row for row in data["locations"]}
    actual = {}
    for session in data["class_sessions"]:
        starts_at = datetime.fromisoformat(session["starts_at"])
        if starts_at.date() == date(2027, 2, 13):
            cls = classes[session["class_id"]]
            level = int(cls["level"].removeprefix("Level "))
            location = locations[cls["location_id"]]["name"].replace(" · ", " ")
            time = starts_at.strftime("%I:%M %p").lstrip("0").replace(":00", "").lower()
            actual[level] = (
                f"Adult Ballet Level {level}, Saturday 13 February 2027 at {time}, {location}"
            )
    assert actual == SATURDAY_TRIAL_CLASSES
    records = FictionalRecords(data)
    reader = FictionalMakeupReader(records, records.context("booking"))
    sessions = reader.tool("search_sessions", {"from_date": "2027-02-13", "to_date": "2027-02-13"})[
        "items"
    ]
    assert {row["level"]: row["remaining_places"] for row in sessions} == {
        "Level 1": 12,
        "Level 2": 10,
        "Level 3": 12,
    }


def test_makeup_booking_requires_approval_and_student_on_roster():
    from uuid import UUID

    data = json.loads((DATA / "examples.v1.json").read_text())
    records = FictionalRecords(data)
    maya = next(student for student in data["students"] if student["email"] == "maya@example.test")
    alex_context = records.context("booking")
    reader = FictionalMakeupReader(records, alex_context)
    student = UUID(maya["id"])
    missed = UUID(
        next(
            row["id"] for row in data["class_sessions"] if row["starts_at"].startswith("2027-02-08")
        )
    )
    booking = reader.existing_makeup(student, missed)
    assert booking.starts_at.isoformat() == "2027-02-13T18:00:00+11:00"
    alex = UUID(alex_context["student"]["id"])
    assert reader.existing_makeup(alex, missed) is None
    assert str(booking.id) in reader.pending_makeups(alex, missed, "another-run")
    run = next(row for row in data["agent_runs"] if row["approved_response_id"])
    approved = run["approved_response_id"]
    run["approved_response_id"] = None
    assert reader.existing_makeup(student, missed) is None
    run["approved_response_id"] = approved
    records.session_rows[str(booking.id)]["students"].remove(str(student))
    assert reader.existing_makeup(student, missed) is None


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
