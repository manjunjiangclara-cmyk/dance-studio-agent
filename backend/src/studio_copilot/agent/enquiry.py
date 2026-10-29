"""Keep the question checklist complete and citations scoped to this drafting attempt."""

from studio_copilot.agent.contracts import Draft, EnquiryAnswer


def context_evidence(context: dict) -> dict:
    """Snapshot already-loaded records so personal answers can cite retained evidence."""
    student = context.get("student", {})
    references = ["student:" + str(student["id"])] if student.get("id") else []
    enrolments = context.get("enrolments", [])
    references.extend("enrolment:" + str(item["id"]) for item in enrolments)
    messages = {}
    for message in [*context.get("history", []), context.get("source", {})]:
        if message.get("id") and message.get("kind") in {
            "student_email",
            "staff_note",
            "teacher_response",
        }:
            messages[message["id"]] = message
    references.extend("message:" + str(key) for key in messages)
    return {
        "tool": "student_context",
        "arguments": {},
        "finding": "Student records and supplied conversation messages.",
        "result": {
            "student": {"id": student.get("id"), "highest_level": student.get("highest_level")},
            "enrolments": enrolments,
            "messages": list(messages.values()),
            "references": references,
        },
    }


def validate_answers(draft: Draft, state: dict) -> Draft:
    if state.get("flow", state.get("context", {}).get("flow")) == "makeup":
        draft.answers = []
        return draft
    questions = list(dict.fromkeys(state["interpretation"].get("questions", [])))
    actions = state["interpretation"].get("requested_actions", [])
    allowed = {"policy:" + state["context"]["policy"]["version"]}
    for item in state.get("evidence", []):
        if "error" not in item["result"]:
            allowed.update(item["result"].get("references", []))
    if state.get("feedback", "").strip():
        allowed.add("teacher_feedback")
    grouped: dict[str, list[EnquiryAnswer]] = {}
    for answer in draft.answers:
        grouped.setdefault(answer.question, []).append(answer)
    answers, unsafe = [], False
    for question in questions:
        matches = grouped.get(question, [])
        answer = matches[0] if len(matches) == 1 else None
        if answer is not None:
            original_refs = answer.references
            answer.references = list(dict.fromkeys(ref for ref in original_refs if ref in allowed))
            invalid = len(answer.references) != len(set(original_refs))
            if not answer.answer.strip() or (
                answer.status == "answered" and (invalid or not answer.references)
            ):
                answer = None
        if answer is None:
            unsafe = True
            answer = EnquiryAnswer(
                question=question,
                status="needs_teacher",
                answer="The teacher needs to verify this before replying.",
                references=[],
            )
        answers.append(answer)
    if set(grouped) - set(questions):
        unsafe = True
    if not questions:
        unsafe = True
    draft.answers = answers
    if unsafe:
        draft.body = safe_body(answers, actions)
        draft.rationale += " Incomplete or unsupported question answers need teacher review."
    return draft


def safe_body(answers: list[EnquiryAnswer], actions: list[str]) -> str:
    parts = ["Thanks for your message."]
    parts.extend(answer.answer for answer in answers if answer.status == "answered")
    parts.extend(answer.answer for answer in answers if answer.status == "needs_student")
    if any(answer.status == "needs_teacher" for answer in answers):
        parts.append("I can't confirm the remaining details yet. I'll check and get back to you.")
    elif actions or not answers:
        parts.append("I'll review your enquiry and get back to you.")
    return "\n\n".join(parts)[:20_000]
