"""Protect the fixtures and grading expectations for enquiry evaluations."""

from copy import deepcopy

import pytest

from evaluations.cases import CATALOG, POLICY, load_scenarios
from evaluations.grading import grade_run
from studio_copilot.agent.policy import load_policy


@pytest.fixture
def scenarios():
    return {item.id: item for item in load_scenarios()}


def test_enquiry_scenarios_declare_distinct_routing_and_student_fixtures(scenarios):
    for name, registered, flow, action in [
        ("new_student_how_to_enrol", False, "enquiry", "information_only"),
        ("existing_student_how_to_enrol", True, "enquiry", "information_only"),
        ("new_student_enrolment_request", False, "teacher_handoff", "other_action"),
        ("enquiry_and_enrolment_request", True, "teacher_handoff", "other_action"),
    ]:
        case = scenarios[name]
        assert case.setup.student.registered is registered
        assert case.steps[0].expected.interpretation.flow == flow
        assert case.steps[0].expected.interpretation.routing.action == action


def test_three_question_fixture_declares_each_status_and_unknown_sources(scenarios):
    case = scenarios["enquiry_three_information_states"]
    assert [check.status for check in case.steps[0].checks.question_answer_checks] == [
        "answered",
        "needs_student",
        "needs_teacher",
    ]
    assert not case.setup.student.registered
    sources = (CATALOG.read_text() + str(load_policy(POLICY))).casefold()
    assert not any(term in sources for term in ["wednesday", "clothing", "uniform", "footwear"])


def test_question_checks_detect_a_dropped_or_misclassified_answer(scenarios):
    step = scenarios["enquiry_time_and_location"].steps[0]
    run = {
        "status": "awaiting_review",
        "interpretation": {"flow": "enquiry", "routing": {"action": "information_only"}},
        "draft_details": {
            "body": "Thursday starts at 6 pm at 100 Fictional Lane.",
            "answers": [
                {"question": "What time does it start?", "status": "answered"},
                {"question": "Where is it held?", "status": "answered"},
            ],
        },
    }

    def results(value):
        return {item["name"]: item["passed"] for item in grade_run(value, step, {"dates": {}})}

    assert results(run)["question_answer:0:status"]
    assert results(run)["question_answer:1:status"]
    missing = deepcopy(run)
    missing["draft_details"]["answers"].pop()
    assert not results(missing)["question_answer:1:present"]
    wrong = deepcopy(run)
    wrong["draft_details"]["answers"][0]["status"] = "needs_teacher"
    assert not results(wrong)["question_answer:0:status"]


def test_unknown_question_rejects_unrelated_reference_and_missing_match(scenarios):
    step = scenarios["enquiry_unknown_class"].steps[0]
    run = {
        "draft_details": {
            "answers": [
                {
                    "question": "When does the Wednesday beginner class start?",
                    "status": "needs_teacher",
                    "references": [],
                }
            ]
        }
    }

    def results(value):
        return {item["name"]: item["passed"] for item in grade_run(value, step, {"dates": {}})}

    assert results(run)["question_answer:0:no_unrelated_references"]
    run["draft_details"]["answers"][0]["references"] = ["class:unrelated"]
    assert not results(run)["question_answer:0:no_unrelated_references"]
    run["draft_details"]["answers"] = []
    assert not results(run)["question_answer:0:present"]
    assert not results(run)["question_answer:0:no_unrelated_references"]


def test_question_selectors_cannot_be_blank():
    from pydantic import ValidationError

    from evaluations.cases import QuestionAnswerCheck

    for terms in ([], [""], ["   "]):
        with pytest.raises(ValidationError):
            QuestionAnswerCheck(question_terms=terms, status="needs_teacher")


def test_one_answer_cannot_satisfy_two_question_checks(scenarios):
    step = scenarios["enquiry_time_and_location"].steps[0]
    run = {
        "draft_details": {
            "answers": [
                {"question": "What time and where is the class held?", "status": "answered"}
            ]
        }
    }
    checks = {c["name"]: c["passed"] for c in grade_run(run, step, {"dates": {}})}
    assert checks["question_answer:0:status"]
    assert checks["question_answer:1:status"]
    assert not checks["distinct_question_answers"]
    run["draft_details"]["answers"].append({"question": "Where is it held?", "status": "answered"})
    checks = {c["name"]: c["passed"] for c in grade_run(run, step, {"dates": {}})}
    assert checks["distinct_question_answers"]


def test_handoff_requires_preserving_enrolment_action(scenarios):
    step = scenarios["enquiry_and_enrolment_request"].steps[0]
    run = {"interpretation": {"requested_actions": ["Enrol the student in Thursday Level 2"]}}
    checks = {c["name"]: c["passed"] for c in grade_run(run, step, {"dates": {}})}
    assert checks["requested_action_present"]
    run["interpretation"]["requested_actions"] = []
    checks = {c["name"]: c["passed"] for c in grade_run(run, step, {"dates": {}})}
    assert not checks["requested_action_present"]
