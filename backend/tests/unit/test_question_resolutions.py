"""Teacher decisions are bounded, explicit revision input."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from studio_copilot.agent.contracts import Review


def resolution(**changes):
    return {
        "question_id": str(uuid4()),
        "decision": "answer",
        "answer": "Wear comfortable clothes.",
        **changes,
    }


def test_resolution_only_revision_does_not_require_freeform_feedback():
    review = Review(action="revise", expected_revision=1, question_resolutions=[resolution()])
    assert review.feedback is None
    assert review.question_resolutions[0].answer == "Wear comfortable clothes."


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_resolutions_are_only_revision_input(action):
    with pytest.raises(ValidationError):
        Review(action=action, expected_revision=1, question_resolutions=[resolution()])


@pytest.mark.parametrize(
    "changes",
    [
        {"answer": None},
        {"answer": ""},
        {"answer": "   "},
        {"decision": "defer", "answer": "Unapplied answer"},
        {"decision": "unknown"},
        {"question_id": "not-a-question-id"},
        {"answer": "x" * 4001},
    ],
)
def test_invalid_teacher_choices_fail_validation(changes):
    with pytest.raises(ValidationError):
        Review(action="revise", expected_revision=1, question_resolutions=[resolution(**changes)])


@pytest.mark.parametrize("answer", [None, "omitted"])
def test_defer_does_not_require_an_answer(answer):
    choice = resolution(decision="defer", answer=answer)
    if answer == "omitted":
        del choice["answer"]
    review = Review(action="revise", expected_revision=1, question_resolutions=[choice])
    assert review.question_resolutions[0].decision == "defer"
    assert review.question_resolutions[0].answer is None


def test_duplicate_question_decisions_are_rejected():
    choice = resolution()
    with pytest.raises(ValidationError):
        Review(action="revise", expected_revision=1, question_resolutions=[choice, choice])


def test_resolution_count_is_bounded():
    with pytest.raises(ValidationError):
        Review(
            action="revise",
            expected_revision=1,
            question_resolutions=[resolution() for _ in range(21)],
        )
