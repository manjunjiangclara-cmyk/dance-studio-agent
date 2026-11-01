"""Keep the question checklist complete and citations scoped to this drafting attempt."""

from studio_copilot.agent.contracts import Draft, EnquiryAnswer, ModelError, QuestionResolution
from studio_copilot.agent.question_resolutions import deferral_text, resolution_reference


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
        draft.question_resolutions = []
        draft.required_question_ids = []
        return draft
    questions = list(dict.fromkeys(state["interpretation"].get("questions", [])))
    actions = state["interpretation"].get("requested_actions", [])
    question_ids = state["interpretation"].get("question_ids", {})
    resolutions = [
        QuestionResolution.model_validate(item) for item in state.get("question_resolutions", [])
    ]
    applied = {str(item.question_id): item for item in resolutions}
    required = set(state.get("draft", {}).get("required_question_ids", []))
    required.update(
        question_ids.get(item["question"])
        for item in state.get("draft", {}).get("answers", [])
        if item.get("status") == "needs_teacher"
    )
    allowed = {"policy:" + state["context"]["policy"]["version"]}
    for item in state.get("evidence", []):
        if "error" not in item["result"]:
            # Structured teacher decisions apply only to their own question below;
            # the model must not reuse one decision as evidence for another.
            allowed.update(
                ref
                for ref in item["result"].get("references", [])
                if not ref.startswith(("teacher_answer:", "teacher_deferral:"))
            )
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
        question_id = question_ids.get(question)
        answer.question_id = question_id
        if answer.status == "needs_teacher" and question_id:
            required.add(question_id)
        if question_id in required and question_id not in applied:
            answer.status = "needs_teacher"
            answer.answer = "The teacher needs to verify this before replying."
            answer.references = []
            unsafe = True
        if question_id in applied:
            decision = applied[question_id]
            required.add(question_id)
            answer = EnquiryAnswer(
                question=question,
                question_id=question_id,
                status="answered" if decision.decision == "answer" else "needs_teacher",
                answer=decision.answer
                if decision.decision == "answer"
                else deferral_text(question),
                references=[resolution_reference(decision.model_dump(mode="json"))],
            )
        answers.append(answer)
    if set(grouped) - set(questions):
        unsafe = True
    if not questions:
        unsafe = True
    draft.answers = answers
    draft.question_resolutions = resolutions
    if unsafe or resolutions:
        try:
            draft.body = safe_body(answers, actions, resolutions)
        except ModelError:
            # Regeneration can expand previously concise model answers after the
            # submitted teacher choices passed the preflight size check. Keep
            # those choices intact and leave a reviewable correction path.
            for answer in sorted(answers, key=lambda item: len(item.answer), reverse=True):
                if answer.question_id in applied or answer.status == "needs_teacher":
                    continue
                answer.status = "needs_teacher"
                answer.answer = (
                    "The generated reply is too long. Please provide a concise answer "
                    "using the evidence, or choose Confirm later."
                )
                if answer.question_id:
                    required.add(answer.question_id)
                try:
                    draft.body = safe_body(answers, actions, resolutions)
                except ModelError:
                    continue
                break
            else:
                raise
            draft.rationale += (
                " The generated reply exceeded the response limit; flagged questions "
                "need concise teacher answers or deferrals. Applied teacher answers are retained."
            )
        if questions or resolutions:
            draft.references = list(
                dict.fromkeys(ref for answer in answers for ref in answer.references)
            )
    draft.required_question_ids = sorted(required - {None})
    if unsafe:
        draft.rationale += " Incomplete or unsupported question answers need teacher review."
    return draft


def safe_body(
    answers: list[EnquiryAnswer],
    actions: list[str],
    resolutions: list[QuestionResolution] | None = None,
) -> str:
    parts = ["Thanks for your message."]
    parts.extend(answer.answer for answer in answers if answer.status == "answered")
    parts.extend(answer.answer for answer in answers if answer.status == "needs_student")
    deferred = {str(item.question_id) for item in resolutions or [] if item.decision == "defer"}
    parts.extend(answer.answer for answer in answers if answer.question_id in deferred)
    if any(
        answer.status == "needs_teacher" and answer.question_id not in deferred
        for answer in answers
    ):
        parts.append("I can't confirm the remaining details yet. I'll check and get back to you.")
    elif actions or not answers:
        parts.append("I'll review your enquiry and get back to you.")
    body = "\n\n".join(parts)
    if resolutions and len(body) > 20_000:
        raise ModelError("The combined reply exceeds the response limit; use shorter answers.")
    return body[:20_000]
