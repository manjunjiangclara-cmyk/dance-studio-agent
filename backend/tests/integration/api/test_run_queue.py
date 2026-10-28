from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import AgentRun, Conversation, Message, Student

pytestmark = pytest.mark.integration


def test_run_queue_filters_pagination_and_bearer_compatibility(client, records, db_engine):
    with Session(db_engine) as db:
        student = db.get(Student, UUID(records["student"]["id"]))
        conversation = Conversation(student=student, subject="Queue examples")
        db.add(conversation)
        db.flush()
        for index, status in enumerate(["awaiting_review", "approved", "failed"]):
            source = Message(conversation=conversation, kind="student_email", body=f"Email {index}")
            db.add(source)
            db.flush()
            db.add(
                AgentRun(
                    conversation_id=conversation.id,
                    source_message_id=source.id,
                    status=status,
                    revision=1,
                    interpretation={
                        "request_summary": f"Request {index}",
                        **(
                            {
                                "routing": {
                                    "intents": ["enrolment"],
                                    "needs_clarification": False,
                                    "reason": "Adding a regular class.",
                                },
                                "flow": "teacher_handoff",
                            }
                            if status == "failed"
                            else {}
                        ),
                    },
                    evidence=[],
                    draft_details={},
                    policy_snapshot={},
                    created_at=datetime(2027, 2, 7, tzinfo=UTC),
                )
            )
        db.commit()
        conversation_id = str(conversation.id)
    all_runs = client.get("/api/v1/agent-runs").json()
    assert all_runs["total"] == 3
    ids = [row["id"] for row in all_runs["items"]]
    assert ids == sorted(ids, reverse=True)
    first = client.get("/api/v1/agent-runs?limit=1").json()
    second = client.get("/api/v1/agent-runs?limit=1&offset=1").json()
    assert first["items"][0]["id"] == ids[0]
    assert second["items"][0]["id"] == ids[1]
    row = client.get(
        "/api/v1/agent-runs",
        params={
            "status": "failed",
            "q": "ALEX",
            "student_id": records["student"]["id"],
            "conversation_id": conversation_id,
        },
    ).json()
    assert row["total"] == 1 and row["items"][0]["status"] == "failed"
    assert row["items"][0]["student_name"] == "Alex Example"
    assert row["items"][0]["routing"]["intents"] == ["enrolment"]
    assert row["items"][0]["flow"] == "teacher_handoff"
    legacy = next(item for item in all_runs["items"] if item["status"] == "approved")
    assert legacy["routing"] is None and legacy["flow"] is None
    assert "interpretation" not in row["items"][0]
    assert "evidence" not in row["items"][0]
    assert "policy_snapshot" not in row["items"][0]
    assert client.get("/api/v1/agent-runs?q=does-not-match").json()["total"] == 0
    assert client.get("/api/v1/agent-runs?status=invalid").status_code == 422
    assert client.get("/api/v1/agent-runs?limit=101").status_code == 422
    assert client.get("/api/v1/agent-runs?offset=-1").status_code == 422
    assert client.get("/api/v1/agent-runs", headers={"Authorization": ""}).status_code == 401


def test_google_owner_can_read_database_but_cannot_administer_records(
    records, db_engine, monkeypatch
):
    for key, value in {
        "OWNER_EMAIL": "owner@example.test",
        "GOOGLE_CLIENT_ID": "test-client",
        "GOOGLE_CLIENT_SECRET": "test-secret",
        "SESSION_SECRET": "a-private-test-secret-longer-than-32-characters",
        "PUBLIC_BASE_URL": "https://studio.example.test",
    }.items():
        monkeypatch.setenv(key, value)
    app = create_app(db_engine, admin_token="test-admin")
    app.state.google_oauth.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "test-google-sub",
                "email": "owner@example.test",
                "email_verified": True,
            }
        }
    )
    with TestClient(app, base_url="https://studio.example.test") as owner:
        assert owner.get("/auth/callback", follow_redirects=False).status_code == 303
        csrf = owner.get("/auth/me").json()["csrf_token"]
        assert owner.get("/api/v1/students").json()["total"] == 1
        assert owner.get("/api/v1/agent-runs").json()["total"] == 0
        assert "session_attendance" in {row["name"] for row in owner.get("/api/v1/database").json()}
        assert owner.get("/api/v1/database/students").json()["total"] == 1
        student = owner.get(f"/api/v1/students/{records['student']['id']}?on_date=2027-02-08")
        assert len(student.json()["current_enrolments"]) == 1
        headers = {"origin": "https://studio.example.test", "x-csrf-token": csrf}
        assert (
            owner.post(
                "/api/v1/students",
                json={"display_name": "Visitor", "email": "v@example.test"},
                headers=headers,
            ).status_code
            == 403
        )
        attendance_path = (
            "/api/v1/sessions/00000000-0000-0000-0000-000000000001"
            "/attendance/00000000-0000-0000-0000-000000000002"
        )
        assert owner.put(attendance_path, json={"status": "attended"}).status_code == 403
        assert (
            owner.put(attendance_path, json={"status": "attended"}, headers=headers).status_code
            == 404
        )
        # A valid browser request reaches the agent dependency; no model is configured
        # and no input is persisted. The owner permission check itself has passed.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        response = owner.post(
            "/api/v1/incoming-emails",
            json={"from": "visitor@example.test", "body": "A fictional enquiry"},
            headers=headers,
        )
        assert response.status_code == 503
        assert owner.get("/api/v1/students").json()["total"] == 1
