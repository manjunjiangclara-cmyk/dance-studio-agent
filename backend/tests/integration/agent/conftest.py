from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import ClassSession, Conversation, Message, SessionAttendance

from .helpers import FakeModel


@pytest.fixture
def scenario(db_engine, db, catalog, tmp_path, monkeypatch):
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        "version: test\nabsence_notice_before_start: true\n"
        "explanation: Synthetic test policy\nlevel_order: [Level 1, Level 2, Level 3]\n"
    )
    monkeypatch.setenv("STUDIO_POLICY_PATH", str(policy))
    historical_start = datetime.now(UTC) - timedelta(days=14)
    historical = ClassSession(
        class_id=catalog.regular_class.id,
        starts_at=historical_start,
        ends_at=historical_start + timedelta(hours=1),
        capacity=12,
        students=[catalog.student.id],
    )
    db.add(historical)
    db.flush()
    db.add(
        SessionAttendance(
            session_id=historical.id,
            student_id=catalog.student.id,
            status="attended",
            level_at_attendance="Level 2",
        )
    )
    catalog.student.context = {"staff_note": "Preserve me"}
    catalog.class_session.students = [catalog.student.id]
    conversation = Conversation(student=catalog.student, subject="Makeup")
    source = Message(
        conversation=conversation,
        kind="student_email",
        body="Thursday please",
        occurred_at=datetime.fromisoformat("2027-02-07T10:00:00+11:00"),
    )
    db.add(source)
    db.flush()
    result = {
        "conversation": conversation.id,
        "source": source.id,
        "student": catalog.student.id,
        "session": catalog.class_session.id,
        "other_student": None,
    }
    db.commit()
    return result


@pytest.fixture
def rig(db_engine, scenario):
    model, saver = FakeModel(), InMemorySaver()
    service = AgentService(db_engine, model, checkpoints=lambda: nullcontext(saver))
    with TestClient(
        create_app(db_engine, admin_token="test", agent_service=service),
        headers={"Authorization": "Bearer test"},
    ) as client:
        yield client, model, service, saver
