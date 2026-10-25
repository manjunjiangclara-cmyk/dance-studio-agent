from uuid import UUID

import pytest

from studio_copilot.agent.contracts import (
    Routing,
)

from .helpers import review, start

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "intents,unclear",
    [
        (["enrolment"], False),
        (["cancellation"], False),
        (["new_student_enquiry"], False),
        (["general_enquiry"], False),
        (["absence"], False),
        (["unknown"], True),
        (["makeup", "enrolment"], False),
        (["makeup"], True),
    ],
)
def test_other_or_ambiguous_intents_bypass_makeup_interpreter_and_tools(
    rig, scenario, intents, unclear
):
    client, model, _, _ = rig
    model.routing = Routing(
        intents=intents,
        request_summary="Student asks to change their regular enrolment.",
        needs_clarification=unclear,
        reason="This needs a different workflow or teacher clarification.",
    )
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert run["interpretation"]["routing"]["intents"] == intents
    assert "absence_date" not in run["interpretation"]
    assert "preferred_weekday" not in run["interpretation"]
    assert model.contexts == []  # Makeup interpreter was never called.
    assert model.query_count == 0
    assert run["evidence"] == []
    assert "makeup" not in run["draft_details"]["body"].lower()
    profile = client.get(f"/api/v1/students/{scenario['student']}").json()
    assert "regular enrolment" in profile["ai_summary"]
    # Existing approval/memory behavior remains available for a teacher-written response.
    approved = review(client, run, "approve", body="I will discuss the enrolment options with you.")
    assert approved.json()["status"] == "approved", approved.text


def test_router_uses_followup_history_and_keeps_absence_makeup_together(rig, scenario):
    client, model, _, _ = rig
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "makeup"
    assert run["interpretation"]["routing"]["intents"] == ["makeup", "absence"]
    email = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={
            "kind": "student_email",
            "body": "Actually, Saturday instead.",
            "occurred_at": "2027-02-07T11:00:00+11:00",
        },
    ).json()
    start(rig, dict(scenario, source=UUID(email["id"])))
    latest_context = model.routing_contexts[-1]
    assert latest_context["source"]["body"] == "Actually, Saturday instead."
    assert any(message["body"] == "Thursday please" for message in latest_context["history"])
    assert latest_context["student"]["ai_summary"]


def test_router_failure_creates_teacher_handoff_without_makeup_queries(rig, scenario):
    model = rig[1]
    model.fail_route = True
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert run["interpretation"]["routing"]["intents"] == ["unknown"]
    assert model.query_count == 0
    assert model.contexts == []


def test_handoff_draft_failure_never_uses_makeup_clarification_template(rig, scenario):
    model = rig[1]
    model.routing = Routing(
        intents=["enrolment"],
        request_summary="Change regular enrolment next term.",
        needs_clarification=False,
        reason="An enrolment workflow is needed.",
    )
    model.fail_draft = True
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert "makeup" not in run["draft_details"]["body"].lower()
    assert model.query_count == 0
