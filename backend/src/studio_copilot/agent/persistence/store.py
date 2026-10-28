"""Short database transactions for graph context, memory, drafts, and approval.

No model calls happen here. LangGraph checkpoint storage is managed separately.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.contracts import RequestInterpretation, ReviewedMemory
from studio_copilot.agent.proposals import candidate_session_ids
from studio_copilot.agent.tools import enrolments
from studio_copilot.bookings.service import create_booking
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Conversation,
    Message,
    Student,
)

HISTORY_LIMIT = 3

HISTORY_LIMIT = 3


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
                "Teacher response approved; delivery is unconfirmed. "
                "Check official booking records."
            )
    for response_id, item in list(memory.get("approved_responses", {}).items())[-10:]:
        current = memory.get("requests", {}).get(item["conversation_id"], {})
        if current.get("source_message_id") != response_id:
            lines.append(f"Earlier teacher-approved response: {item['request_summary']}")
            lines.append("Delivery is unconfirmed. Check official booking records.")
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
            recent = list(
                db.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(
                        Message.occurred_at.desc(), Message.created_at.desc(), Message.id.desc()
                    )
                    .limit(HISTORY_LIMIT)
                )
            )
            history = [_message_data(message) for message in reversed(recent)]
            return {
                "source": _message_data(source),
                "conversation_id": str(conversation.id),
                "student": {
                    "id": str(student.id),
                    "name": student.display_name,
                    "email": student.email,
                    "highest_level": student.highest_level,
                    "context": student.context,
                    "ai_summary": student.ai_summary,
                },
                "enrolments": enrolments(student),
                "history": history,
                "history_limit": HISTORY_LIMIT,
                "policy": run.policy_snapshot,
                "intake": run.interpretation.get("intake", {}),
            }

    def save_routing(self, run_id: str, routing: dict, flow: str) -> None:
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            run.interpretation = {**run.interpretation, "routing": routing, "flow": flow}

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
            run.interpretation = {
                **run.interpretation,
                **interpretation.model_dump(mode="json"),
                "routing": routing,
                "flow": flow,
            }

    def save_revision_interpretation(
        self, run_id: str, interpretation: RequestInterpretation
    ) -> None:
        """Keep staff corrections inspectable without relabelling them as new student memory."""
        with Session(self.engine) as db, db.begin():
            run = _active_run(db, run_id)
            run.interpretation = {**run.interpretation, **interpretation.model_dump(mode="json")}

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
            if run.approved_response_id is not None:
                return  # Checkpoint replay must not replace an already committed approval.
            # Replaying this node after a checkpoint failure must not create a second draft.
            if run.revision < attempt:
                message = Message(
                    conversation_id=run.conversation_id,
                    review_managed=True,
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
                proposal = run.draft_details.get("booking_session_id")
                if proposal:
                    draft = require(db, Message, run.draft_message_id)
                    if body is not None and body != draft.body:
                        conflict(
                            "Regenerate the draft before approving an edited booking response."
                        )
                    session_id = UUID(str(proposal))
                    if run.interpretation.get(
                        "flow"
                    ) != "makeup" or session_id not in candidate_session_ids(run.evidence):
                        conflict(
                            "Regenerate the draft: its booking proposal has no session evidence."
                        )
                    create_booking(db, run, session_id)
                    # The locks acquired by create_booking are still held. Bind the
                    # confirmation to the evidenced schedule, not just a mutable row ID.
                    target = require(db, ClassSession, session_id)
                    snapshots = [
                        item
                        for evidence in run.evidence
                        if evidence.get("tool") == "search_sessions"
                        for item in evidence.get("result", {}).get("items", [])
                        if str(item.get("id")) == str(session_id)
                    ]
                    if snapshots:
                        snapshot = snapshots[-1]
                        for field in ("starts_at", "ends_at"):
                            if field in snapshot and datetime.fromisoformat(
                                snapshot[field]
                            ) != getattr(target, field):
                                conflict(
                                    "The session time changed. Request a new draft before booking."
                                )
                        if snapshot.get("class_id") and str(target.class_id) != str(
                            snapshot["class_id"]
                        ):
                            conflict(
                                "The session class changed. Request a new draft before booking."
                            )
                        for field, attribute in (
                            ("class_name", "name"),
                            ("level", "level"),
                            ("prerequisites", "prerequisites"),
                        ):
                            if field in snapshot and snapshot[field] != getattr(
                                target.regular_class, attribute
                            ):
                                conflict("The class details changed. Request a new draft first.")
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

    def approved_booking(self, run_id: str) -> dict | None:
        with Session(self.engine) as db:
            run = require(db, AgentRun, UUID(run_id))
            proposal = run.draft_details.get("booking_session_id")
            if not run.approved_response_id or not proposal:
                return None
            session = require(db, ClassSession, UUID(proposal))
            conversation = require(db, Conversation, run.conversation_id)
            if conversation.student_id not in session.students:
                return None
            return {
                "session_id": str(session.id),
                "class_name": session.regular_class.name,
                "starts_at": session.starts_at.isoformat(),
                "status": "confirmed",
            }

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
