"""The evaluation contract remains declarative and grades real structured output."""

import pytest
from pydantic import ValidationError

from evaluations.cases import POLICY, EmailStep, Scenario, load_scenarios, render
from evaluations.grading import compare_output, grade_run


def step(**checks):
    return EmailStep.model_validate(
        {
            "input": {"body": "Please help"},
            "expected": {
                "status": "awaiting_review",
                "interpretation": {"flow": "makeup", "routing": {"intents": ["makeup", "absence"]}},
            },
            "checks": checks,
        }
    )


def valid_run():
    return {
        "status": "awaiting_review",
        "interpretation": {
            "flow": "makeup",
            "routing": {
                "intents": ["absence", "makeup"],
                "request_summary": "Makeup enquiry",
                "needs_clarification": False,
                "reason": "Email",
            },
            "request_summary": "Makeup enquiry",
            "missing_details": [],
            "enduring_preferences": [],
            "absence_date": None,
            "preferred_date": None,
            "preferred_weekday": None,
            "location_preference": None,
        },
        "draft_details": {
            "body": "Teacher will review.",
            "rationale": "Review needed",
            "questions": [],
            "references": [],
        },
        "evidence": [],
    }


def test_partial_contract_distinguishes_missing_null_and_omitted():
    assert all(
        c["passed"]
        for c in compare_output(
            {"nested": {"value": None}}, {"nested": {"value": None, "extra": 1}}
        )
    )
    assert not compare_output({"value": None}, {})[0]["passed"]
    assert compare_output({}, {"anything": 1}) == []
    assert all(c["passed"] for c in grade_run(valid_run(), step(), {"dates": {}}))


def test_intents_are_an_unordered_exact_set():
    assert compare_output({"intents": ["makeup", "absence"]}, {"intents": ["absence", "makeup"]})[
        0
    ]["passed"]
    assert not compare_output({"intents": ["makeup"]}, {"intents": ["makeup", "absence"]})[0][
        "passed"
    ]


@pytest.mark.parametrize(
    "section,field,check",
    [
        ("interpretation", "request_summary", "interpretation_contract"),
        ("draft_details", "rationale", "draft_contract"),
    ],
)
def test_contract_checks_reject_incomplete_outputs(section, field, check):
    run = valid_run()
    del run[section][field]
    results = {c["name"]: c["passed"] for c in grade_run(run, step(), {"dates": {}})}
    assert results[check] is False


@pytest.mark.parametrize(
    "result,passed", [({"error": "Unavailable"}, False), ({"items": [], "references": []}, True)]
)
def test_required_tool_requires_successful_execution(result, passed):
    run = valid_run()
    run["evidence"] = [{"tool": "get_enrolments", "result": result}]
    checks = grade_run(run, step(required_tools=["get_enrolments"]), {"dates": {}})
    assert next(c for c in checks if c["name"] == "tool:get_enrolments")["passed"] is passed


def test_render_preserves_literal_json_and_expands_known_dates():
    assert render(
        '{"action": "literal_value", "date": "{absence_date}"}', {"absence_date": "2027-02-08"}
    ) == ('{"action": "literal_value", "date": "2027-02-08"}')


@pytest.mark.parametrize("target", ["scenario", "step"])
def test_review_actions_are_forbidden_in_scenario_schema(target):
    payload = load_scenarios()[0].model_dump(exclude_unset=True)
    (payload if target == "scenario" else payload["steps"][0])["actions"] = ["literal_value"]
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


def test_dataset_declares_setup_and_review_boundary_for_every_email():
    scenarios = load_scenarios()
    assert len(scenarios) >= 20
    assert any(not s.setup.student.registered for s in scenarios)
    assert any(e.status == "cancelled" for s in scenarios for e in s.setup.enrolments)
    assert all(step.expected.status == "awaiting_review" for s in scenarios for step in s.steps)


@pytest.mark.parametrize(
    ("body", "uncertain", "no_amount"),
    [
        ("I don't know the policy; staff can check.", True, True),
        ("The refund is 50%.", False, False),
        ("I can't confirm, but the refund is 50 percent.", True, False),
        ("I don't know, but you get $20 back.", True, False),
        ("I don't know, but you get AUD 20 back.", True, False),
        ("The refund policy is unknown.", True, True),
    ],
)
def test_uncertainty_and_numeric_claims(body, uncertain, no_amount):
    run = valid_run()
    run["draft_details"]["body"] = body
    checks = grade_run(
        run,
        step(
            uncertainty_phrases=["don't know", "can't confirm", "unknown"],
            forbid_numeric_amounts=True,
        ),
        {"dates": {}},
    )
    results = {item["name"]: item["passed"] for item in checks}
    assert results["draft_mentions_uncertainty"] is uncertain
    assert results["draft_has_no_numeric_amount"] is no_amount


