"""Compose validated document answers without asking another model to rewrite them."""

import re

from studio_copilot.agent.contracts import Draft, EnquiryAnswer

EVIDENCE_MARKER = re.compile(r"(?<!\w)\[?(?:document:)?E[0-9a-f]{24}\]?(?!\w)", re.IGNORECASE)


def document_draft(state):
    if not state.get("document_answers_enabled"):
        return None
    results = {
        item["result"]["question_id"]: item["result"]
        for item in state.get("evidence", [])
        if item.get("tool") == "document_answer"
    }
    answers = []
    retained_characters = 0
    retained_references = set()
    for question in state["interpretation"].get("questions", []):
        question_id = state["interpretation"]["question_ids"][question]
        result = results.get(question_id, {})
        # Build student-facing text from validated claims, not the annotated
        # evidence rendering. Keep the original structured citations for review.
        source_ids = [ref.removeprefix("document:") for ref in result.get("references", [])]
        claims = []
        for claim in result.get("claims", []):
            text = claim.get("text", "")
            for source_id in source_ids:
                text = text.replace(f"[{source_id}]", "")
            text = EVIDENCE_MARKER.sub("", text)
            claims.append(text.strip())
        answer_text = "\n\n".join(text for text in claims if text)
        supported = (
            result.get("status") in {"answered", "partial", "needs_clarification"}
            and result.get("claims")
            and result.get("references")
            and answer_text
            and len(answer_text) <= 4000
            and retained_characters + len(answer_text) <= 16_000
            and len(retained_references | set(result.get("references", []))) <= 40
        )
        if supported:
            retained_characters += len(answer_text)
            retained_references.update(result["references"])
        complete = bool(
            supported
            and result.get("status") == "answered"
            and not result.get("missing_information")
        )
        answers.append(
            EnquiryAnswer(
                question=question,
                question_id=question_id,
                status="answered" if complete else "needs_teacher",
                answer=answer_text
                if supported
                else "The teacher needs to verify this before replying.",
                references=result["references"] if supported else [],
            )
        )
    return Draft(
        body=document_safe_body(answers),
        answers=answers,
        references=list(dict.fromkeys(ref for item in answers for ref in item.references)),
        rationale=(
            "Document answers use grounded generation with exact citation checks. "
            "Semantic verification is disabled. "
            "Incomplete answers and live-record questions require teacher confirmation. "
            "See supporting evidence for partial answers, original quotes and source ranges."
        ),
        questions=[item.question for item in answers if item.status == "needs_teacher"],
    )


def document_safe_body(answers: list[EnquiryAnswer]) -> str:
    """A reviewable fallback with no unapproved promise or live-state assertion."""
    facts = [item.answer for item in answers if item.references and item.answer.strip()]
    parts = ["Thanks for your message.", *facts]
    if any(item.status == "needs_teacher" for item in answers):
        parts.append("I can't confirm the remaining details yet.")
    return "\n\n".join(parts)
