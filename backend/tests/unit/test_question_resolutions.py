"""Teacher decisions are bounded, explicit revision input."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from studio_copilot.agent.contracts import EnquiryInterpretation, ModelError, Review
from studio_copilot.agent.question_resolutions import identify_questions


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


def test_recovered_questions_preserve_existing_ids_and_do_not_guess_paraphrase_equivalence():
    run_id = str(uuid4())
    existing_id = str(uuid4())
    previous = {
        "questions": ["What should I wear?"],
        "question_ids": {"What should I wear?": existing_id},
    }
    parsed = EnquiryInterpretation(
        request_summary="Questions",
        missing_details=[],
        enduring_preferences=[],
        questions=["  WHAT should I wear? ", "Is there a dress code?", "Where is class?"],
    )
    identify_questions(parsed, run_id, previous)
    assert parsed.questions == ["What should I wear?", "Is there a dress code?", "Where is class?"]
    assert parsed.question_ids["What should I wear?"] == existing_id
    assert len(set(parsed.question_ids.values())) == 3


def test_combined_question_limit_does_not_silently_drop_recovered_question():
    questions = [f"Question {index}?" for index in range(20)]
    previous = {"questions": questions}
    parsed = EnquiryInterpretation(
        request_summary="Questions",
        missing_details=[],
        enduring_preferences=[],
        questions=["Another question?"],
    )
    with pytest.raises(ModelError, match="20 questions"):
        identify_questions(parsed, str(uuid4()), previous)
    assert parsed.questions == ["Another question?"]
