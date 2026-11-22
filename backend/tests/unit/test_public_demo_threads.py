from uuid import uuid4

import pytest
from fastapi import HTTPException

from studio_copilot.public_demo import availability
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
    evidence = service.thread_execute(a, first, "evidence")
    assert "10 places remaining" in evidence["evidence"][0]
    service.thread_execute(a, first, "draft")
    assert ThreadModel.contexts[-1]["trial_spaces_remaining"] == 10
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
        {"intents": ["trial_enquiry"], "experience_level": "beginner", "preferred_day": "Monday"},
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


@pytest.mark.parametrize(("experience", "level"), [("beginner", 1), ("advanced", 3)])
def test_saturday_trial_offer_matches_the_students_reported_level(experience, level):
    offer = update_state(
        initial_state(),
        {
            "intents": ["trial_enquiry"],
            "experience_level": experience,
            "preferred_day": "Saturday",
        },
        "Can I try the Saturday class?",
    )
    assert offer["booking_status"] == "offered"
    assert f"Adult Ballet Level {level}," in offer["recommended_class"]["description"]
    changed_level = "advanced" if level == 1 else "beginner"
    changed = update_state(offer, {"experience_level": changed_level}, "Yes, please", True)
    assert changed["recommended_class"] != offer["recommended_class"]
    assert changed["booking_status"] == "offered"


def test_quote_recognition_is_conservative():
    assert strip_quotes("Hello\nOn Tuesday Pat wrote:\n> old") == "Hello"
    assert strip_quotes("Hello\nMaybe you wrote this") == "Hello\nMaybe you wrote this"


def test_explicit_trial_class_and_confirmation_do_not_depend_on_inferred_placement():
    previous = update_state(
        initial_state(),
        {"intents": ["trial_enquiry"], "experience_level": "one year of training"},
        "I have done one year of ballet. Can I book intermediate class?",
    )
    assert previous["booking_status"] == "collecting"
    level_request = "Can you book level 1 for me instead"
    confirmation = "Yes please help me book it"
    offer = update_state(previous, {}, level_request)
    assert offer["requested_trial_level"] == 1
    assert offer["experience_level"] == "one year of training"
    assert offer["preferred_day"] is None
    assert offer["booking_status"] == "offered"
    assert (
        "Adult Ballet Level 1, Saturday 13 February 2027 at 4 pm"
        in (offer["recommended_class"]["description"])
    )
    assert update_state(offer, {}, confirmation)["booking_status"] == "offered"
    assert update_state(offer, {}, confirmation, True)["booking_status"] == "collecting_name"
    named = {**offer, "customer_name": "Riley James"}
    assert update_state(named, {}, confirmation, True)["booking_status"] == "awaiting_approval"
    changed = update_state(named, {}, "Yes, please book Level 3 instead", True)
    assert changed["requested_trial_level"] == 3
    assert changed["booking_status"] == "offered"

    legacy = update_state(previous, {}, confirmation, previous_email=level_request)
    assert legacy["recommended_class"] == offer["recommended_class"]
    assert legacy["booking_status"] == "offered"
    different_day = update_state(previous, {"preferred_day": "Thursday"}, level_request)
    assert different_day["booking_status"] == "escalated"


def test_recorded_level_prevents_a_higher_trial_offer():
    extracted = {
        "intents": ["trial_enquiry"],
        "experience_level": "advanced",
        "preferred_day": "Saturday",
    }
    offered = update_state(initial_state(), extracted, "Can I try Level 3 on Saturday?")
    assert offered["booking_status"] == "offered"
    assert "Level 3" in offered["recommended_class"]["description"]
    blocked = update_state(initial_state(), extracted, "Can I try Level 3?", recorded_level=2)
    assert blocked["booking_status"] == "escalated"
    assert blocked["recommended_class"] is None
    pending = {**offered, "booking_status": "awaiting_approval"}
    blocked_saved_offer = update_state(pending, {}, "Yes please", True, recorded_level=2)
    assert blocked_saved_offer["booking_status"] == "escalated"
    assert blocked_saved_offer["recommended_class"] is None


