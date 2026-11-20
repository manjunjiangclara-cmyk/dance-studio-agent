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
        state, {"customer_name": "Alex"}, "Yes, please", "Would you like a trial in Level 2?"
    )
    assert requested["booking_status"] == "awaiting_approval"


def test_quote_recognition_is_conservative():
    assert strip_quotes("Hello\nOn Tuesday Pat wrote:\n> old") == "Hello"
    assert strip_quotes("Hello\nMaybe you wrote this") == "Hello\nMaybe you wrote this"


def test_approval_is_revision_bound_and_idempotent(tmp_path):
    class Model(ThreadModel):
        def call(self, scenario, stage, evidence, *, context):
            if stage == "draft":
                return {"body": "Would you like a trial in Level 2?", "model": "fake"}
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
    service.accept_reply(token, first, "Would you like a trial in Level 2?")
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
