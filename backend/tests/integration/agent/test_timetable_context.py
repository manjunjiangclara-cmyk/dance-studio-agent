"""Every enquiry can read the actual timetable before asking the student for details."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import Draft, Routing, ToolTurn
from studio_copilot.agent.tools import timetable
from studio_copilot.persistence.models import ClassSession, Enrolment, StudioClass

from .helpers import review, start, turn

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("intent", ["enrolment", "new_student_enquiry", "general_enquiry"])
def test_handoff_gets_single_monday_class_despite_missing_workflow(rig, scenario, intent):
    model = rig[1]
    model.routing = Routing(
        intents=[intent],
        request_summary="Can I add a Monday class this term?",
        needs_clarification=False,
        reason="Teacher must review the enrolment.",
    )
    model.turns = lambda n: turn("get_timetable", {}) if n == 1 else ToolTurn(calls=[], output=[])
    captured = []

    def draft(context):
        captured.append(context)
        item = context["evidence"][0]["result"]["items"][0]
        return Draft(
            body=f"The Monday option is {item['name']}. I'll check enrolment for you.",
            rationale="Timetable evidence; enrolment needs review.",
            questions=[],
            references=["class:" + item["id"]],
        )

    model.draft = draft
    run = start(rig, scenario)
    result = captured[0]["evidence"][0]["result"]
    assert result["truncated"] is False
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["name"] == "Monday Level 2"
    assert item["term"]["current_at_source"] is True
    assert item["location"]["name"] == "Studio A"
    assert item["sessions_truncated"] is False
    assert item["upcoming_sessions"] == [
        {
            "id": str(scenario["session"]),
            "starts_at": "2027-02-08T18:00:00+11:00",
            "ends_at": "2027-02-08T19:00:00+11:00",
            "weekday": "Monday",
        }
    ]
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert run["draft_details"]["references"] == ["class:" + item["id"]]
    assert run["draft_details"]["booking_session_id"] is None


def test_missing_details_and_empty_enrolments_do_not_block_timetable(rig, scenario):
    model = rig[1]
    model.routing = Routing(
        intents=["general_enquiry"],
        request_summary="Which Monday class?",
        needs_clarification=False,
        reason="Timetable enquiry",
    )
    model.missing = ["Which Monday class?"]
    model.turns = lambda n: (
        turn("get_enrolments", {"on_date": "2028-01-01"})
        if n == 1
        else turn("get_timetable", {})
        if n == 2
        else ToolTurn(calls=[], output=[])
    )
    run = start(rig, scenario)
    assert [e["tool"] for e in run["evidence"]] == ["get_enrolments", "get_timetable"]
    assert run["evidence"][0]["result"]["items"] == []
    assert run["evidence"][1]["result"]["items"][0]["name"] == "Monday Level 2"
    assert model.query_count == 3


def test_catalog_discovers_future_term_outside_session_search_window(db, catalog):
    result = timetable(db, datetime.fromisoformat("2026-10-25T20:00:00+11:00"))
    item = result["items"][0]
    assert item["term"]["starts_on"] == "2027-02-01"
    assert item["term"]["current_at_source"] is False
    assert item["upcoming_sessions"][0]["weekday"] == "Monday"
    # Upcoming means relative to the source, not to execution time or UTC weekday.
    result = timetable(db, catalog.class_session.ends_at + timedelta(days=1))
    assert result["items"][0]["upcoming_sessions"] == []


def test_catalog_keeps_distinct_monday_options_and_excludes_student_data(db, catalog):
    cls = StudioClass(
        name="Monday beginner", level="Level 1", term=catalog.term, location=catalog.location
    )
    other = ClassSession(
        regular_class=cls,
        starts_at=catalog.class_session.starts_at,
        ends_at=catalog.class_session.ends_at,
        capacity=12,
    )
    db.add(other)
    db.flush()
    result = timetable(db, catalog.class_session.starts_at - timedelta(days=1))
    assert {item["name"] for item in result["items"]} == {"Monday Level 2", "Monday beginner"}
    assert all(item["upcoming_sessions"][0]["weekday"] == "Monday" for item in result["items"])
    assert catalog.student.email not in str(result)
    assert str(catalog.student.id) not in str(result)


def test_catalog_marks_class_and_session_truncation(db, catalog):
    for index in range(30):
        db.add(
            StudioClass(
                name=f"Class {index}", level="Level 1", term=catalog.term, location=catalog.location
            )
        )
    for index in range(9):
        db.add(
            ClassSession(
                regular_class=catalog.regular_class,
                starts_at=catalog.class_session.starts_at + timedelta(days=index + 1),
                ends_at=catalog.class_session.ends_at + timedelta(days=index + 1),
                capacity=12,
            )
        )
    db.flush()
    result = timetable(db, catalog.class_session.starts_at - timedelta(days=1))
    assert len(result["items"]) == 30
    assert result["truncated"] is True
    # The existing class may be outside the class limit because UUIDs determine ordering.
    for cls in list(db.scalars(select(StudioClass))):
        if cls.id != catalog.regular_class.id:
            db.delete(cls)
    db.flush()
    item = timetable(db, catalog.class_session.starts_at - timedelta(days=1))["items"][0]
    assert len(item["upcoming_sessions"]) == 8
    assert item["sessions_truncated"] is True


def test_handoff_timetable_evidence_never_enables_booking(rig, scenario, db_engine):
    model = rig[1]
    model.routing = Routing(
        intents=["enrolment"],
        request_summary="Add Monday",
        needs_clarification=False,
        reason="Regular enrolment request.",
    )
    model.turns = lambda n: (
        turn(
            "search_sessions",
            {
                "from_date": "2027-02-08",
                "to_date": "2027-02-08",
                "weekday": 0,
                "level": None,
                "location_id": None,
            },
        )
        if n == 1
        else ToolTurn(calls=[], output=[])
    )
    model.draft = lambda context: Draft(
        body="I've booked Monday.",
        rationale="Test invalid proposal",
        questions=[],
        references=["session:" + str(scenario["session"])],
        booking_session_id=scenario["session"],
    )
    with Session(db_engine) as db:
        before = list(db.get(ClassSession, scenario["session"]).students)
        enrolment_count = db.scalar(select(func.count()).select_from(Enrolment))
    run = start(rig, scenario)
    assert run["evidence"][0]["result"]["items"]
    assert run["draft_details"]["booking_session_id"] is None
    assert "I've booked" not in run["draft_details"]["body"]
    response = review(rig[0], run, "approve")
    assert response.status_code == 200, response.text
    with Session(db_engine) as db:
        assert list(db.get(ClassSession, scenario["session"]).students) == before
        assert db.scalar(select(func.count()).select_from(Enrolment)) == enrolment_count
