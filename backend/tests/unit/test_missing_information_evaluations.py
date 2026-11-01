"""Missing-fact scenarios distinguish availability, status and citation relevance."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from evaluations.cases import POLICY, QuestionAnswerCheck, load_scenarios
from evaluations.grading import grade_run
from studio_copilot.agent.policy import load_policy


def scenario(case="known_timetable_unknown_clothing"):
    return next(item for item in load_scenarios() if item.id == case)


def output():
    questions = ["What time does Thursday Level 2 start?", "What should I wear?"]
    return {
        "status": "awaiting_review",
        "interpretation": {
            "flow": "enquiry",
            "routing": {
                "intents": ["general_enquiry"],
                "action": "information_only",
                "request_summary": "Time and clothing questions",
                "needs_clarification": False,
                "reason": "Information only",
            },
            "request_summary": "Time and clothing questions",
            "questions": questions,
            "requested_actions": [],
            "missing_details": [],
            "enduring_preferences": [],
        },
        "draft_details": {
            "body": (
                "Thursday starts at 6 pm. I'll check the clothing requirements with the teacher."
            ),
            "rationale": "Only the timetable is available.",
            "questions": [],
            "references": ["class:thursday"],
            "answers": [
                {
                    "question": questions[0],
                    "status": "answered",
                    "answer": "Thursday starts at 6 pm.",
                    "references": ["class:thursday"],
                },
                {
                    "question": questions[1],
                    "status": "needs_teacher",
                    "answer": "The teacher needs to check the clothing rules.",
                    "references": [],
                },
            ],
        },
        "evidence": [
            {
                "tool": "get_timetable",
                "result": {"references": ["class:thursday"], "items": [{"id": "thursday"}]},
            }
        ],
    }


def checks(run, case="known_timetable_unknown_clothing"):
    return {
        item["name"]: item["passed"]
        for item in grade_run(run, scenario(case).steps[0], {"dates": {}})
    }


def test_mixed_enquiry_accepts_supported_time_and_explicit_missing_clothing_fact():
    assert all(checks(output()).values())


@pytest.mark.parametrize("status", ["answered", "needs_student"])
def test_unavailable_clothing_cannot_be_answered_or_sent_back_to_the_student(status):
    run = output()
    run["draft_details"]["answers"][1]["status"] = status
    result = checks(run)
    assert result["question_answer:0:present"]
    assert not result["question_answer:0:status"]
    assert result["question_answer:1:status"]


def test_valid_but_unrelated_timetable_citation_fails_missing_clothing_check():
    run = output()
    run["draft_details"]["answers"][1]["references"] = ["class:thursday"]
    result = checks(run)
    assert result["grounded_references"]
    assert result["question_answer:0:status"]
    assert not result["question_answer:0:no_unrelated_references"]


def test_dropping_clothing_question_does_not_pass_vacuously():
    run = output()
    run["draft_details"]["answers"] = run["draft_details"]["answers"][:1]
    result = checks(run)
    assert not result["question_answer:0:present"]
    assert not result["question_answer:0:status"]
    assert not result["question_answer:0:no_unrelated_references"]


def test_every_matching_question_must_have_the_expected_missing_fact_status():
    run = output()
    clothing = deepcopy(run["draft_details"]["answers"][1])
    clothing.update(question="Is a uniform required?", status="answered")
    run["draft_details"]["answers"].append(clothing)
    assert not checks(run)["question_answer:0:status"]


def test_uncertainty_does_not_hide_a_known_invented_dress_code():
    run = output()
    run["draft_details"]["body"] += " You must wear a leotard."
    result = checks(run)
    assert result["draft_mentions_uncertainty"]
    assert not result["draft_contradicts_scenario:must wear a leotard"]


@pytest.mark.parametrize("terms", [[], [""], ["   "]])
def test_question_topic_selectors_cannot_match_everything_accidentally(terms):
    with pytest.raises(ValidationError):
        QuestionAnswerCheck(question_terms=terms, status="needs_teacher")


def test_missing_clothing_scenarios_use_sources_without_a_dress_code():
    policy = str(load_policy(POLICY)).casefold()
    assert not any(term in policy for term in ["clothing", "dress code", "uniform", "footwear"])
    for case in ["unknown_clothing_requirements", "known_timetable_unknown_clothing"]:
        item = scenario(case)
        assert item.steps[0].expected.interpretation.flow == "enquiry"
        assert item.steps[0].checks.question_answer_checks[0].status == "needs_teacher"
        assert not item.steps[0].checks.question_answer_checks[0].allow_references
        assert any("citation" in criterion for criterion in item.rubric)
