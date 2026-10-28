"""Makeup safety checks are mandatory even when the model requests no tools."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import Draft
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Enrolment,
    Message,
    Student,
    StudioClass,
)

from .helpers import review, start

pytestmark = pytest.mark.integration


@pytest.fixture
def verified_makeup(rig, scenario, db_engine, monkeypatch):
    with Session(db_engine) as db, db.begin():
        missed = db.get(ClassSession, scenario["session"])
        missed.students = [scenario["student"]]
        source = db.get(Message, scenario["source"])
        source.body = "I will miss my class on 2027-02-08. Could I attend 2027-02-11 instead?"
        target_class = StudioClass(
            name="Thursday Level 2",
            level="Level 2",
            term_id=missed.regular_class.term_id,
            location_id=missed.regular_class.location_id,
        )
        target = ClassSession(
            regular_class=target_class,
            starts_at=datetime.fromisoformat("2027-02-11T18:00:00+11:00"),
            ends_at=datetime.fromisoformat("2027-02-11T19:00:00+11:00"),
            capacity=1,
        )
        db.add(target)
        db.flush()
        target_id = target.id

    model = rig[1]
    interpret = model.interpret_makeup

    def interpret_with_notice(context):
        return interpret(context).model_copy(update={"absence_message_id": scenario["source"]})

    def forbidden_model_lookup(*args, **kwargs):
        pytest.fail("Makeup validation must not depend on model-selected tools")

    monkeypatch.setattr(model, "interpret_makeup", interpret_with_notice)
    monkeypatch.setattr(model, "choose_tools", forbidden_model_lookup)
    monkeypatch.setattr(
        model,
        "draft",
        lambda context: Draft(
            body="Your teacher will review the Thursday proposal.",
            rationale="A proposal, pending teacher review.",
            questions=[],
            references=["session:" + str(target_id)],
            booking_session_id=target_id,
        ),
    )
    return target_id


def assert_no_approval_side_effects(engine, run, target_id, expected_students):
    with Session(engine) as db:
        persisted = db.get(AgentRun, UUID(run["id"]))
        assert persisted.status == "awaiting_review"
        assert persisted.approved_response_id is None
        assert db.get(ClassSession, target_id).students == expected_students
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
            )
            == 0
        )


def test_makeup_verifies_and_searches_without_model_tool_selection(
    rig, scenario, verified_makeup, db_engine
):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    tools = {item["tool"] for item in run["evidence"]}
    assert {
        "get_enrolments",
        "check_absence_notice",
        "verify_makeup_request",
        "search_sessions",
        "validate_makeup_candidates",
    } <= tools
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])
    first = review(rig[0], run, "approve")
    assert first.status_code == 200, first.text
    second = review(rig[0], run, "approve")
    assert second.status_code == 200, second.text
    with Session(db_engine) as db:
        assert db.get(ClassSession, verified_makeup).students == [scenario["student"]]
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
            )
            == 1
        )


@pytest.mark.parametrize("edited", ["We cannot offer this makeup.", "Please attend another class."])
def test_edited_approval_cannot_book_original_proposal(
    rig, scenario, verified_makeup, db_engine, edited
):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    assert review(rig[0], run, "approve", body=edited).status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])
    assert review(rig[0], run, "approve", body=run["draft_details"]["body"]).status_code == 200


def test_weekday_only_search_excludes_other_days(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        start_at = datetime.now(UTC) + timedelta(days=3)
        target.starts_at = start_at
        target.ends_at = start_at + timedelta(hours=1)
        other = ClassSession(
            class_id=target.class_id,
            starts_at=start_at + timedelta(days=1),
            ends_at=start_at + timedelta(days=1, hours=1),
            capacity=1,
        )
        db.add(other)
        db.flush()
        other_id = other.id
        weekday = (
            start_at.astimezone(ZoneInfo(target.regular_class.location.timezone))
            .strftime("%A")
            .swapcase()
        )
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_date": None, "preferred_weekday": weekday}
        ),
    )
    run = start(rig, scenario)
    result = next(e["result"] for e in run["evidence"] if e["tool"] == "search_sessions")
    ids = {item["id"] for item in result["items"]}
    assert str(verified_makeup) in ids
    assert str(other_id) not in ids
    assert run["draft_details"]["booking_session_id"] is None


def test_invalid_weekday_does_not_search_or_propose(rig, scenario, verified_makeup, monkeypatch):
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_date": None, "preferred_weekday": "Someday"}
        ),
    )
    run = start(rig, scenario)
    assert not any(e["tool"] == "search_sessions" for e in run["evidence"])
    assert run["draft_details"]["booking_session_id"] is None


def test_approval_rechecks_requested_weekday(rig, scenario, verified_makeup, db_engine):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    with Session(db_engine) as db, db.begin():
        record = db.get(AgentRun, UUID(run["id"]))
        record.interpretation = {**record.interpretation, "preferred_weekday": "Monday"}
    assert review(rig[0], run, "approve").status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])


@pytest.mark.parametrize("changed", ["notice", "location_name"])
def test_approval_rechecks_notice_and_confirmation_details(
    rig, scenario, verified_makeup, db_engine, changed
):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    with Session(db_engine) as db, db.begin():
        if changed == "notice":
            db.get(Message, scenario["source"]).body = "What should I wear?"
        else:
            db.get(ClassSession, verified_makeup).regular_class.location.name = "New studio name"
    assert review(rig[0], run, "approve").status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])


def test_makeup_database_lookup_failure_produces_safe_clarification(
    rig, scenario, verified_makeup, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    def unavailable(*args, **kwargs):
        raise SQLAlchemyError("synthetic-database-detail")

    monkeypatch.setattr("studio_copilot.agent.makeup.execute_tool", unavailable)
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    assert run["draft_details"]["warnings"]
    assert "synthetic-database-detail" not in str(run)


def test_teacher_date_revision_reextracts_and_revalidates_candidate(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        thursday = db.get(ClassSession, verified_makeup)
        saturday = ClassSession(
            class_id=thursday.class_id,
            starts_at=datetime.fromisoformat("2027-02-13T18:00:00+11:00"),
            ends_at=datetime.fromisoformat("2027-02-13T19:00:00+11:00"),
            capacity=1,
        )
        db.add(saturday)
        db.flush()
        saturday_id = saturday.id
    model = rig[1]
    interpret = model.interpret_makeup

    def corrected(context):
        parsed = interpret(context)
        if "Saturday" in context.get("teacher_feedback", ""):
            parsed = parsed.model_copy(
                update={"preferred_date": "2027-02-13", "preferred_weekday": "Saturday"}
            )
        return parsed

    def draft(context):
        choices = next(
            e["result"]["valid_session_ids"]
            for e in context["evidence"]
            if e["tool"] == "validate_makeup_candidates"
        )
        return Draft(
            body="The selected session is proposed for teacher approval.",
            rationale="Verified candidate",
            questions=[],
            references=["session:" + choices[0]],
            booking_session_id=choices[0],
        )

    monkeypatch.setattr(model, "interpret_makeup", corrected)
    monkeypatch.setattr(model, "draft", draft)
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    revised = review(rig[0], run, "revise", feedback="Please propose Saturday instead.")
    assert revised.status_code == 200, revised.text
    updated = revised.json()
    assert updated["interpretation"]["preferred_date"] == "2027-02-13"
    assert updated["draft_details"]["booking_session_id"] == str(saturday_id)
    assert review(rig[0], updated, "approve").status_code == 200
    with Session(db_engine) as db:
        assert db.get(ClassSession, verified_makeup).students == []
        assert db.get(ClassSession, saturday_id).students == [scenario["student"]]


def test_revision_can_refresh_legacy_missing_absence_reference(
    rig, scenario, verified_makeup, monkeypatch
):
    model = rig[1]
    interpret = model.interpret_makeup

    def legacy_until_revision(context):
        result = interpret(context)
        if not context.get("teacher_feedback"):
            result = result.model_copy(update={"absence_message_id": None})
        return result

    monkeypatch.setattr(model, "interpret_makeup", legacy_until_revision)
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    refreshed = review(rig[0], run, "revise", feedback="Please verify the original absence email.")
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["draft_details"]["booking_session_id"] == str(verified_makeup)


@pytest.mark.parametrize(
    "invalid",
    ["missing_roster", "cancelled_enrolment", "outside_enrolment", "full", "already_attending"],
)
def test_invalid_records_cannot_become_booking_proposals(
    rig, scenario, verified_makeup, db_engine, invalid
):
    with Session(db_engine) as db, db.begin():
        if invalid == "missing_roster":
            db.get(ClassSession, scenario["session"]).students = []
        elif invalid == "cancelled_enrolment":
            db.scalar(select(Enrolment)).status = "cancelled"
        elif invalid == "outside_enrolment":
            db.scalar(select(Enrolment)).starts_on = date(2027, 2, 9)
        elif invalid == "full":
            other = Student(display_name="Occupied seat", email="occupied@example.test")
            db.add(other)
            db.flush()
            db.get(ClassSession, verified_makeup).students = [other.id]
        else:
            db.get(ClassSession, verified_makeup).students = [scenario["student"]]
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None


def test_ended_enrolment_still_verifies_historical_membership(
    rig, scenario, verified_makeup, db_engine
):
    with Session(db_engine) as db, db.begin():
        enrolment = db.scalar(select(Enrolment))
        enrolment.status = "ended"
        enrolment.ends_on = date(2027, 2, 9)
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)


def test_multiple_enrolled_sessions_on_absence_date_need_clarification(
    rig, scenario, verified_makeup, db_engine
):
    with Session(db_engine) as db, db.begin():
        missed = db.get(ClassSession, scenario["session"])
        db.add(
            ClassSession(
                class_id=missed.class_id,
                starts_at=datetime.fromisoformat("2027-02-08T20:00:00+11:00"),
                ends_at=datetime.fromisoformat("2027-02-08T21:00:00+11:00"),
                capacity=12,
                students=[scenario["student"]],
            )
        )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None


def test_model_class_selection_cannot_resolve_ambiguous_generic_notice(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        original = db.get(ClassSession, scenario["session"])
        other_class = StudioClass(
            name="Another Monday class",
            level="Level 2",
            term_id=original.regular_class.term_id,
            location_id=original.regular_class.location_id,
        )
        db.add(other_class)
        db.flush()
        db.add(
            Enrolment(
                student_id=scenario["student"],
                class_id=other_class.id,
                starts_on=date(2027, 2, 1),
                status="active",
            )
        )
        db.add(
            ClassSession(
                class_id=other_class.id,
                starts_at=datetime.fromisoformat("2027-02-08T20:00:00+11:00"),
                ends_at=datetime.fromisoformat("2027-02-08T21:00:00+11:00"),
                capacity=12,
                students=[scenario["student"]],
            )
        )
        original_class = original.class_id
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(update={"absence_class_id": original_class}),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None


def test_approval_rejects_new_ambiguous_same_day_session(rig, scenario, verified_makeup, db_engine):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    with Session(db_engine) as db, db.begin():
        original = db.get(ClassSession, scenario["session"])
        db.add(
            ClassSession(
                class_id=original.class_id,
                starts_at=datetime.fromisoformat("2027-02-08T20:00:00+11:00"),
                ends_at=datetime.fromisoformat("2027-02-08T21:00:00+11:00"),
                capacity=12,
                students=[scenario["student"]],
            )
        )
    assert review(rig[0], run, "approve").status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])


@pytest.mark.parametrize("invalid", ["missing_roster", "full"])
def test_unverified_or_unavailable_request_overrides_confirmation_without_booking_id(
    rig, scenario, verified_makeup, db_engine, monkeypatch, invalid
):
    with Session(db_engine) as db, db.begin():
        if invalid == "missing_roster":
            db.get(ClassSession, scenario["session"]).students = []
        else:
            other = Student(display_name="Occupied seat", email="body-occupied@example.test")
            db.add(other)
            db.flush()
            db.get(ClassSession, verified_makeup).students = [other.id]
    unsafe_body = "Your makeup is confirmed. You are eligible and booked for Thursday."
    monkeypatch.setattr(
        rig[1],
        "draft",
        lambda context: Draft(
            body=unsafe_body,
            rationale="Model claimed confirmation without a structured proposal.",
            questions=[],
            references=[],
            booking_session_id=None,
        ),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    assert run["draft_details"]["body"] != unsafe_body
    assert "confirmed" not in run["draft_details"]["body"].lower()
    assert "?" in run["draft_details"]["body"]


@pytest.mark.parametrize("notice", [None, "unknown", "another_student"])
def test_missing_or_untrusted_absence_notice_cannot_authorize_proposal(
    rig, scenario, verified_makeup, db_engine, monkeypatch, notice
):
    notice_id = None if notice is None else uuid4()
    if notice == "another_student":
        from studio_copilot.persistence.models import Conversation

        with Session(db_engine) as db, db.begin():
            other = Student(display_name="Other student", email="notice-other@example.test")
            conversation = Conversation(student=other)
            message = Message(
                conversation=conversation,
                kind="student_email",
                body="I will miss my class on 2027-02-08.",
                occurred_at=datetime.fromisoformat("2027-02-07T09:00:00+11:00"),
            )
            db.add(message)
            db.flush()
            notice_id = message.id
    interpret = rig[1].interpret_makeup
    monkeypatch.setattr(
        rig[1],
        "interpret_makeup",
        lambda context: interpret(context).model_copy(update={"absence_message_id": notice_id}),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None


@pytest.mark.parametrize(
    "change", ["roster", "enrolment", "missed_class_level", "full", "already_attending"]
)
def test_approval_rechecks_current_source_and_target_records_atomically(
    rig, scenario, verified_makeup, db_engine, change
):
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    expected_students = []
    with Session(db_engine) as db, db.begin():
        if change == "roster":
            db.get(ClassSession, scenario["session"]).students = []
        elif change == "enrolment":
            db.scalar(select(Enrolment)).status = "cancelled"
        elif change == "missed_class_level":
            db.get(ClassSession, scenario["session"]).regular_class.level = "Level 3"
        elif change == "full":
            other = Student(display_name="Last seat", email="last-seat@example.test")
            db.add(other)
            db.flush()
            expected_students = [other.id]
            db.get(ClassSession, verified_makeup).students = expected_students
        else:
            expected_students = [scenario["student"]]
            db.get(ClassSession, verified_makeup).students = expected_students
    response = review(rig[0], run, "approve")
    assert response.status_code == 409, response.text
    assert_no_approval_side_effects(db_engine, run, verified_makeup, expected_students)


def test_attended_missed_session_blocks_proposal(rig, scenario, verified_makeup, db_engine):
    from studio_copilot.persistence.models import SessionAttendance

    with Session(db_engine) as db, db.begin():
        db.add(
            SessionAttendance(
                session_id=scenario["session"],
                student_id=scenario["student"],
                status="attended",
                level_at_attendance="Level 2",
            )
        )
    run = start(rig, scenario)
    evidence = next(e["result"] for e in run["evidence"] if e["tool"] == "verify_makeup_request")
    assert evidence["attendance_status"] == "attended"
    assert not evidence["verified"]
    assert run["draft_details"]["booking_session_id"] is None
    assert "attended" in run["draft_details"]["body"]


def test_higher_than_actual_attendance_is_excluded(rig, scenario, verified_makeup, db_engine):
    from studio_copilot.persistence.models import SessionAttendance

    with Session(db_engine) as db, db.begin():
        row = db.scalar(
            select(SessionAttendance).where(SessionAttendance.student_id == scenario["student"])
        )
        row.level_at_attendance = "Level 1"
    run = start(rig, scenario)
    validation = next(
        e["result"] for e in run["evidence"] if e["tool"] == "validate_makeup_candidates"
    )
    assert validation["max_attended_level"] == "Level 1"
    assert {"session_id": str(verified_makeup), "reason": "above_attended_level"} in validation[
        "excluded"
    ]
    assert run["draft_details"]["booking_session_id"] is None


def test_approval_rechecks_changed_attendance_level(rig, scenario, verified_makeup, db_engine):
    from studio_copilot.persistence.models import SessionAttendance

    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    with Session(db_engine) as db, db.begin():
        row = db.scalar(
            select(SessionAttendance).where(SessionAttendance.student_id == scenario["student"])
        )
        row.level_at_attendance = "Level 1"
    assert review(rig[0], run, "approve").status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])


def test_options_request_lists_valid_sessions_without_booking(
    rig, scenario, verified_makeup, monkeypatch, db_engine
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        target.starts_at = datetime.now(UTC) + timedelta(days=3)
        target.ends_at = target.starts_at + timedelta(hours=1)
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_date": None, "preferred_weekday": None}
        ),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    assert "Thursday Level 2" in run["draft_details"]["body"]
    assert "Studio A" in run["draft_details"]["body"]


def test_named_nonexistent_class_cannot_be_substituted(rig, scenario, verified_makeup, monkeypatch):
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_class_name": "Moonlight Tap Acrobatics"}
        ),
    )
    run = start(rig, scenario)
    validation = next(
        e["result"] for e in run["evidence"] if e["tool"] == "validate_makeup_candidates"
    )
    assert {"session_id": str(verified_makeup), "reason": "requested_class_mismatch"} in validation[
        "excluded"
    ]
    assert run["draft_details"]["booking_session_id"] is None
    assert "couldn't find" in run["draft_details"]["body"].lower()


def test_matching_named_class_is_rechecked_at_approval(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_class_name": "Thursday Level 2"}
        ),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(verified_makeup)
    with Session(db_engine) as db, db.begin():
        db.get(ClassSession, verified_makeup).regular_class.name = "Different class"
    assert review(rig[0], run, "approve").status_code == 409
    assert_no_approval_side_effects(db_engine, run, verified_makeup, [])


def test_overlap_reply_does_not_claim_student_is_in_requested_session(
    rig, scenario, verified_makeup, db_engine
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        other_class = StudioClass(
            name="Contemporary",
            level="Level 2",
            term_id=target.regular_class.term_id,
            location_id=target.regular_class.location_id,
        )
        db.add(
            ClassSession(
                regular_class=other_class,
                starts_at=target.starts_at + timedelta(minutes=30),
                ends_at=target.ends_at + timedelta(minutes=30),
                capacity=2,
                students=[scenario["student"]],
            )
        )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    assert "another class at that time" in run["draft_details"]["body"]
    assert "already list you in the requested session" not in run["draft_details"]["body"]


def test_requested_time_excludes_other_session_at_same_class(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        correct = ClassSession(
            class_id=target.class_id,
            starts_at=target.starts_at + timedelta(hours=1),
            ends_at=target.ends_at + timedelta(hours=1),
            capacity=2,
        )
        db.add(correct)
        db.flush()
        correct_id = correct.id
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(update={"preferred_time": "19:00"}),
    )
    # The fake draft proposes the 18:00 session even though the student asked for 19:00.
    run = start(rig, scenario)
    validation = next(
        e["result"] for e in run["evidence"] if e["tool"] == "validate_makeup_candidates"
    )
    assert {"session_id": str(verified_makeup), "reason": "requested_time_mismatch"} in validation[
        "excluded"
    ]
    assert str(correct_id) in validation["valid_session_ids"]
    assert run["draft_details"]["booking_session_id"] is None


def test_invalid_requested_time_fails_closed(rig, scenario, verified_makeup, monkeypatch):
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(update={"preferred_time": "not-a-time"}),
    )
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] is None
    assert "confirm the requested makeup start time" in run["draft_details"]["body"].lower()


def test_late_notice_requires_review_without_a_booking_proposal(
    rig, scenario, verified_makeup, db_engine
):
    with Session(db_engine) as db, db.begin():
        missed = db.get(ClassSession, scenario["session"])
        source = db.get(Message, scenario["source"])
        source.occurred_at = missed.starts_at + timedelta(minutes=1)
    run = start(rig, scenario)
    verification = next(
        e["result"] for e in run["evidence"] if e["tool"] == "verify_makeup_request"
    )
    assert verification["verified"] is True
    assert verification["notice_before_start"] is False
    assert verification["notice_acceptable"] is False
    assert run["draft_details"]["booking_session_id"] is None
    assert "after the class started" in run["draft_details"]["body"]


def test_options_search_continues_past_ineligible_first_page(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        first = datetime.now(UTC) + timedelta(days=2)
        target.starts_at = first + timedelta(hours=8)
        target.ends_at = target.starts_at + timedelta(hours=1)
        for index in range(31):
            starts = first + timedelta(minutes=index * 10)
            db.add(
                ClassSession(
                    class_id=target.class_id,
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    capacity=1,
                    students=[scenario["student"]],
                )
            )
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_date": None, "preferred_weekday": None}
        ),
    )
    run = start(rig, scenario)
    searches = [e["result"] for e in run["evidence"] if e["tool"] == "search_sessions"]
    validation = next(
        e["result"] for e in run["evidence"] if e["tool"] == "validate_makeup_candidates"
    )
    assert len(searches) >= 2
    assert any(item["id"] == str(verified_makeup) for page in searches for item in page["items"])
    assert str(verified_makeup) in validation["valid_session_ids"]
    assert "could not find" not in run["draft_details"]["body"].lower()


def test_weekday_search_continues_after_500_nonmatching_rows(
    rig, scenario, verified_makeup, db_engine, monkeypatch
):
    with Session(db_engine) as db, db.begin():
        target = db.get(ClassSession, verified_makeup)
        first = datetime.now(UTC) + timedelta(days=2)
        target.starts_at = first + timedelta(days=2)
        target.ends_at = target.starts_at + timedelta(hours=1)
        weekday = target.starts_at.astimezone(
            ZoneInfo(target.regular_class.location.timezone)
        ).strftime("%A")
        db.add_all(
            [
                ClassSession(
                    class_id=target.class_id,
                    starts_at=first + timedelta(seconds=index),
                    ends_at=first + timedelta(hours=1, seconds=index),
                    capacity=1,
                )
                for index in range(501)
            ]
        )
    model = rig[1]
    interpret = model.interpret_makeup
    monkeypatch.setattr(
        model,
        "interpret_makeup",
        lambda context: interpret(context).model_copy(
            update={"preferred_date": None, "preferred_weekday": weekday}
        ),
    )
    run = start(rig, scenario)
    searches = [e["result"] for e in run["evidence"] if e["tool"] == "search_sessions"]
    validation = next(
        e["result"] for e in run["evidence"] if e["tool"] == "validate_makeup_candidates"
    )
    assert len(searches) >= 2
    assert str(verified_makeup) in validation["valid_session_ids"]
