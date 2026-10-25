from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from studio_copilot.persistence.models import (
    Conversation,
    Message,
    Student,
)

pytestmark = pytest.mark.integration


def test_profile_memory_and_two_consecutive_emails_survive_reload(db, catalog):
    student = catalog.student
    student.context = {"preferred_day": "Thursday"}
    conversation = Conversation(student=student, subject="Makeup request")
    first_at = datetime(2027, 2, 7, 10, tzinfo=ZoneInfo("Australia/Melbourne"))
    # Insert out of order to verify retrieval follows occurrence time.
    conversation.messages = [
        Message(
            kind="student_email",
            body="Actually, Saturday please.",
            occurred_at=first_at + timedelta(minutes=10),
        ),
        Message(kind="student_email", body="Could I attend Thursday?", occurred_at=first_at),
        Message(
            kind="assistant_draft", body="Draft only.", occurred_at=first_at + timedelta(minutes=11)
        ),
    ]
    db.add(conversation)
    student_id, conversation_id = student.id, None
    db.commit()
    conversation_id = conversation.id
    db.expunge_all()

    saved = db.get(Student, student_id)
    assert saved.highest_level == "Level 2"
    assert saved.context == {"preferred_day": "Thursday"}
    saved.context["preferred_day"] = "Saturday"
    db.commit()
    db.expire_all()
    assert db.get(Student, student_id).context["preferred_day"] == "Saturday"
    assert db.get(Student, student_id).highest_level == "Level 2"
    messages = db.get(Conversation, conversation_id).messages
    assert [message.body for message in messages[:2]] == [
        "Could I attend Thursday?",
        "Actually, Saturday please.",
    ]
    assert messages[2].kind == "assistant_draft"
    assert messages[0].occurred_at.utcoffset() is not None
