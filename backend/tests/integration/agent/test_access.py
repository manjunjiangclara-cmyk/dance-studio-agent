import pytest
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Conversation, Message, Student

from .helpers import start

pytestmark = pytest.mark.integration


def test_student_isolation_and_staff_auth(rig, scenario, db_engine):
    client, model, _, _ = rig
    with Session(db_engine) as db, db.begin():
        other = Student(
            display_name="Other", email="other@example.test", context={"private": "do not expose"}
        )
        conversation = Conversation(student=other)
        db.add(Message(conversation=conversation, kind="student_email", body="Private message"))
    run = start(rig, scenario)
    assert "Private message" not in str(model.contexts)
    assert "do not expose" not in str(model.contexts)
    url = f"/api/v1/agent-runs/{run['id']}"
    assert client.get(url, headers={"Authorization": ""}).status_code == 401
    assert (
        client.post(
            url + "/review",
            json={"action": "approve", "expected_revision": 1},
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )


def test_busy_student_returns_conflict_instead_of_waiting(rig, scenario, db_engine):
    from studio_copilot.agent.persistence.locking import student_lock

    client = rig[0]
    with student_lock(db_engine, scenario["student"]):
        result = client.post(
            f"/api/v1/conversations/{scenario['conversation']}/agent-runs",
            json={"source_message_id": str(scenario["source"])},
        )
        assert result.status_code == 409
        incoming = client.post(
            f"/api/v1/conversations/{scenario['conversation']}/messages",
            json={"kind": "student_email", "body": "A follow-up"},
        )
        assert incoming.status_code == 409
