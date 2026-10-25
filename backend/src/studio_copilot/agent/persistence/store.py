"""Short database transactions for graph context, memory, drafts, and approval.

No model calls happen here. LangGraph checkpoint storage is managed separately.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.contracts import RequestInterpretation, ReviewedMemory
from studio_copilot.agent.tools import enrolments
from studio_copilot.persistence.models import AgentRun, Conversation, Message, Student


def _active_run(db, run_id):
    run = require(db, AgentRun, UUID(run_id), lock=True)
    if run.status in {"superseded", "closed", "approved"}:
        conflict("This run no longer accepts changes.")
    return run


def _message_data(message):
    return {
        "id": str(message.id),
        "kind": message.kind,
        "body": message.body,
        "occurred_at": message.occurred_at.isoformat(),
    }


def _memory_summary(memory):
    lines = ["Conversational memory; official student records remain authoritative."]
    for key, item in memory.get("preferences", {}).items():
        lines.append(f"Preference {key}: {item['value']} ({item['kind']}).")
    for item in list(memory.get("requests", {}).values())[-10:]:
        lines.append(f"Request: {item['request_summary']} ({item['kind']}).")
        if item.get("approved_response_id"):
            lines.append(
                "Teacher response approved; delivery and business actions are unconfirmed."
            )
    for response_id, item in list(memory.get("approved_responses", {}).items())[-10:]:
        current = memory.get("requests", {}).get(item["conversation_id"], {})
        if current.get("source_message_id") != response_id:
            lines.append(f"Earlier teacher-approved response: {item['request_summary']}")
            lines.append("Delivery and business actions are unconfirmed.")
    return "\n".join(lines)


def _save_memory(
    db,
    student,
    conversation_id,
    source_id,
    summary,
    preferences,
    *,
    approved=False,
    request_source_id=None,
):
    # Replace the JSONB object to track nested changes while preserving staff-maintained keys.
    context = dict(student.context)
    memory = dict(context.get("_agent_memory", {}))
    saved_preferences = dict(memory.get("preferences", {}))
    kind = "teacher_reviewed" if approved else "student_stated"
    response = require(db, Message, source_id) if approved else None
    for preference in preferences:
        previous_source = saved_preferences.get(preference.key, {}).get("source_message_id")
        if response is not None and previous_source:
            previous_message = db.get(Message, UUID(previous_source))
            if previous_message is not None and previous_message.created_at > response.created_at:
                continue  # Recovery of an older approval must not replace a newer preference.
        saved_preferences[preference.key] = {
            "value": preference.value,
            "source_message_id": str(source_id),
            "kind": kind,
        }
    requests = dict(memory.get("requests", {}))
    entry = {
        "request_summary": summary,
        "source_message_id": str(source_id),
        "kind": kind,
        **({"approved_response_id": str(source_id)} if approved else {}),
    }
    current_source = requests.get(str(conversation_id), {}).get("source_message_id")
    if not approved or current_source in {None, str(request_source_id), str(source_id)}:
        requests[str(conversation_id)] = entry
    if approved:
        responses = dict(memory.get("approved_responses", {}))
        responses[str(source_id)] = {**entry, "conversation_id": str(conversation_id)}
        memory["approved_responses"] = responses
    memory.update(preferences=saved_preferences, requests=requests)
    context["_agent_memory"] = memory
    student.context, student.ai_summary = context, _memory_summary(memory)
    db.flush()


class WorkflowStore:
    def __init__(self, engine):
        self.engine = engine

    def load_context(self, run_id: str) -> dict:
        with Session(self.engine) as db:
            run = require(db, AgentRun, UUID(run_id))
            source = require(db, Message, run.source_message_id)
            conversation = require(db, Conversation, run.conversation_id)
            student = require(db, Student, conversation.student_id)
            # Preserve message kinds, including the distinction between drafts and responses.
            history = [_message_data(message) for message in conversation.messages][-50:]
            return {
                "source": _message_data(source),
                "conversation_id": str(conversation.id),
                "student": {
                    "id": str(student.id),
                    "name": student.display_name,
                    "highest_level": student.highest_level,
                    "context": student.context,
                    "ai_summary": student.ai_summary,
                },
                "enrolments": enrolments(student),
                "history": history,
                "history_limit": 50,
                "policy": run.policy_snapshot,
            }

    def save_routing(self, run_id: str, routing: dict, flow: str) -> None:
        with Session(self.engine) as db, db.begin():
            _active_run(db, run_id).interpretation = {"routing": routing, "flow": flow}

    def remember_student(
        self,
        run_id: str,
        interpretation: RequestInterpretation,
        routing: dict,
        flow: str,
    ) -> None:
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            conversation = require(db, Conversation, run.conversation_id)
            student = require(db, Student, conversation.student_id, lock=True)
            _save_memory(
                db,
                student,
                conversation.id,
                run.source_message_id,
                interpretation.request_summary,
                interpretation.enduring_preferences,
            )
            run.interpretation = {**interpretation.model_dump(), "routing": routing, "flow": flow}

    def save_draft(
        self,
        run_id: str,
        attempt: int,
        draft: dict,
        evidence: list[dict],
        warnings: list[str],
    ) -> None:
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            # Replaying this node after a checkpoint failure must not create a second draft.
            if run.revision < attempt:
                message = Message(
                    conversation_id=run.conversation_id,
                    kind="assistant_draft",
                    body=draft["body"],
                )
                db.add(message)
                db.flush()
                run.draft_message_id, run.revision = message.id, attempt
            run.evidence = evidence
            run.draft_details = {**draft, "warnings": warnings}
            run.status, run.error = "awaiting_review", None

    def approve(self, run_id: str, body: str | None) -> str:
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            # A retry after storing the response reuses it before reconciling memory.
            if run.approved_response_id is None:
                draft = require(db, Message, run.draft_message_id)
                response = Message(
                    conversation_id=run.conversation_id,
                    kind="teacher_response",
                    body=body or draft.body,
                )
                db.add(response)
                db.flush()
                run.approved_response_id = response.id
            run.status = "finalizing"
            return str(run.approved_response_id)

    def approved_response(self, run_id: str) -> str:
        with Session(self.engine) as db:
            run = require(db, AgentRun, UUID(run_id))
            return require(db, Message, run.approved_response_id).body

    def remember_approval(self, run_id: str, memory: ReviewedMemory) -> None:
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            conversation = require(db, Conversation, run.conversation_id)
            student = require(db, Student, conversation.student_id, lock=True)
            _save_memory(
                db,
                student,
                conversation.id,
                run.approved_response_id,
                memory.request_summary,
                memory.enduring_preferences,
                approved=True,
                request_source_id=run.source_message_id,
            )
            run.status, run.error = "approved", None
