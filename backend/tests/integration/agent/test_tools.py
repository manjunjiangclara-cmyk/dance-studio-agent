from datetime import timedelta

import pytest
from pydantic import ValidationError

from studio_copilot.agent.policy import load_policy
from studio_copilot.agent.tools import execute_tool
from studio_copilot.persistence.models import Conversation, Message

pytestmark = pytest.mark.integration


def test_notice_is_strictly_before_start_and_policy_is_editable(db, catalog, tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        'version: "test"\nabsence_notice_before_start: true\nexplanation: "Test policy"\n'
    )
    policy = load_policy(path)
    start = catalog.class_session.starts_at
    conversation = Conversation(student=catalog.student)
    for notice_at, expected in [
        (start - timedelta(seconds=1), True),
        (start, False),
        (start + timedelta(seconds=1), False),
    ]:
        notice = Message(
            conversation=conversation,
            kind="student_email",
            body="I cannot attend Monday.",
            occurred_at=notice_at,
        )
        db.add(notice)
        db.flush()
        result = execute_tool(
            db,
            catalog.student.id,
            notice.id,
            policy,
            "check_absence_notice",
            {"session_id": str(catalog.class_session.id), "absence_message_id": str(notice.id)},
        )
        assert result["notice_before_start"] is expected
        assert result["makeup_eligibility"] == "unknown"
    path.write_text(
        'version: "changed"\nabsence_notice_before_start: false\nexplanation: "Changed policy"\n'
    )
    changed = execute_tool(
        db,
        catalog.student.id,
        None,
        load_policy(path),
        "check_absence_notice",
        {"session_id": str(catalog.class_session.id), "absence_message_id": None},
    )
    assert changed["notice_before_start"] is None
    assert changed["explanation"] == "Changed policy"


@pytest.mark.parametrize(
    "invalid_notice",
    [
        "missing",
        "unknown",
        "other_conversation",
        "staff_note",
        "assistant_draft",
        "later",
        "backdated",
    ],
)
def test_notice_without_valid_conversation_provenance_is_unknown(db, catalog, invalid_notice):
    from uuid import uuid4

    start = catalog.class_session.starts_at
    conversation = Conversation(student=catalog.student)
    source = Message(
        conversation=conversation,
        kind="student_email",
        body="Saturday instead",
        occurred_at=start + timedelta(days=1),
    )
    notice = Message(
        conversation=conversation,
        kind="student_email",
        body="I cannot attend Monday",
        occurred_at=start - timedelta(days=1),
    )
    if invalid_notice == "other_conversation":
        notice.conversation = Conversation(student=catalog.student)
    elif invalid_notice in {"staff_note", "assistant_draft"}:
        notice.kind = invalid_notice
    elif invalid_notice == "later":
        notice.occurred_at = source.occurred_at + timedelta(seconds=1)
    db.add_all([source, notice])
    db.flush()
    if invalid_notice == "backdated":
        notice.created_at = source.created_at + timedelta(seconds=1)
        db.flush()
    notice_id = None if invalid_notice == "missing" else str(notice.id)
    if invalid_notice == "unknown":
        notice_id = str(uuid4())
    result = execute_tool(
        db,
        catalog.student.id,
        source.id,
        load_policy(),
        "check_absence_notice",
        {"session_id": str(catalog.class_session.id), "absence_message_id": notice_id},
    )
    assert result["notice_before_start"] is None
    assert result["absence_message_id"] is None
    assert result["timing_unknown_reason"]
    assert not any(ref.startswith("message:") for ref in result["references"])


def test_followup_uses_original_absence_email_timestamp(rig, scenario, db_engine):
    from sqlalchemy.orm import Session

    from .helpers import start

    client, model, _, _ = rig
    with Session(db_engine) as db, db.begin():
        notice = db.get(Message, scenario["source"])
        notice.body = "I cannot attend my Monday class on 2027-02-08. Can I make it up Thursday?"
    followup = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={
            "kind": "student_email",
            "body": "Saturday instead",
            "occurred_at": "2027-02-09T10:00:00+11:00",
        },
    )
    assert followup.status_code == 201
    run = start(rig, {**scenario, "source": followup.json()["id"]})
    result = next(e["result"] for e in run["evidence"] if e["tool"] == "check_absence_notice")
    assert result["notice_before_start"] is True
    assert result["absence_message_id"] == str(scenario["source"])
    assert "message:" + str(scenario["source"]) in result["references"]


def test_session_search_returns_local_dates_and_does_not_promise_makeup_capacity(db, catalog):
    result = execute_tool(
        db,
        catalog.student.id,
        None,
        load_policy(),
        "search_sessions",
        {
            "from_date": "2027-02-08",
            "to_date": "2027-02-08",
            "weekday": 0,
            "level": "Level 2",
            "location_id": None,
        },
    )
    assert result["items"][0]["id"] == str(catalog.class_session.id)
    assert "unknown" in result["items"][0]["makeup_availability"]
    assert result["items"][0]["placement"] == "requires policy or teacher judgment"


def test_tools_reject_student_override_and_unbounded_date_ranges(db, catalog):
    with pytest.raises(ValidationError):
        execute_tool(
            db,
            catalog.student.id,
            None,
            load_policy(),
            "get_enrolments",
            {"on_date": "2027-02-08", "student_id": str(catalog.student.id)},
        )
    with pytest.raises(ValidationError):
        execute_tool(
            db,
            catalog.student.id,
            None,
            load_policy(),
            "search_sessions",
            {
                "from_date": "2027-01-01",
                "to_date": "2028-01-01",
                "weekday": None,
                "level": None,
                "location_id": None,
            },
        )
