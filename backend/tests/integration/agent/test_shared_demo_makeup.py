"""Compare the same deterministic rules with PostgreSQL and fictional records."""

from copy import deepcopy
from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Uuid
from sqlalchemy.orm import Session

from studio_copilot.agent.makeup import (
    WorkspaceMakeupReader,
    evidence_result,
    gather_makeup_records,
    validated_candidate_ids,
)
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Conversation,
    Enrolment,
    Location,
    Message,
    SessionAttendance,
    Student,
    StudioClass,
    Term,
)
from studio_copilot.public_demo.records import FictionalRecords, example_records

pytestmark = pytest.mark.integration


def _materialize(db, data):
    for table, model in (
        ("terms", Term),
        ("locations", Location),
        ("classes", StudioClass),
        ("students", Student),
        ("class_sessions", ClassSession),
        ("enrolments", Enrolment),
        ("session_attendance", SessionAttendance),
        ("conversations", Conversation),
        ("messages", Message),
        ("agent_runs", AgentRun),
    ):
        for row in data[table]:
            native = dict(row)
            for column in model.__table__.columns:
                key = column.name
                if native.get(key) is None:
                    continue
                if isinstance(column.type, Uuid):
                    native[key] = UUID(native[key])
                elif key in {"created_at", "updated_at", "occurred_at", "starts_at", "ends_at"}:
                    native[key] = datetime.fromisoformat(native[key])
                elif key in {"starts_on", "ends_on"}:
                    native[key] = date.fromisoformat(native[key])
                elif key == "students":
                    native[key] = [UUID(value) for value in native[key]]
            db.add(model(**native))
        db.flush()


@pytest.mark.parametrize("case", ["pending", "booked", "full", "above_level", "ambiguous"])
def test_owner_and_demo_apply_the_same_makeup_rules(db_engine, case):
    data = deepcopy(example_records())
    alex = "97aa529c-2ca7-5ee9-86c6-0d7c9da03752"
    maya = "5032d2ca-83cc-546f-9f4f-e46202247081"
    saturday = "df96032d-5ce8-561e-948f-bda79b05887e"
    slot = next(row for row in data["class_sessions"] if row["id"] == saturday)
    source = next(row for row in data["messages"] if row["id"] == alex)
    desired_time = "18:00"
    if case == "full":
        slot["capacity"] = len(slot["students"])
    elif case == "above_level":
        source["body"] = "Saturday 2027-02-13 at 7:30 pm instead, please."
        desired_time = "19:30"
    elif case == "ambiguous":
        source["body"] = "Saturday 2027-02-13 instead, please."
        desired_time = None
    fiction = FictionalRecords(data)
    context = fiction.context_for_message(maya if case == "booked" else alex)
    state = {
        "run_id": str(uuid4()),
        "flow": "makeup",
        "context": context,
        "interpretation": {
            "absence_date": "2027-02-08",
            "absence_message_id": context["history"][0]["id"],
            "preferred_date": "2027-02-13",
            "preferred_time": desired_time,
            "missing_details": [],
        },
    }
    demo = fiction.makeup(state)["evidence"]
    with Session(db_engine) as db:
        _materialize(db, data)
        owner_reader = WorkspaceMakeupReader(
            db, UUID(context["student"]["id"]), UUID(context["source"]["id"]), context["policy"]
        )
        owner = gather_makeup_records(owner_reader, state, fiction.now)["evidence"]

    assert [item["tool"] for item in owner] == [item["tool"] for item in demo]
    for key in ("verified", "attendance_status", "existing_makeup_session_id", "issues"):
        assert evidence_result(owner, "verify_makeup_request").get(key) == evidence_result(
            demo, "verify_makeup_request"
        ).get(key)
    assert validated_candidate_ids(owner) == validated_candidate_ids(demo)
    assert evidence_result(owner, "validate_makeup_candidates") == evidence_result(
        demo, "validate_makeup_candidates"
    )
    if case == "pending":
        assert validated_candidate_ids(demo) == {UUID(saturday)}
        for result in (owner, demo):
            slot = next(
                row
                for row in evidence_result(result, "search_sessions")["items"]
                if row["id"] == saturday
            )
            assert (slot["remaining_places"], slot["makeup_status"]) == (10, "awaiting_review")
    else:
        assert not validated_candidate_ids(demo)
    if case == "booked":
        assert (
            evidence_result(demo, "verify_makeup_request")["existing_makeup_session_id"] == saturday
        )
