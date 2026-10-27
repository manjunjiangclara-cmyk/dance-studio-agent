"""Add an approved student to the session inside the caller's transaction."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.makeup import revalidate_makeup
from studio_copilot.persistence.models import AgentRun, ClassSession, Conversation, StudioClass


def create_booking(db: Session, run: AgentRun, session_id: UUID) -> ClassSession:
    revalidate_makeup(db, run, session_id)
    target = require(db, ClassSession, session_id)
    require(db, StudioClass, target.class_id, lock=True)
    target = require(db, ClassSession, session_id, lock=True)
    conversation = require(db, Conversation, run.conversation_id)
    if target.starts_at <= datetime.now(UTC):
        conflict("Only a future dated session can be booked.")
    if conversation.student_id in target.students:
        conflict("The student is already in this session's student list.")
    if len(target.students) >= target.capacity:
        conflict("The selected session has no remaining capacity.")
    target.students.append(conversation.student_id)
    db.flush()
    return target
