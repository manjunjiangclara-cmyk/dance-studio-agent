from uuid import uuid4

import pytest
from fastapi import HTTPException

from studio_copilot.public_demo.service import PublicDemo
from studio_copilot.public_demo.trial import initial_state, strip_quotes, update_state


class ThreadModel:
    contexts = []

    def call(self, scenario, stage, evidence, *, context):
        self.contexts.append(context)
        if stage == "evidence":
            return {
                "evidence": ["Fictional policy"],
                "route": "enquiry",
                "model": "fake",
                "missing_information": [],
                "student_information": [],
                "workflow_extraction": {
                    "intents": ["trial_enquiry", "faq"],
                    "experience_level": "intermediate",
                    "preferred_day": "Saturday",
                },
            }
        return {"body": "Draft", "model": "fake"}

    def close(self):
        pass


def test_thread_history_isolation_and_retry(tmp_path):
    ThreadModel.contexts = []
    service = PublicDemo(tmp_path / "demo.sqlite", factory=ThreadModel)
    a = service.create_thread("new")["token"]
    b = service.create_thread("new")["token"]
    first = str(uuid4())
    message = "I am intermediate, Saturday. What should I wear?"
    service.add_turn(a, first, message)
    assert service.add_turn(a, first, message) == {"request_id": first}
    with pytest.raises(HTTPException):
        service.add_turn(b, first, message)
    service.thread_execute(a, first, "evidence")
    service.thread_execute(a, first, "draft")
    service.accept_reply(a, first, "Edited reply")
    second = str(uuid4())
    service.add_turn(a, second, "Yes please\nOn Tuesday someone wrote:\n> old text")
    service.thread_execute(a, second, "evidence")
    context = ThreadModel.contexts[-1]
    assert context["thread_history"] == [{"email": message, "reply": "Edited reply"}]
    assert context["email_body"] == "Yes please"
    assert service.thread_view(b)["turns"] == []
    assert len(PublicDemo(service.path, factory=ThreadModel).thread_view(a)["turns"]) == 2


def test_workflow_requires_explicit_consent_and_appropriate_class():
    state = update_state(
        initial_state(),
        {"intents": ["trial_enquiry"], "experience_level": "beginner", "preferred_day": "Saturday"},
        "I am a beginner",
    )
    assert state["booking_status"] == "escalated"
    assert state["recommended_class"] is None
    state = update_state(
        initial_state(),
        {
            "intents": ["trial_enquiry"],
            "experience_level": "intermediate",
            "preferred_day": "Saturday",
        },
        "I am intermediate",
    )
    assert state["booking_status"] == "offered"
    rejected = update_state(state, {"customer_name": "Alex"}, "No, please don't book it")
    assert rejected["booking_status"] != "awaiting_approval"
    requested = update_state(
        state,
        {"customer_name": "Alex"},
        "Yes, please",
        True,
    )
    assert requested["booking_status"] == "awaiting_approval"


def test_quote_recognition_is_conservative():
    assert strip_quotes("Hello\nOn Tuesday Pat wrote:\n> old") == "Hello"
    assert strip_quotes("Hello\nMaybe you wrote this") == "Hello\nMaybe you wrote this"


def test_approval_is_revision_bound_and_idempotent(tmp_path):
    class Model(ThreadModel):
        def call(self, scenario, stage, evidence, *, context):
            if stage == "draft":
                return {
                    "body": "Would you like a trial in Level 2 on Saturday 13 February 2027?",
                    "model": "fake",
                }
            extracted = {
                "intents": ["trial_enquiry"],
                "experience_level": None,
                "preferred_day": None,
                "customer_name": None,
            }
            if not context["thread_history"]:
                extracted.update(experience_level="intermediate", preferred_day="Saturday")
            else:
                extracted["customer_name"] = "Alex"
            return {
                "evidence": ["Class information"],
                "route": "enquiry",
                "model": "fake",
                "missing_information": [],
                "student_information": [],
                "workflow_extraction": extracted,
            }

    service = PublicDemo(tmp_path / "demo.sqlite", factory=Model)
    token = service.create_thread("new")["token"]
    first = str(uuid4())
    service.add_turn(token, first, "I am intermediate and available Saturday.")
    service.thread_execute(token, first, "evidence")
    service.thread_execute(token, first, "draft")
    service.accept_reply(
        token, first, "Would you like a trial in Level 2 on Saturday 13 February 2027?", True
    )
    second = str(uuid4())
    service.add_turn(token, second, "Yes please")
    service.thread_execute(token, second, "evidence")
    state = service.thread_view(token)["state"]
    assert state["booking_status"] == "awaiting_approval"
    with pytest.raises(HTTPException):
        service.approve_mock(token, state["revision"])
    service.thread_execute(token, second, "draft")
    service.accept_reply(token, second, "Your request is for review.")
    with pytest.raises(HTTPException):
        service.approve_mock(token, state["revision"] - 1)
    first_approval = service.approve_mock(token, state["revision"])
    assert first_approval["state"]["booking_status"] == "approved_mock"
    assert service.approve_mock(token, state["revision"]) == first_approval


