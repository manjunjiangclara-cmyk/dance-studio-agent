from datetime import datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Conversation, Message

from .helpers import start

pytestmark = pytest.mark.integration


def test_history_includes_all_student_emails_in_chronological_order(rig, scenario, db_engine):
    source_at = datetime.fromisoformat("2027-02-07T10:00:00+11:00")
    with Session(db_engine) as db, db.begin():
        for index in range(8):
            db.add(
                Message(
                    conversation_id=scenario["conversation"],
                    kind="student_email",
                    body=f"Old {index}",
                    occurred_at=source_at - timedelta(hours=index + 1),
                )
            )
        # Identical timestamps must still produce deterministic order by ID.
        for number in [30, 10, 20]:
            db.add(
                Message(
                    id=UUID(int=number),
                    conversation_id=scenario["conversation"],
                    kind="student_email",
                    body=f"Recent {number}",
                    occurred_at=source_at - timedelta(minutes=1),
                )
            )
        for kind in ("assistant_draft", "staff_note", "teacher_response"):
            db.add(
                Message(
                    conversation_id=scenario["conversation"],
                    kind=kind,
                    body=kind,
                    occurred_at=source_at - timedelta(seconds=1),
                )
            )
        other = Conversation(student_id=scenario["student"])
        db.add(
            Message(
                conversation=other,
                kind="student_email",
                body="Different conversation",
                occurred_at=source_at + timedelta(hours=1),
            )
        )

    start(rig, scenario)
    context = rig[1].routing_contexts[-1]
    assert [item["body"] for item in context["history"]] == [
        *(f"Old {index}" for index in reversed(range(8))),
        "Recent 10",
        "Recent 20",
        "Recent 30",
        "Thursday please",
    ]
    assert context["source"]["id"] == str(scenario["source"])
    assert context["student"]["context"]["staff_note"] == "Preserve me"
    assert [item["body"] for item in context["approved_replies"]] == ["teacher_response"]
    assert context["approved_replies"][0]["delivery"] == "unconfirmed"


def test_history_with_only_the_incoming_email(rig, scenario):
    start(rig, scenario)
    history = rig[1].routing_contexts[-1]["history"]
    assert len(history) == 1
    assert history[0]["id"] == str(scenario["source"])
