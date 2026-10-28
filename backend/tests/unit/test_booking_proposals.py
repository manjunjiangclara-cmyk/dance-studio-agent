"""Only evidenced makeup candidates may become explicit approval side effects."""

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from studio_copilot.agent.contracts import Draft, Review, Routing
from studio_copilot.agent.makeup import _explicit_absence_notice
from studio_copilot.agent.workflow.nodes import _validate_booking_proposal, select_flow


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I will miss my Monday class on 2027-02-08.", True),
        ("I missed my class on 2027-02-08. Can I make it up?", True),
        ("What should I wear on 2027-02-08?", False),
        ("I will not miss my class on 2027-02-08.", False),
        ("I will miss my class on 2027-02-08 if I am ill.", False),
        ("I will miss my class on 2027-02-09.", False),
        ("I might miss my class on 2027-02-08.", False),
        ("I will miss my class on 2027-02-08. Actually I will attend.", False),
        ("This is only an example: I will miss my class on 2027-02-08.", False),
        ("I will miss my Tuesday class on 2027-02-08.", False),
    ],
)
def test_notice_recognizer_requires_an_explicit_matching_statement(text, expected):
    assert _explicit_absence_notice(SimpleNamespace(body=text), date(2027, 2, 8)) is expected


def proposal(session_id):
    return Draft(
        body="I have booked the Thursday place for you.",
        rationale="A candidate was found.",
        questions=[],
        references=[],
        booking_session_id=session_id,
    )


def state(session_id, *, flow="makeup", tool="search_sessions"):
    return {
        "flow": flow,
        "context": {"flow": flow},
        "evidence": [
            {"tool": "verify_makeup_request", "result": {"verified": True}},
            {
                "tool": "validate_makeup_candidates",
                "result": {"valid_session_ids": [str(session_id)]},
            },
            {
                "tool": tool,
                "arguments": {},
                "result": {
                    "items": [
                        {
                            "id": str(session_id),
                            "class_name": "Thursday Level 2",
                            "location_name": "Studio A",
                            "starts_at": "2027-02-11T18:00:00+11:00",
                        }
                    ],
                    "references": ["session:" + str(session_id)],
                },
            },
        ],
        "warnings": [],
    }


def test_evidenced_makeup_proposal_retains_selected_session():
    session_id = uuid4()
    draft = proposal(session_id)
    result = _validate_booking_proposal(draft, state(session_id))
    assert result.booking_session_id == session_id
    assert "Thursday Level 2" in result.body
    assert "11 February 2027" in result.body


@pytest.mark.parametrize("unsupported", ["different_id", "wrong_tool", "handoff", "reference_only"])
def test_unsupported_proposal_clears_action_and_replaces_unsupported_body(unsupported):
    session_id = uuid4()
    draft = proposal(session_id)
    original_body = draft.body
    evidence = state(session_id)
    if unsupported == "different_id":
        evidence = state(uuid4())
    elif unsupported == "wrong_tool":
        evidence = state(session_id, tool="get_enrolments")
    elif unsupported == "handoff":
        evidence = state(session_id, flow="teacher_handoff")
    else:
        evidence["evidence"][-1]["result"]["items"] = []
    result = _validate_booking_proposal(draft, evidence)
    assert result.booking_session_id is None
    assert result.body != original_body
    assert result.rationale != "A candidate was found."


def test_draft_without_proposal_remains_ordinary_review():
    draft = Draft(
        body="Could you confirm the date?", rationale="Need a date.", questions=[], references=[]
    )
    result = _validate_booking_proposal(draft, {"flow": "teacher_handoff", "evidence": []})
    assert result == draft
    assert result.booking_session_id is None


def test_booking_proposal_requires_uuid_and_review_cannot_replace_the_proposal():
    with pytest.raises(ValidationError):
        proposal("not-a-session-id")
    with pytest.raises(ValidationError):
        Review(action="approve", expected_revision=1, booking_session_id=uuid4())


def test_corrupt_candidate_evidence_cannot_authorize_a_proposal():
    session_id = uuid4()
    evidence = state(session_id)
    evidence["evidence"][1]["result"]["valid_session_ids"] = ["invalid"]
    evidence["evidence"][-1]["result"]["items"] = [{"id": "invalid"}]
    assert _validate_booking_proposal(proposal(session_id), evidence).booking_session_id is None


@pytest.mark.parametrize("intents", [["makeup"], ["makeup", "absence"]])
def test_missing_dates_do_not_bypass_makeup_verification(intents):
    routing = Routing(
        intents=intents,
        request_summary="Could I do a makeup?",
        needs_clarification=True,
        reason="Missing class dates",
    )
    assert select_flow(routing) == "makeup"
