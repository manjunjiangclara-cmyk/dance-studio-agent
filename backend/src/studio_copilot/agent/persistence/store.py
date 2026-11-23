"""Short database transactions for graph context, memory, drafts, and approval.

No model calls happen here. LangGraph checkpoint storage is managed separately.
"""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.contracts import RequestInterpretation, ReviewedMemory
from studio_copilot.agent.proposals import (
    candidate_session_ids,
    confirmation_body,
    legacy_confirmation_body,
)
from studio_copilot.agent.question_resolutions import require_resolved_questions
from studio_copilot.agent.tools import enrolments
from studio_copilot.bookings.service import create_booking
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Conversation,
    Location,
    Message,
    Student,
    StudioClass,
)


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


def _confirmed_booking(
    db: Session, student_id: UUID, proposal: str | None, *, lock: bool = False
) -> dict | None:
    if not proposal:
        return None
    session_id = UUID(proposal)
    session = db.get(ClassSession, session_id)
    if session is not None and lock:
        require(db, StudioClass, session.class_id, lock=True)
        session = db.get(ClassSession, session_id, populate_existing=True, with_for_update=True)
    if session is None or student_id not in session.students:
        return None
    group = session.regular_class
    location = require(db, Location, group.location_id, lock=True) if lock else group.location
    return {
        "session_id": str(session.id),
        "class_name": group.name,
        "starts_at": session.starts_at.astimezone(ZoneInfo(location.timezone)).isoformat(),
        "location_name": location.name,
        "status": "confirmed",
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
            order = (Message.occurred_at, Message.created_at, Message.id)
            messages = db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    tuple_(*order) <= (source.occurred_at, source.created_at, source.id),
                    Message.kind.in_(("student_email", "teacher_response")),
                )
                .order_by(*order)
            )
            history, approved_replies = [], []
            for message in messages:
                if message.kind == "student_email":
                    history.append(_message_data(message))
                else:
                    approved_replies.append({**_message_data(message), "delivery": "unconfirmed"})

            confirmed_bookings = []
            if approved_replies:
                approvals = db.scalars(
                    select(AgentRun).where(
                        AgentRun.conversation_id == conversation.id,
                        AgentRun.approved_response_id.in_(
                            UUID(reply["id"]) for reply in approved_replies
                        ),
                        AgentRun.draft_details["booking_session_id"].astext.is_not(None),
                    )
                )
                for approval in approvals:
                    booking = _confirmed_booking(
                        db, student.id, approval.draft_details["booking_session_id"]
                    )
                    if booking:
                        confirmed_bookings.append(
                            {**booking, "approved_response_id": str(approval.approved_response_id)}
                        )

            context, summary = student.context, student.ai_summary
            memory = context.get("_agent_memory", {})
            if conversation.thread_id is not None:
                visible_conversations = {str(conversation.id)}
            elif memory:
                # Legacy conversations can share legacy summaries. Threaded requests
                # remain scoped even when the next email uses legacy intake.
                visible_conversations = {
                    str(identifier)
                    for identifier in db.scalars(
                        select(Conversation.id).where(
                            Conversation.student_id == student.id,
                            Conversation.thread_id.is_(None),
                        )
                    )
                }
            else:
                visible_conversations = set()
            requests = memory.get("requests", {})
            responses = memory.get("approved_responses", {})
            scoped_requests = {
                key: entry for key, entry in requests.items() if key in visible_conversations
            }
            scoped_responses = {
                key: entry
                for key, entry in responses.items()
                if entry.get("conversation_id") in visible_conversations
            }
            if (
                conversation.thread_id is not None
                or scoped_requests != requests
                or scoped_responses != responses
            ):
                scoped_memory = {
                    "preferences": memory.get("preferences", {}),
                    "requests": scoped_requests,
                    "approved_responses": scoped_responses,
                }
                context = {**context, "_agent_memory": scoped_memory}
                summary = _memory_summary(scoped_memory)
            return {
                "source": _message_data(source),
                "conversation_id": str(conversation.id),
                "student": {
                    "id": str(student.id),
                    "name": student.display_name,
                    "email": student.email,
                    "highest_level": student.highest_level,
                    "context": context,
                    "ai_summary": summary,
                },
                "enrolments": enrolments(student),
                "history": history,
                "approved_replies": approved_replies,
                "confirmed_bookings": confirmed_bookings,
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
                from studio_copilot.documents.online import OnlineError, require_current_sources

                try:
                    require_current_sources(db, run)
                except OnlineError:
                    conflict(
                        "Document sources changed or were disabled. "
                        "Regenerate the draft before approval."
                    )
                for evidence in run.evidence:
                    if evidence.get("tool") != "student_context" or not evidence.get(
                        "arguments", {}
                    ).get("booked_schedule"):
                        continue
                    conversation = require(db, Conversation, run.conversation_id)
                    for booking in evidence["result"]["confirmed_bookings"]:
                        snapshot = {
                            key: value
                            for key, value in booking.items()
                            if key != "approved_response_id"
                        }
                        current = _confirmed_booking(
                            db, conversation.student_id, booking["session_id"], lock=True
                        )
                        if current != snapshot:
                            conflict("The confirmed makeup changed. Regenerate the schedule reply.")
                require_resolved_questions(run)
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
                    location = require(db, Location, target.regular_class.location_id, lock=True)
                    conversation = require(db, Conversation, run.conversation_id)
                    student = require(db, Student, conversation.student_id)
                    local_start = target.starts_at.astimezone(ZoneInfo(location.timezone))
                    session_details = target.regular_class.name, location.name, local_start
                    if draft.body not in (
                        confirmation_body(*session_details, student.display_name),
                        legacy_confirmation_body(*session_details),
                    ):
                        conflict("Session details changed. Request a new draft before booking.")
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
                        for field, value in (
                            ("location_id", str(location.id)),
                            ("location_name", location.name),
                        ):
                            if field in snapshot and snapshot[field] != value:
                                conflict("The session location changed. Request a new draft first.")
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
            if not run.approved_response_id:
                return None
            conversation = require(db, Conversation, run.conversation_id)
            return _confirmed_booking(
                db, conversation.student_id, run.draft_details.get("booking_session_id")
            )

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
