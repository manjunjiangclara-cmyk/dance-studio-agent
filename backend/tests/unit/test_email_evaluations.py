"""The evaluation contract remains declarative and grades real structured output."""

import pytest
from pydantic import ValidationError

from evaluations.cases import EmailStep, Scenario, load_scenarios, render
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
