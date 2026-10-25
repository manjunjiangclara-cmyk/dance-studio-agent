from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import AgentRun, Message, Student

from .helpers import review, start

pytestmark = pytest.mark.integration


def test_revision_is_explicit_and_rejection_leaves_no_record_or_checkpoint(
    rig, scenario, db_engine
):
    client, model, _, saver = rig
    run = start(rig, scenario)
    revised = review(client, run, "revise", feedback="Ask about travel preferences.")
    assert revised.status_code == 200, revised.text
    newer = revised.json()
    assert newer["revision"] == 2 and newer["draft_message_id"] != run["draft_message_id"]
    assert model.query_count == 4
    assert review(client, run, "approve").status_code == 409
    assert review(client, newer, "reject").json()["status"] == "closed"
    assert saver.get_tuple({"configurable": {"thread_id": run["id"]}}) is None
    with Session(db_engine) as db:
        assert {m.kind for m in db.scalars(select(Message))} == {"student_email", "assistant_draft"}
        assert "Teacher approved" not in db.get(Student, scenario["student"]).ai_summary
        assert db.get(AgentRun, UUID(run["id"])).approved_response_id is None