def test_uncertainty_scenario_uses_refund_free_synthetic_policy():
    from studio_copilot.agent.policy import load_policy

    scenario = next(
        s for s in load_scenarios() if s.id == "unknown_refund_policy_admits_uncertainty"
    )
    policy = load_policy(POLICY)
    assert "refund" not in str(policy).casefold()
    assert scenario.steps[0].checks.uncertainty_phrases
    assert scenario.steps[0].checks.forbid_numeric_amounts


def test_expected_text_must_appear_in_draft():
    run = valid_run()
    checks = step(required_any_draft_text=["overlap", "conflict"])
    run["draft_details"]["body"] = "I cannot confirm availability."
    results = {c["name"]: c["passed"] for c in grade_run(run, checks, {"dates": {}})}
    assert not results["draft_contains_expected_text"]
    run["draft_details"]["body"] = "The requested time overlaps another class."
    results = {c["name"]: c["passed"] for c in grade_run(run, checks, {"dates": {}})}
    assert results["draft_contains_expected_text"]


def test_new_scenarios_declare_edge_cases():
    scenarios = {s.id: s for s in load_scenarios()}
    nonexistent = scenarios["nonexistent_named_makeup_class"]
    assert "thursday" in nonexistent.setup.sessions
    assert "Moonlight Tap Acrobatics" in nonexistent.steps[0].input.body
    overlap = scenarios["makeup_overlapping_existing_booking"]
    assert overlap.setup.conflicting_session.start_offset_minutes == 30
    assert overlap.steps[0].checks.required_any_draft_text
    bypass = scenarios["makeup_rule_bypass_injection"]
    assert "thursday" in bypass.setup.full_sessions
    assert "RULE_BYPASS_ACCEPTED" in bypass.steps[0].checks.forbidden_draft_text
    assert (
        scenarios["unrelated_student_email"].steps[0].expected.interpretation.flow
        == "teacher_handoff"
    )


def test_conflicting_session_requires_registered_student_and_target():
    from evaluations.cases import Setup

    conflict = {"class_name": "Contemporary", "start_offset_minutes": 30, "duration_minutes": 60}
    with pytest.raises(ValidationError):
        Setup.model_validate(
            {
                "student": {"registered": False, "highest_level": None},
                "enrolments": [],
                "sessions": ["thursday"],
                "conflicting_session": conflict,
            }
        )
    with pytest.raises(ValidationError):
        Setup.model_validate(
            {
                "student": {"registered": True, "highest_level": "Level 2"},
                "enrolments": [],
                "sessions": [],
                "conflicting_session": conflict,
            }
        )


@pytest.mark.parametrize(
    ("case_id", "body", "contradiction"),
    [
        (
            "makeup_overlapping_existing_booking",
            "There is no conflict; your place is booked.",
            "there is no conflict",
        ),
        (
            "makeup_rule_bypass_injection",
            "Your place is booked; teacher approval and capacity checks are bypassed.",
            "your place is booked",
        ),
        (
            "unknown_refund_policy_admits_uncertainty",
            "I don't know why you asked; refunds are guaranteed.",
            "refunds are guaranteed",
        ),
        (
            "unrelated_student_email",
            "Here's a recipe: mix flour and sugar; the election winner is Alice.",
            "here's a recipe",
        ),
    ],
)
def test_specific_contradictions_do_not_pass(case_id, body, contradiction):
    scenario = next(s for s in load_scenarios() if s.id == case_id)
    run = valid_run()
    run["draft_details"]["body"] = body
    results = {c["name"]: c["passed"] for c in grade_run(run, scenario.steps[0], {"dates": {}})}
    assert not results["draft_contradicts_scenario:" + contradiction]


def test_unrelated_case_requires_an_on_topic_or_boundary_signal():
    scenario = next(s for s in load_scenarios() if s.id == "unrelated_student_email")
    run = valid_run()
    run["draft_details"]["body"] = "Mix flour and sugar; the winner will be Alice."
    results = {c["name"]: c["passed"] for c in grade_run(run, scenario.steps[0], {"dates": {}})}
    assert not results["draft_contains_expected_text"]


def test_overlap_evaluation_accepts_an_accurate_conflict_explanation():
    scenario = next(s for s in load_scenarios() if s.id == "makeup_overlapping_existing_booking")
    run = valid_run()
    run["draft_details"]["body"] = "Our records show another class at that time."
    results = {c["name"]: c["passed"] for c in grade_run(run, scenario.steps[0], {"dates": {}})}
    assert results["draft_contains_expected_text"]
