"""Only evidenced makeup candidates may become explicit approval side effects."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from studio_copilot.agent.contracts import Draft, Review, Routing
from studio_copilot.agent.workflow.nodes import _validate_booking_proposal, select_flow


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
                    "items": [{"id": str(session_id)}],
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
    assert result.body == draft.body


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
