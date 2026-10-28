"""Booking is an explicit, capacity-checked effect of approving the current proposal."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from uuid import UUID

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from studio_copilot.administration.service import AdministrationError
from studio_copilot.agent.contracts import Draft, ToolTurn
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Conversation,
    Enrolment,
    Message,
    Student,
    StudioClass,
)

from .helpers import review, start, turn

pytestmark = pytest.mark.integration


@pytest.fixture
def booking_target(rig, scenario, db_engine):
    with Session(db_engine) as db, db.begin():
        original = db.get(ClassSession, scenario["session"])
        db.get(
            Message, scenario["source"]
        ).body = "I will miss my class on 2027-02-08. Could I attend 2027-02-11 instead?"
        target_class = StudioClass(
            name="Thursday makeup candidate",
            level="Level 2",
            term_id=original.regular_class.term_id,
            location_id=original.regular_class.location_id,
        )
        target = ClassSession(
            regular_class=target_class,
            starts_at=datetime.fromisoformat("2027-02-11T18:00:00+11:00"),
            ends_at=datetime.fromisoformat("2027-02-11T19:00:00+11:00"),
            capacity=1,
        )
        db.add(target)
        db.flush()
        result = {"id": target.id, "class_id": target.class_id}
    model = rig[1]
    model.turns = lambda count: (
        turn(
            "search_sessions",
            {
                "from_date": "2027-02-11",
                "to_date": "2027-02-11",
                "weekday": None,
                "level": "Level 2",
                "location_id": None,
            },
        )
        if count % 2
        else ToolTurn(calls=[], output=[])
    )
    model.draft = lambda context: Draft(
        body="Your teacher has selected Thursday's session.",
        rationale="The teacher must approve this booking proposal.",
        questions=[],
        references=["session:" + str(result["id"])],
        booking_session_id=result["id"],
    )
    return result


def booking_counts(engine):
    with Session(engine) as db:
        candidate_ids = set(db.scalars(select(Conversation.student_id)))
        regular_memberships = {(e.student_id, e.class_id) for e in db.scalars(select(Enrolment))}
        return (
            sum(
                len(
                    [
                        student_id
                        for student_id in session.students
                        if student_id in candidate_ids
                        and (student_id, session.class_id) not in regular_memberships
                    ]
                )
                for session in db.scalars(select(ClassSession))
            ),
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
            ),
        )


def test_approval_adds_student_once_without_changing_regular_enrolment(
    rig, scenario, booking_target, db_engine, monkeypatch
):
    client, model, _, _ = rig
    reconciliations = []
    reconcile = model.reconcile

    def capture_reconciliation(context):
        reconciliations.append(context)
        return reconcile(context)

    monkeypatch.setattr(model, "reconcile", capture_reconciliation)
    run = start(rig, scenario)
    assert run["draft_details"]["booking_session_id"] == str(booking_target["id"])
    assert booking_counts(db_engine) == (0, 0)
    for _ in range(2):
        approved = review(client, run, "approve", body=run["draft_details"]["body"])
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"
    assert booking_counts(db_engine) == (1, 1)
    assert len(reconciliations) == 1
    assert reconciliations[0]["confirmed_booking"]["session_id"] == str(booking_target["id"])
    assert reconciliations[0]["confirmed_booking"]["status"] == "confirmed"
    assert reconciliations[0]["teacher_response"]["delivery"] == "unconfirmed"
    with Session(db_engine) as db:
        assert db.get(ClassSession, booking_target["id"]).students == [scenario["student"]]
        assert db.scalar(select(func.count()).select_from(Enrolment)) == 1
    assert client.get("/api/v1/bookings").status_code == 404
    roster = client.get(f"/api/v1/sessions/{booking_target['id']}/students").json()
    assert [student["id"] for student in roster["items"]] == [str(scenario["student"])]


@pytest.mark.parametrize("action", ["reject", "revise"])
def test_rejection_or_revision_does_not_book(rig, scenario, booking_target, db_engine, action):
    run = start(rig, scenario)
    kwargs = {"feedback": "Please reconsider the proposal."} if action == "revise" else {}
    response = review(rig[0], run, action, **kwargs)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == ("closed" if action == "reject" else "awaiting_review")
    assert booking_counts(db_engine) == (0, 0)
    if action == "revise":
        assert response.json()["revision"] == run["revision"] + 1
        assert review(rig[0], run, "approve").status_code == 409
        assert booking_counts(db_engine) == (0, 0)


def test_full_session_rejects_approval_without_response_or_booking(
    rig, scenario, booking_target, db_engine
):
    run = start(rig, scenario)
    # Capacity may change after the model read its evidence and before review.
    with Session(db_engine) as db, db.begin():
        occupant = Student(display_name="Regular attendee", email="regular@example.test")
        db.add(occupant)
        db.flush()
        db.get(ClassSession, booking_target["id"]).students = [occupant.id]
    response = review(rig[0], run, "approve")
    assert response.status_code == 409, response.text
    assert booking_counts(db_engine) == (0, 0)
    with Session(db_engine) as db:
        persisted = db.get(AgentRun, UUID(run["id"]))
        assert persisted.approved_response_id is None
        assert persisted.status == "awaiting_review"
    assert (
        rig[0].patch(f"/api/v1/sessions/{booking_target['id']}", json={"capacity": 2}).status_code
        == 200
    )
    approved = review(rig[0], run, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert booking_counts(db_engine) == (1, 1)


def test_booking_survives_memory_failure_and_retry_without_duplicates(
    rig, scenario, booking_target, db_engine
):
    client, model, _, _ = rig
    run = start(rig, scenario)
    model.fail_reconcile = True
    failed = review(client, run, "approve")
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "failed"
    assert failed.json()["approved_response_id"]
    assert booking_counts(db_engine) == (1, 1)
    model.fail_reconcile = False
    response = client.post(f"/api/v1/agent-runs/{run['id']}/retry")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    assert response.json()["approved_response_id"] == failed.json()["approved_response_id"]
    assert booking_counts(db_engine) == (1, 1)


def test_response_write_failure_rolls_back_booking_with_the_response(
    rig, scenario, booking_target, db_engine
):
    run = start(rig, scenario)

    def response_write_failure(db, flush_context, instances):
        if any(isinstance(item, Message) and item.kind == "teacher_response" for item in db.new):
            raise RuntimeError("Synthetic response write failure")

    event.listen(Session, "before_flush", response_write_failure)
    try:
        with pytest.raises(RuntimeError, match="Synthetic response write failure"):
            review(rig[0], run, "approve")
    finally:
        event.remove(Session, "before_flush", response_write_failure)
    assert booking_counts(db_engine) == (0, 0)
    with Session(db_engine) as db:
        assert db.get(AgentRun, UUID(run["id"])).approved_response_id is None


@pytest.mark.parametrize("before_interrupt", [False, True])
def test_retry_recovers_crash_after_booking_commit_before_graph_resume(
    rig, scenario, booking_target, db_engine, monkeypatch, before_interrupt
):
    from studio_copilot.agent.workflow import Workflow

    client, model, service, saver = rig
    run = start(rig, scenario)
    if before_interrupt:
        graph = Workflow(db_engine, model).compile(saver)
        config = {"configurable": {"thread_id": run["id"]}}
        snapshot = graph.get_state(config)
        graph.update_state(config, {"draft": snapshot.values["draft"]}, as_node="persist_draft")
        pending = graph.get_state(config)
        assert pending.next == ("review",)
        assert not any(task.interrupts for task in pending.tasks)
    drive = service._drive

    def crash_before_graph_resume(*args, **kwargs):
        raise RuntimeError("Synthetic process crash after durable approval")

    monkeypatch.setattr(service, "_drive", crash_before_graph_resume)
    with pytest.raises(RuntimeError, match="Synthetic process crash"):
        review(client, run, "approve", body=run["draft_details"]["body"])
    assert booking_counts(db_engine) == (1, 1)
    saved = client.get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["approved_response_id"]
    monkeypatch.setattr(service, "_drive", drive)
    recovered = client.post(f"/api/v1/agent-runs/{run['id']}/retry")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "approved"
    assert recovered.json()["approved_response_id"] == saved["approved_response_id"]
    assert booking_counts(db_engine) == (1, 1)


@pytest.mark.parametrize("change", ["session_time", "class_level"])
def test_changed_session_proposal_rolls_back_approval(
    rig, scenario, booking_target, db_engine, change
):
    client = rig[0]
    run = start(rig, scenario)
    if change == "session_time":
        changed = client.patch(
            f"/api/v1/sessions/{booking_target['id']}",
            json={"starts_at": "2027-02-11T18:15:00+11:00"},
        )
    else:
        changed = client.patch(
            f"/api/v1/classes/{booking_target['class_id']}", json={"level": "Advanced"}
        )
    assert changed.status_code == 200, changed.text
    response = review(client, run, "approve")
    assert response.status_code == 409, response.text
    assert booking_counts(db_engine) == (0, 0)
    with Session(db_engine) as db:
        saved = db.get(AgentRun, UUID(run["id"]))
        assert saved.status == "awaiting_review"
        assert saved.approved_response_id is None


def test_newer_email_prevents_booking_stale_draft(rig, scenario, booking_target, db_engine):
    run = start(rig, scenario)
    message = rig[0].post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={
            "kind": "student_email",
            "body": "Please wait before booking anything.",
            "occurred_at": "2027-02-07T11:00:00+11:00",
        },
    )
    assert message.status_code == 201, message.text
    assert review(rig[0], run, "approve").status_code == 409
    assert booking_counts(db_engine) == (0, 0)


def test_last_seat_is_serialized_between_two_students(rig, scenario, booking_target, db_engine):
    from studio_copilot.bookings.service import create_booking

    first = start(rig, scenario)
    with Session(db_engine) as db, db.begin():
        other = Student(display_name="Other candidate", email="other-booking@example.test")
        conversation = Conversation(student=other)
        source = Message(
            conversation=conversation,
            kind="student_email",
            body="I will miss my class on 2027-02-08. Could I attend 2027-02-11 instead?",
            occurred_at=datetime.fromisoformat("2027-02-07T10:00:00+11:00"),
        )
        db.add(source)
        db.flush()
        missed = db.get(ClassSession, scenario["session"])
        missed.students.append(other.id)
        db.add(
            Enrolment(
                student=other,
                regular_class=missed.regular_class,
                starts_on=missed.regular_class.term.starts_on,
                status="active",
            )
        )
        other_scenario = {"conversation": conversation.id, "source": source.id}
    second = start(rig, other_scenario)
    ready = Barrier(2)

    def compete(run_id):
        try:
            with Session(db_engine) as db, db.begin():
                run = db.get(AgentRun, UUID(run_id))
                ready.wait(timeout=10)
                create_booking(db, run, booking_target["id"])
            return "booked"
        except AdministrationError as error:
            assert error.status == 409
            return "full"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(compete, run["id"]) for run in [first, second]]
        assert sorted(future.result(timeout=15) for future in futures) == ["booked", "full"]
    assert booking_counts(db_engine) == (1, 0)


def test_enrolment_does_not_consume_independent_session_capacity(
    rig, scenario, booking_target, db_engine
):
    client = rig[0]
    run = start(rig, scenario)
    assert review(client, run, "approve").json()["status"] == "approved"
    created = client.post(
        "/api/v1/students", json={"display_name": "New regular", "email": "newregular@example.com"}
    )
    assert created.status_code == 201, created.text
    extra = created.json()
    enrolled = client.post(
        "/api/v1/enrolments",
        json={
            "student_id": extra["id"],
            "class_id": str(booking_target["class_id"]),
            "starts_on": "2027-02-01",
        },
    )
    assert enrolled.status_code == 201, enrolled.text
    session_url = f"/api/v1/sessions/{booking_target['id']}"
    assert client.patch(session_url, json={"capacity": 1}).status_code == 200
    assert client.get(session_url).json()["students"] == [str(scenario["student"])]
    assert (
        client.patch(
            session_url, json={"students": [str(scenario["student"]), extra["id"]]}
        ).status_code
        == 409
    )
    assert booking_counts(db_engine) == (1, 1)
