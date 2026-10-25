from contextlib import nullcontext
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import Conversation, Message

from .helpers import FakeModel


@pytest.fixture
def scenario(db_engine, db, catalog):
    catalog.student.context = {"staff_note": "Preserve me"}
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
