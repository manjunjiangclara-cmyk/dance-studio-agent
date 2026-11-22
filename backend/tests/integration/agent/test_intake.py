"""The email intake owns identity, message creation and agent startup."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import ModelContextLimitError, Routing
from studio_copilot.agent.persistence.locking import student_lock
from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import AgentRun, Conversation, Message, Student

from .helpers import review

pytestmark = pytest.mark.integration


@pytest.fixture
def current_history(db_engine, scenario):
    with Session(db_engine) as db, db.begin():
        db.get(Student, scenario["student"]).email = "alex@example.com"
        db.get(Message, scenario["source"]).occurred_at = datetime(2020, 1, 1, tzinfo=UTC)


def counts(engine):
    with Session(engine) as db:
        return tuple(
            db.scalar(select(func.count()).select_from(model))
            for model in (Student, Conversation, Message, AgentRun)
        )


def submit(client, sender="alex@example.com", body="Saturday please", **kwargs):
    return client.post("/api/v1/incoming-emails", json={"from": sender, "body": body}, **kwargs)


def test_known_sender_creates_reviewable_run(rig, scenario, current_history, db_engine):
    client, model, _, _ = rig
    before = datetime.now(UTC)
    response = submit(client, " ALEX@EXAMPLE.COM ")
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "awaiting_review", run
    assert run["conversation_id"] == str(scenario["conversation"])
    assert run["interpretation"]["flow"] == "makeup"
    assert run["draft_details"]["body"]
    assert model.routing_contexts
    with Session(db_engine) as db:
        message = db.get(Message, UUID(run["source_message_id"]))
        assert message.kind == "student_email"
        assert message.body == "Saturday please"
        assert before <= message.occurred_at <= datetime.now(UTC)
        assert db.scalar(select(func.count()).select_from(AgentRun)) == 1
        assert not db.scalar(select(Message.id).where(Message.kind == "teacher_response"))
    approved = review(client, run, "approve", body="Teacher reviewed this email.")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"


def test_email_thread_isolates_history_and_keeps_original_message(
    rig, scenario, current_history, db_engine
):
    client, model, _, _ = rig

    def send(thread_id, body):
        response = client.post(
            "/api/v1/incoming-emails",
            json={
                "from": "alex@example.com",
                "body": body,
                "thread_id": thread_id,
                "subject": "Same subject",
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = send("thread-a", "Original message in this thread.")
    other = send("thread-b", "Thread B private marker.")
    assert first["conversation_id"] != other["conversation_id"]
    assert client.get(f"/api/v1/agent-runs/{first['id']}").json()["status"] == "awaiting_review"

    reply = review(client, first, "approve", body="Teacher-approved response.")
    assert reply.status_code == 200, reply.text
    followup = send("thread-a", "Follow up.")
    last = send("thread-a", "Third email.")
    context = model.routing_contexts[-1]
    assert last["conversation_id"] == followup["conversation_id"] == first["conversation_id"]
    assert [item["id"] for item in context["history"]] == [
        first["source_message_id"],
        followup["source_message_id"],
        last["source_message_id"],
    ]
    assert len(context["approved_replies"]) == 1
    approved = context["approved_replies"][0]
    assert approved["delivery"] == "unconfirmed"
    assert approved["body"] == "Teacher-approved response."
    assert other["conversation_id"] not in str(context)
    assert client.get(f"/api/v1/agent-runs/{other['id']}").json()["status"] == "awaiting_review"

    before = counts(db_engine)
    collision = client.post(
        "/api/v1/incoming-emails",
        json={"from": "unknown@example.com", "body": "Unrelated", "thread_id": "thread-a"},
    )
    assert collision.status_code == 409
    assert counts(db_engine) == before
    legacy = submit(client)
    assert legacy.json()["conversation_id"] == str(scenario["conversation"])
    with Session(db_engine) as db:
        original_thread = db.get(Conversation, UUID(first["conversation_id"]))
        assert original_thread.subject == "Same subject"


def test_context_limit_requires_manual_review(rig, monkeypatch):
    client, model, _, _ = rig

    def overflow(context):
        raise ModelContextLimitError("provider details")

    monkeypatch.setattr(model, "route", overflow)
    response = submit(client, sender="long-thread@example.com")
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "failed"
    assert "Review this thread manually" in run["error"]
    assert "provider details" not in run["error"]
    assert run["draft_details"].get("booking_session_id") is None
    assert review(client, run, "approve", expected_revision=1).status_code == 409
    assert review(client, run, "reject").json()["status"] == "closed"


def test_known_student_without_conversation_gets_one(rig, db_engine):
    with Session(db_engine) as db, db.begin():
        student = Student(display_name="Existing", email="existing@example.com")
        db.add(student)
        db.flush()
        student_id = student.id
    response = submit(rig[0], "existing@example.com")
    assert response.status_code == 200, response.text
    with Session(db_engine) as db:
        conversation = db.get(Conversation, UUID(response.json()["conversation_id"]))
        assert conversation.student_id == student_id
        assert (
            db.scalar(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.student_id == student_id)
            )
            == 1
        )


def test_latest_conversation_is_selected(rig, scenario, current_history, db_engine):
    with Session(db_engine) as db, db.begin():
        db.get(Conversation, scenario["conversation"]).created_at = datetime(2020, 1, 1, tzinfo=UTC)
        latest = Conversation(student_id=scenario["student"], subject="Latest enquiry")
        db.add(latest)
        db.flush()
        latest_id = latest.id
    response = submit(rig[0])
    assert response.status_code == 200, response.text
    assert response.json()["conversation_id"] == str(latest_id)


def test_unknown_sender_first_email_handoff_and_followup_routing(rig, db_engine):
    client, model, _, _ = rig
    model.routing = Routing(
        intents=["new_student_enquiry"],
        action="information_only",
        request_summary="New dancer asks where to start.",
        needs_clarification=False,
        reason="Information without a booking request.",
    )
    before = counts(db_engine)
    first = submit(client, "New.Person@example.com", "I have never danced before.")
    assert first.status_code == 200, first.text
    run = first.json()
    assert run["status"] == "awaiting_review", run
    assert run["interpretation"]["flow"] == "enquiry"
    assert run["interpretation"]["routing"]["intents"] == ["new_student_enquiry"]
    assert model.contexts == []
    assert run["draft_details"]["booking_session_id"] is None
    with Session(db_engine) as db:
        student = db.scalar(select(Student).where(Student.email == "new.person@example.com"))
        assert student is not None
        assert student.display_name == "New enquirer"
        assert student.highest_level is None
        assert student.enrolment_history == []
    assert len(model.routing_contexts) == 1
    assert model.enquiry_contexts[0]["source"]["body"] == "I have never danced before."
    model.routing = None
    second = submit(client, "NEW.PERSON@example.com", "Would Saturday work for a beginner?")
    assert second.status_code == 200, second.text
    followup = second.json()
    assert followup["conversation_id"] == run["conversation_id"]
    assert followup["source_message_id"] != run["source_message_id"]
    assert followup["interpretation"]["flow"] == "makeup"
    assert followup["interpretation"]["routing"]["intents"] == ["makeup", "absence"]
    assert counts(db_engine)[:2] == (before[0] + 1, before[1] + 1)
    assert client.get(f"/api/v1/agent-runs/{run['id']}").json()["status"] == "superseded"
    assert len(model.contexts) == 1
    assert any(
        message["body"] == "I have never danced before."
        for message in model.routing_contexts[-1]["history"]
    )


@pytest.mark.parametrize("authorization", ["", "Bearer wrong"])
def test_auth_failure_has_no_writes(rig, db_engine, authorization):
    before = counts(db_engine)
    response = submit(rig[0], headers={"Authorization": authorization})
    assert response.status_code == 401
    assert counts(db_engine) == before


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"from": "not-an-email", "body": "Hello"},
        {"from": "alex@example.com", "body": "   "},
        {"from": "alex@example.com", "body": "Hello", "occurred_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_invalid_input_has_no_writes(rig, db_engine, payload):
    before = counts(db_engine)
    response = rig[0].post("/api/v1/incoming-emails", json=payload)
    assert response.status_code == 422, response.text
    assert counts(db_engine) == before


def test_busy_student_has_no_writes(rig, scenario, current_history, db_engine):
    before = counts(db_engine)
    with student_lock(db_engine, scenario["student"]):
        response = submit(rig[0])
    assert response.status_code == 409, response.text
    assert counts(db_engine) == before


def test_policy_failure_has_no_writes_even_for_unknown_sender(rig, db_engine, tmp_path):
    rig[2].policy_path = tmp_path / "missing-policy.yaml"
    before = counts(db_engine)
    response = submit(rig[0], "new@example.com")
    assert response.status_code == 503, response.text
    assert counts(db_engine) == before


def test_future_dated_history_rejects_without_writes(rig, scenario, current_history, db_engine):
    with Session(db_engine) as db, db.begin():
        db.get(Message, scenario["source"]).occurred_at = datetime(2099, 1, 1, tzinfo=UTC)
    before = counts(db_engine)
    response = submit(rig[0])
    assert response.status_code == 409, response.text
    assert counts(db_engine) == before


def test_processing_failure_keeps_email_and_retry_reuses_run(rig, current_history, db_engine):
    client, model, _, _ = rig
    model.fail_interpret = True
    response = submit(client)
    assert response.status_code == 200, response.text
    failed = response.json()
    assert failed["status"] == "failed", failed
    assert failed["error"]
    before = counts(db_engine)
    model.fail_interpret = False
    retry = client.post(f"/api/v1/agent-runs/{failed['id']}/retry")
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "awaiting_review"
    assert retry.json()["source_message_id"] == failed["source_message_id"]
    after = counts(db_engine)
    assert after[:2] == before[:2]
    assert after[3] == before[3]
    with Session(db_engine) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "student_email")
            )
            == 2
        )


def test_new_sender_marker_survives_failed_checkpoint_startup(rig, db_engine):
    client, model, service, _ = rig
    model.routing = Routing(
        intents=["new_student_enquiry"],
        action="information_only",
        request_summary="New dancer enquiry",
        needs_clarification=False,
        reason="Information only",
    )
    original = service.checkpoints

    def unavailable():
        raise RuntimeError("Synthetic checkpoint outage")

    service.checkpoints = unavailable
    try:
        response = submit(client, "new@example.com", "I am new to ballet.")
    finally:
        service.checkpoints = original
    assert response.status_code == 200, response.text
    failed = response.json()
    assert failed["status"] == "failed"
    assert failed["interpretation"]["intake"]["new_sender"] is True
    before = counts(db_engine)
    retried = client.post(f"/api/v1/agent-runs/{failed['id']}/retry")
    assert retried.status_code == 200, retried.text
    run = retried.json()
    assert run["status"] == "awaiting_review", run
    assert run["interpretation"]["routing"]["intents"] == ["new_student_enquiry"]
    assert len(model.routing_contexts) == 1
    assert run["interpretation"]["flow"] == "enquiry"
    assert model.contexts == []
    assert counts(db_engine)[:2] == before[:2]
    assert counts(db_engine)[3] == before[3]


def test_concurrent_first_contact_does_not_duplicate_student_or_conversation(rig, db_engine):
    client, model, _, _ = rig
    entered, release = Event(), Event()
    original = model.draft

    def paused_draft(context):
        entered.set()
        assert release.wait(timeout=10), "Concurrent request did not finish"
        return original(context)

    model.draft = paused_draft
    before = counts(db_engine)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(submit, client, "concurrent@example.com", "I am new to ballet.")
        try:
            assert entered.wait(timeout=10), "First request did not reach drafting"
            second = submit(client, "CONCURRENT@example.com", "Another email")
            assert second.status_code == 409, second.text
        finally:
            release.set()
        response = first.result(timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "awaiting_review", response.json()
    after = counts(db_engine)
    assert after[:2] == (before[0] + 1, before[1] + 1)
    assert after[3] == before[3] + 1
    with Session(db_engine) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.body == "Another email")
            )
            == 0
        )


@pytest.mark.parametrize("missing", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_missing_model_configuration_has_no_writes(db_engine, monkeypatch, missing):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-test-model")
    monkeypatch.delenv(missing, raising=False)
    before = counts(db_engine)
    with TestClient(
        create_app(db_engine, admin_token="test"),
        headers={"Authorization": "Bearer test"},
    ) as client:
        response = submit(client, "new@example.com", "I would like to try ballet.")
    assert response.status_code == 503, response.text
    assert counts(db_engine) == before
