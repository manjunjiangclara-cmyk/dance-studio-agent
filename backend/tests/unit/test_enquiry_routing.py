"""Routing selects the requested capability independently of student identity."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from studio_copilot.agent.contracts import Draft, EnquiryAnswer, EnquiryInterpretation, Routing
from studio_copilot.agent.enquiry import safe_body, validate_answers
from studio_copilot.agent.tools import tool_definitions
from studio_copilot.agent.workflow.nodes import WorkflowNodes, select_flow


@pytest.mark.parametrize(
    "intents,action,flow",
    [
        (["new_student_enquiry"], "information_only", "enquiry"),
        (["general_enquiry"], "information_only", "enquiry"),
        (["makeup"], "information_only", "enquiry"),
        (["enrolment"], "information_only", "enquiry"),
        (["absence", "makeup"], "makeup_booking", "makeup"),
        (["makeup"], "makeup_booking", "makeup"),
        (["makeup", "enrolment"], "makeup_booking", "teacher_handoff"),
        (["enrolment"], "makeup_booking", "teacher_handoff"),
        (["general_enquiry"], "other_action", "teacher_handoff"),
        (["makeup"], "unclear", "teacher_handoff"),
    ],
)
def test_requested_action_selects_flow(intents, action, flow):
    routing = Routing(
        intents=intents,
        action=action,
        request_summary="Synthetic request",
        needs_clarification=action == "unclear",
        reason="Synthetic classification",
    )
    assert select_flow(routing) == flow


@pytest.mark.parametrize("new_sender", [False, True])
def test_first_contact_uses_the_same_router(new_sender):
    calls, saved = [], []
    routing = Routing(
        intents=["makeup"],
        action="information_only",
        request_summary="How do makeup classes work?",
        needs_clarification=False,
        reason="An informational question without a booking request.",
    )

    def route(context):
        calls.append(context)
        return routing

    nodes = WorkflowNodes(
        SimpleNamespace(engine=None, save_routing=lambda *args: saved.append(args)),
        SimpleNamespace(route=route),
    )
    context = {
        "source": {"body": "How do makeup classes work?"},
        "student": {"name": "Synthetic student"},
        "intake": {"new_sender": new_sender},
    }
    result = nodes.route({"run_id": "synthetic-run", "context": context})
    assert calls == [context]
    assert result["flow"] == "enquiry"
    assert result["routing"]["action"] == "information_only"
    assert saved[0][1] == result["routing"]


def test_old_routing_payload_defaults_to_unclear():
    routing = Routing(
        intents=["makeup"],
        request_summary="An old saved classification",
        needs_clarification=False,
        reason="Legacy payload without an action field",
    )
    assert routing.action == "unclear"
    assert select_flow(routing) == "teacher_handoff"


def test_enquiry_model_only_sees_live_information_tools():
    assert {item["name"] for item in tool_definitions("enquiry")} == {
        "get_timetable",
        "search_sessions",
        "get_locations",
    }
    assert "get_enrolments" in {item["name"] for item in tool_definitions("teacher_handoff")}


@pytest.mark.parametrize(
    "reference,feedback,status",
    [
        ("policy:test", "", "answered"),
        ("teacher_feedback", "", "needs_teacher"),
        ("teacher_feedback", "   ", "needs_teacher"),
        ("teacher_feedback", "The fee is confirmed by the teacher.", "answered"),
    ],
)
def test_answers_require_current_policy_or_actual_teacher_feedback(reference, feedback, status):
    question = "What is the studio policy?"
    draft = Draft(
        body="A supported response.",
        rationale="Synthetic evidence test",
        questions=[],
        references=[reference],
        answers=[
            EnquiryAnswer(
                question=question,
                status="answered",
                answer="A supported response.",
                references=[reference],
            )
        ],
    )
    result = validate_answers(
        draft,
        {
            "flow": "enquiry",
            "context": {"policy": {"version": "test"}},
            "interpretation": {"questions": [question], "requested_actions": []},
            "evidence": [],
            "feedback": feedback,
        },
    )
    assert result.answers[0].status == status


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_extracted_questions_cannot_break_answer_validation(question):
    try:
        interpretation = EnquiryInterpretation(
            request_summary="Synthetic enquiry",
            missing_details=[],
            enduring_preferences=[],
            questions=[question],
            requested_actions=[],
        )
    except ValidationError:
        return
    assert all(0 < len(item.strip()) <= 2000 for item in interpretation.questions)


@pytest.mark.parametrize("status", ["answered", "needs_student", "needs_teacher"])
def test_blank_answer_text_has_an_explicit_teacher_review_fallback(status):
    question = "Which class suits my experience?"
    draft = Draft(
        body="An unverified reply.",
        rationale="Synthetic blank answer",
        questions=[],
        references=[],
        answers=[EnquiryAnswer(question=question, status=status, answer="   ", references=[])],
    )
    result = validate_answers(
        draft,
        {
            "flow": "enquiry",
            "context": {"policy": {"version": "test"}},
            "interpretation": {"questions": [question], "requested_actions": []},
            "evidence": [],
        },
    )
    assert result.answers[0].status == "needs_teacher"
    assert result.answers[0].answer.strip()
    assert "unverified reply" not in result.body


def test_conservative_body_stays_within_the_review_body_limit():
    answers = [
        EnquiryAnswer(
            question=f"Question {index}",
            status="answered",
            answer="A" * 4000,
            references=["policy:test"],
        )
        for index in range(20)
    ]
    body = safe_body(answers, [])
    assert body.strip()
    assert len(body) <= 20_000
