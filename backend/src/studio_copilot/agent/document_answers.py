"""Compose validated document answers without asking another model to rewrite them."""

import re

from studio_copilot.agent.contracts import Draft, EnquiryAnswer
from studio_copilot.agent.enquiry import safe_body

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
        complete = (
            result.get("status") == "answered"
            and not result.get("missing_information")
            and result.get("claims")
            and result.get("references")
            and answer_text
            and len(answer_text) <= 4000
            and retained_characters + len(answer_text) <= 16_000
            and len(retained_references | set(result.get("references", []))) <= 40
        )
        if complete:
            retained_characters += len(answer_text)
            retained_references.update(result["references"])
        answers.append(
            EnquiryAnswer(
                question=question,
                question_id=question_id,
                status="answered" if complete else "needs_teacher",
                answer=answer_text
                if complete
                else "The teacher needs to verify this before replying.",
                references=result["references"] if complete else [],
            )
        )
    return Draft(
        body=safe_body(answers, state["interpretation"].get("requested_actions", [])),
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
