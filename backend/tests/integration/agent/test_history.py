from datetime import datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Conversation, Message

from .helpers import start

pytestmark = pytest.mark.integration


def test_history_is_limited_in_sql_to_three_chronological_conversation_messages(
    rig, scenario, db_engine
):
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
                    kind="staff_note",
                    body=f"Recent {number}",
                    occurred_at=source_at - timedelta(minutes=1),
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

    statements = []

    def capture(_connection, _cursor, statement, parameters, _context, _many):
        if "FROM messages" in statement and "messages.conversation_id =" in statement:
            statements.append((statement, parameters))

    event.listen(db_engine, "before_cursor_execute", capture)
    try:
        start(rig, scenario)
    finally:
        event.remove(db_engine, "before_cursor_execute", capture)
    context = rig[1].routing_contexts[-1]
    assert context["history_limit"] == 3
    assert [item["body"] for item in context["history"]] == [
        "Recent 20",
        "Recent 30",
        "Thursday please",
    ]
    assert context["source"]["id"] == str(scenario["source"])
    assert context["student"]["context"]["staff_note"] == "Preserve me"
    assert statements and all("LIMIT" in sql for sql, _params in statements)
    assert any(
        params.get("param_1") == 3 and scenario["conversation"] in params.values()
        for _sql, params in statements
    )


def test_history_with_fewer_than_three_messages_keeps_the_incoming_email(rig, scenario):
    start(rig, scenario)
    history = rig[1].routing_contexts[-1]["history"]
    assert len(history) == 1
    assert history[0]["id"] == str(scenario["source"])