def test_consent_is_tied_to_the_specific_offer_and_cannot_survive_changed_mind():
    offered = update_state(
        initial_state(),
        {
            "intents": ["trial_enquiry"],
            "experience_level": "intermediate",
            "preferred_day": "Saturday",
        },
        "Intermediate Saturday",
    )
    assert (
        update_state(offered, {"customer_name": "Alex"}, "Yes", False)["booking_status"]
        == "offered"
    )
    assert (
        update_state(
            offered, {"customer_name": "Alex"}, "Please book the Monday class instead", True
        )["booking_status"]
        != "awaiting_approval"
    )
    assert (
        update_state(offered, {}, "Yes, can you tell me the price before I decide?", True)[
            "booking_status"
        ]
        == "offered"
    )
    assert (
        update_state(offered, {}, "Yes, I want to wait until next month", True)["booking_status"]
        == "offered"
    )
    collecting = update_state(offered, {}, "Yes, I'd love to", True)
    assert collecting["booking_status"] == "collecting_name"
    changed = update_state(
        collecting, {"customer_name": "Alex"}, "My name is Alex, but I changed my mind"
    )
    assert changed["booking_status"] != "awaiting_approval"
    pending = update_state(collecting, {"customer_name": "Alex"}, "My name is Alex")
    assert pending["booking_status"] == "awaiting_approval"
    approved = {**pending, "booking_status": "approved_mock", "next_action": "complete"}
    assert (
        update_state(approved, {"intents": ["faq"]}, "What should I wear?")["booking_status"]
        == "approved_mock"
    )
    assert (
        update_state(pending, {"intents": ["faq"]}, "What should I wear?")["booking_status"]
        == "awaiting_approval"
    )


def test_quotes_include_outlook_and_prefixed_lines():
    assert strip_quotes("New text\n> Old text\nNew paragraph") == "New text\nNew paragraph"
    assert strip_quotes("New text\nFrom: sender@example.com\nSent: Monday\nold") == "New text"


def test_thread_api_origin_and_round_trip(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from studio_copilot.api import public_demo as api

    monkeypatch.setenv("STUDIO_PUBLIC_LIVE_DEMO", "true")
    monkeypatch.setenv("STUDIO_PUBLIC_DEMO_DB", str(tmp_path / "api.sqlite"))
    monkeypatch.setenv("OPENAI_MODEL", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    monkeypatch.setattr(api, "PublicDemo", lambda path: PublicDemo(path, factory=ThreadModel))
    client = TestClient(api.create_public_demo_app())
    assert client.post("/api/public-demo/threads", json={"student": "new"}).status_code == 403
    headers = {"Origin": "http://localhost:8000"}
    created = client.post("/api/public-demo/threads", json={"student": "new"}, headers=headers)
    assert created.status_code == 200
    headers["Authorization"] = "Bearer " + created.json()["token"]
    turn_id = str(uuid4())
    assert (
        client.post(
            "/api/public-demo/threads/current/turns",
            headers=headers,
            json={"request_id": turn_id, "email_body": "Hello"},
        ).status_code
        == 200
    )
    view = client.post("/api/public-demo/threads/current", headers=headers, json={})
    assert view.status_code == 200
    assert view.json()["turns"][0]["email"] == "Hello"
    evidence = client.post(
        f"/api/public-demo/threads/current/turns/{turn_id}/evidence", headers=headers, json={}
    )
    assert evidence.status_code == 200
