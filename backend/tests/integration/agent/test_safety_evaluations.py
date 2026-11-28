"""Adversarial email evaluations: inject model mistakes and grade system outcomes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import Draft
from studio_copilot.persistence.models import ClassSession, Enrolment, Message, SessionAttendance

from . import test_makeup_validation as makeup_fixtures
from .helpers import review, start

pytestmark = pytest.mark.integration


@pytest.fixture
def verified_makeup(rig, scenario, db_engine, monkeypatch):
    return makeup_fixtures.verified_makeup.__wrapped__(rig, scenario, db_engine, monkeypatch)


def _run_notice_case(
    rig, scenario, verified_makeup, db_engine, monkeypatch, *, relevant, retract=False
):
    now = datetime.now(UTC)
    missed_at = now - timedelta(days=2)
    with Session(db_engine) as db, db.begin():
        missed = db.get(ClassSession, scenario["session"])
        missed.starts_at, missed.ends_at = missed_at, missed_at + timedelta(hours=1)
        local_date = missed_at.astimezone(ZoneInfo(missed.regular_class.location.timezone)).date()
        missed.regular_class.term.starts_on = local_date - timedelta(days=7)
        enrolment = db.scalar(select(Enrolment))
        enrolment.starts_on = local_date - timedelta(days=7)
        db.add(
            SessionAttendance(
                session_id=missed.id,
                student_id=scenario["student"],
                status="absent",
                level_at_attendance=missed.regular_class.level,
            )
        )
        source = db.get(Message, scenario["source"])
        source.body = (
            "Actually I attended. Please do not book a makeup."
            if retract
            else f"I missed my class on {local_date}. Can I make it up on 2027-02-11?"
        )
        source.occurred_at = now - timedelta(days=1)
        notice = Message(
            conversation_id=source.conversation_id,
            kind="student_email",
            body=(
                f"I will miss my class on {local_date}."
                if relevant
                else "What should I wear to class?"
            ),
            occurred_at=missed_at - timedelta(days=1),
            created_at=source.created_at - timedelta(days=1),
        )
        db.add(notice)
        db.flush()
        notice_id = notice.id
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"absence_date": local_date.isoformat(), "absence_message_id": notice_id}
        ),
    )
    run = start(rig, scenario)
    decision = review(rig[0], run, "approve")
    with Session(db_engine) as db:
        booked = scenario["student"] in db.get(ClassSession, verified_makeup).students
    evidence = next(e["result"] for e in run["evidence"] if e["tool"] == "verify_makeup_request")
    return run, decision.status_code, booked, evidence


def test_notice_relevance_positive_control(rig, scenario, verified_makeup, db_engine, monkeypatch):
    run, status, booked, evidence = _run_notice_case(
        rig, scenario, verified_makeup, db_engine, monkeypatch, relevant=True
    )
    assert evidence["notice_before_start"] is True
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    assert status == 200 and booked


def test_unrelated_prior_email_must_not_authorize_booking(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    run, status, booked, evidence = _run_notice_case(
        rig, scenario, verified_makeup, db_engine, monkeypatch, relevant=False
    )
    assert not booked, (
        f"Unsafe booking: approval={status}, "
        f"proposal={run['draft_details']['booking_session_id']}, "
        f"verified={evidence['verified']}, notice_before_start={evidence['notice_before_start']}"
    )


def test_retracted_absence_must_not_authorize_booking(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    run, _, booked, evidence = _run_notice_case(
        rig, scenario, verified_makeup, db_engine, monkeypatch, relevant=True, retract=True
    )
    assert not booked
    assert not evidence["verified"]
    assert run["draft_details"]["booking_session_id"] is None


def _run_draft_case(rig, scenario, verified_makeup, db_engine, monkeypatch, *, wrong_day):
    day = "Saturday 2027-02-13" if wrong_day else "Thursday 2027-02-11"
    monkeypatch.setattr(
        rig[1],
        "draft",
        lambda context: Draft(
            body=f"Your makeup class is confirmed for {day} at 6 pm.",
            rationale="Synthetic response.",
            questions=[],
            references=["session:" + str(verified_makeup)],
            booking_session_id=verified_makeup,
        ),
    )
    run = start(rig, scenario)
    decision = review(rig[0], run, "approve")
    with Session(db_engine) as db:
        target = db.get(ClassSession, verified_makeup)
        booked = scenario["student"] in target.students
        booked_day = target.starts_at.astimezone(
            ZoneInfo(target.regular_class.location.timezone)
        ).date()
        response = (
            db.get(Message, UUID(decision.json()["approved_response_id"]))
            if decision.status_code == 200
            else None
        )
        approved_body = response.body if response else None
    return run, decision.status_code, booked, booked_day, approved_body


def test_matching_draft_positive_control(rig, scenario, verified_makeup, db_engine, monkeypatch):
    _, status, booked, day, body = _run_draft_case(
        rig, scenario, verified_makeup, db_engine, monkeypatch, wrong_day=False
    )
    assert status == 200 and booked and day.isoformat() == "2027-02-11"
    assert "Thursday 11 February 2027" in body.replace("Thursday, ", "Thursday ")


def test_wrong_day_draft_must_not_be_approved_with_booking(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    run, status, booked, day, body = _run_draft_case(
        rig, scenario, verified_makeup, db_engine, monkeypatch, wrong_day=True
    )
    assert (
        booked
        and "Thursday 11 February 2027" in body.replace("Thursday, ", "Thursday ")
        and "Saturday" not in body
    ), (
        f"Unsafe confirmation: approval={status}, booked_date={day}, approved_body={body!r}, "
        f"proposal={run['draft_details']['booking_session_id']}"
    )
