"""Server-owned question identities and explicit teacher decisions for one run."""

from uuid import UUID, uuid5

from pydantic import ValidationError

from studio_copilot.administration.service import conflict, invalid
from studio_copilot.agent.contracts import EnquiryInterpretation, ModelError, QuestionResolution

QUESTION_LIMIT_FAILURE = "question_limit_exceeded"


class QuestionLimitError(ModelError):
    """A revised extraction cannot fit without losing checklist questions."""


class RevisionExtractionError(ModelError):
    """The revised checklist could not be verified."""


def identify_questions(parsed: EnquiryInterpretation, run_id: str, previous: dict) -> None:
    # Keep the original checklist and add recovered questions. Only normalize case
    # and whitespace: assuming two paraphrases are equivalent could hide a distinct
    # question. Potential duplicates remain visible for teacher review.
    questions = [*previous.get("questions", []), *parsed.questions]
    distinct = {}
    for question in questions:
        distinct.setdefault(" ".join(question.split()).casefold(), question)
    if len(distinct) > 20:
        raise QuestionLimitError(
            "The combined question checklist exceeds 20 questions; review the enquiry manually."
        )
    parsed.questions = list(distinct.values())
    existing_ids = previous.get("question_ids", {})
    parsed.question_ids = {
        question: existing_ids.get(question) or str(uuid5(UUID(run_id), normalized))
        for normalized, question in distinct.items()
    }


def merge_resolutions(existing: list[dict], updates: list[dict]) -> list[dict]:
    merged = {str(item["question_id"]): item for item in existing}
    merged.update({str(item["question_id"]): item for item in updates})
    return list(merged.values())


def resolved_question_context(interpretation: dict, resolutions: list[dict]) -> list[dict]:
    """Pair each teacher decision with the original question for the model."""
    questions = {
        str(value): question for question, value in interpretation.get("question_ids", {}).items()
    }
    return [
        {**item, "question": questions[str(item["question_id"])]}
        for item in resolutions
        if str(item["question_id"]) in questions
    ]


def validate_resolution_update(interpretation: dict, draft: dict, updates: list[dict]) -> None:
    if not updates:
        return
    ids = interpretation.get("question_ids", {})
    if not ids:
        conflict("Regenerate this older review before resolving individual questions.")
    eligible = set(draft.get("required_question_ids", []))
    eligible.update(
        item.get("question_id")
        for item in draft.get("answers", [])
        if item.get("status") == "needs_teacher"
    )
    eligible.update(str(item["question_id"]) for item in draft.get("question_resolutions", []))
    known = set(ids.values())
    for item in updates:
        question_id = str(item["question_id"])
        if question_id not in known or question_id not in eligible:
            invalid("This question is unknown or does not require a teacher answer.")
    merged = merge_resolutions(draft.get("question_resolutions", []), updates)
    by_id = {str(item["question_id"]): item for item in merged}
    parts = ["Thanks for your message."]
    for answer in draft.get("answers", []):
        decision = by_id.get(answer.get("question_id"))
        if decision:
            parts.append(
                decision["answer"]
                if decision["decision"] == "answer"
                else deferral_text(answer["question"])
            )
        elif answer.get("status") in {"answered", "needs_student"}:
            parts.append(answer.get("answer", ""))
    parts.append("I can't confirm the remaining details yet. I'll check and get back to you.")
    if len("\n\n".join(parts)) > 20_000:
        invalid(
            "The combined reply would be too long. Shorten the teacher answers and update again."
        )


def resolution_evidence(resolutions: list[dict]) -> dict:
    return {
        "tool": "teacher_question_resolutions",
        "arguments": {},
        "finding": "Teacher answers and explicit decisions to confirm information later.",
        "result": {
            "items": resolutions,
            "references": [resolution_reference(item) for item in resolutions],
        },
    }


def resolution_reference(item: dict) -> str:
    prefix = "teacher_answer:" if item["decision"] == "answer" else "teacher_deferral:"
    return prefix + str(item["question_id"])


def deferral_text(question: str) -> str:
    return f"Regarding “{question}”, I'll confirm the details and get back to you."


def require_resolved_questions(run) -> None:
    """Run inside the approval transaction before any response or booking is committed."""
    if run.interpretation.get("flow") == "makeup":
        return
    draft = run.draft_details
    required = set(draft.get("required_question_ids", []))
    answers = draft.get("answers", [])
    for item in answers:
        if item.get("status") == "needs_teacher":
            if not item.get("question_id"):
                conflict(
                    "Regenerate this older review before resolving missing studio information."
                )
            required.add(item["question_id"])
    if not required:
        return
    ids = run.interpretation.get("question_ids", {})
    if not ids or not required <= set(ids.values()):
        conflict("Regenerate this review to restore its question checklist.")
    try:
        resolutions = [
            QuestionResolution.model_validate(item)
            for item in draft.get("question_resolutions", [])
        ]
    except (ValidationError, TypeError):
        conflict("Update the draft to apply valid answers or deferrals before approval.")
    by_id = {str(item.question_id): item for item in resolutions}
    by_answer = {item.get("question_id"): item for item in answers}
    if len(by_id) != len(resolutions):
        conflict("Update the draft to apply one decision per question.")
    references = {
        ref
        for item in run.evidence
        for ref in item.get("result", {}).get("references", [])
        if item.get("tool") == "teacher_question_resolutions"
    }
    for question_id in required:
        decision = by_id.get(question_id)
        answer = by_answer.get(question_id)
        if decision is None or answer is None:
            conflict(
                "Answer or explicitly defer each question needing teacher input, "
                "then update the draft."
            )
        ref = resolution_reference(decision.model_dump(mode="json"))
        expected = "answered" if decision.decision == "answer" else "needs_teacher"
        if (
            ref not in references
            or ref not in answer.get("references", [])
            or answer.get("status") != expected
        ):
            conflict(
                "Update the draft to apply the teacher's answers or deferrals before approval."
            )
        if decision.decision == "answer" and answer.get("answer") != decision.answer:
            conflict("Update the draft to apply the latest teacher answer before approval.")
