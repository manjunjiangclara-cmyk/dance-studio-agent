"""The browser exposes complete stored application records with bounded reads."""

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import AgentRun, Base, Conversation, Message, Student

pytestmark = pytest.mark.integration


def test_database_catalog_and_every_stored_column(client, records, db_engine):
    with Session(db_engine) as db:
        student = db.get(Student, UUID(records["student"]["id"]))
        student.context = {"preferences": {"days": ["Thursday"], "confirmed": False}}
        conversation = Conversation(student=student, subject="Database browser")
        source = Message(conversation=conversation, kind="student_email", body="Full message text")
        db.add(source)
        db.flush()
        db.add(
            AgentRun(
                conversation_id=conversation.id,
                source_message_id=source.id,
                status="awaiting_review",
                revision=1,
                interpretation={"request_summary": "Inspect all stored fields"},
                evidence=[{"source": "student"}],
                draft_details={"body": "A complete draft"},
                policy_snapshot={"policy": "Full policy snapshot"},
            )
        )
        db.commit()
    catalog = client.get("/api/v1/database")
    assert catalog.status_code == 200
    assert catalog.headers["cache-control"] == "no-store"
    assert {table["name"] for table in catalog.json()} == set(Base.metadata.tables) - {
        "embedding_runs",
        "embedding_vectors",
        "document_chunks",
    }
    assert "session_bookings" not in {table["name"] for table in catalog.json()}
    sessions = next(table for table in catalog.json() if table["name"] == "class_sessions")
    assert "students" in sessions["columns"]
    with Session(db_engine) as db:
        for descriptor in catalog.json():
            table = Base.metadata.tables[descriptor["name"]]
            assert descriptor["columns"] == list(table.columns.keys())
            response = client.get(f"/api/v1/database/{table.name}")
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            result = response.json()
            assert (
                result["total"]
                == descriptor["total"]
                == db.scalar(select(func.count()).select_from(table))
            )
            for item in result["items"]:
                assert set(item) == set(table.columns.keys())
    student = client.get("/api/v1/database/students").json()["items"][0]
    assert student["context"]["preferences"]["confirmed"] is False
    assert student["highest_level"] == "Level 2"
    assert student["ai_summary"] is None
    message = client.get("/api/v1/database/messages").json()["items"][0]
    assert message["body"] == "Full message text" and message["review_managed"] is False
    run = client.get("/api/v1/database/agent_runs").json()["items"][0]
    assert run["policy_snapshot"] == {"policy": "Full policy snapshot"}
    assert run["evidence"] == [{"source": "student"}]


def test_database_pagination_and_table_allowlist(client, records):
    first = client.get("/api/v1/database/locations?limit=1").json()
    second = client.get("/api/v1/database/locations?limit=1&offset=1").json()
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/v1/database/locations?limit=1").json() == first
    assert client.get("/api/v1/database/locations?offset=2").json() == {
        "items": [],
        "total": 2,
        "limit": 20,
        "offset": 2,
    }
    for query in ["limit=0", "limit=101", "offset=-1"]:
        assert client.get(f"/api/v1/database/students?{query}").status_code == 422
    for name in [
        "unknown",
        "alembic_version",
        "checkpoints",
        "students;DROP TABLE students",
        "embedding_runs",
        "embedding_vectors",
        "document_chunks",
    ]:
        assert client.get(f"/api/v1/database/{name}").status_code == 404