@pytest.mark.parametrize("capacity", [1, 2])
def test_trial_does_not_offer_a_session_with_no_places(monkeypatch, capacity):
    session_id = next(iter(availability.TRIAL_SESSION_IDS.values()))
    monkeypatch.setattr(
        availability,
        "_demo_sessions",
        lambda: {session_id: {"capacity": capacity, "students": ["a", "b"]}},
    )
    state = update_state(
        initial_state(),
        {"intents": ["trial_enquiry"], "experience_level": "beginner", "preferred_day": "Saturday"},
        "Can I try the Saturday class?",
    )
    assert state["booking_status"] == "class_full"
    assert availability.trial_spaces(state["recommended_class"]) == 0


def test_reported_training_duration_does_not_establish_a_trial_level():
    previous = {
        **initial_state(),
        "intents": ["trial_enquiry"],
        "experience_level": "One year of training",
        "preferred_day": "Saturday",
        "booking_status": "escalated",
    }
    offer = update_state(previous, {}, "Saturday works for me.")
    assert offer["experience_level"] == "One year of training"
    assert offer["booking_status"] == "escalated"
    assert offer["recommended_class"] is None


@pytest.mark.parametrize(
    "experience, day",
    [
        ("Beginner with one year of training", "Saturday"),
        ("One year ago", "Saturday"),
        ("No training", "Saturday"),
        ("One year of training", "Monday"),
    ],
)
def test_reported_training_duration_does_not_offer_an_unmatched_class(experience, day):
    state = update_state(
        initial_state(),
        {"intents": ["trial_enquiry"], "experience_level": experience, "preferred_day": day},
        "Tell me about trials.",
    )
    assert state["booking_status"] == "escalated"
    assert state["recommended_class"] is None


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
    assert service.thread_view(token)["turns"][0]["offer_confirmed"] is True
    assert service.thread_view(token)["turns"][0]["offer_confirmed"] is True
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
    monkeypatch.setattr(
        api, "PublicDemo", lambda path, **options: PublicDemo(path, factory=ThreadModel, **options)
    )
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


def test_failed_draft_restores_bound_teacher_answers(tmp_path):
    class FailingDraft(ThreadModel):
        def call(self, scenario, stage, evidence, *, context):
            if stage == "draft":
                raise ValueError("temporary failure")
            result = super().call(scenario, stage, evidence, context=context)
            result["missing_information"] = ["Trial fee"]
            return result

    service = PublicDemo(tmp_path / "demo.sqlite", factory=FailingDraft)
    token = service.create_thread("new")["token"]
    turn = str(uuid4())
    service.add_turn(token, turn, "What is the trial fee?")
    service.thread_execute(token, turn, "evidence")
    with pytest.raises(HTTPException) as error:
        service.thread_execute(token, turn, "draft", teacher_answers=["I will confirm."])
    assert error.value.status_code == 502
    restored = PublicDemo(service.path, factory=FailingDraft).thread_view(token)
    assert restored["turns"][0]["draft_answers"] == ["I will confirm."]
    with pytest.raises(HTTPException) as error:
        service.thread_execute(token, turn, "draft", teacher_answers=["Changed"])
    assert error.value.status_code == 409


@pytest.mark.parametrize("admission", ["thread", "legacy"])
def test_admission_cleans_up_expired_conversation_data(tmp_path, admission):
    now = 1_800_000_000
    service = PublicDemo(tmp_path / "demo.sqlite", factory=ThreadModel, clock=lambda: now)
    token = service.create_thread("new")["token"]
    turn = str(uuid4())
    service.add_turn(token, turn, "Fictional email")
    with service.db() as db:
        db.execute("UPDATE threads SET created=? WHERE token=?", (now - 4 * 86400, token))
        db.execute("UPDATE runs SET created=? WHERE request_id=?", (now - 4 * 86400, turn))
    if admission == "thread":
        service.create_thread("new")
    else:
        service.create("booking", str(uuid4()))
    with service.db() as db:
        assert (
            db.execute("SELECT count(*) FROM runs WHERE request_id=?", (turn,)).fetchone()[0] == 0
        )
        assert (
            db.execute("SELECT count(*) FROM turns WHERE request_id=?", (turn,)).fetchone()[0] == 0
        )
