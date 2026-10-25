from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.persistence.locking import guard_message
from studio_copilot.agent.service import supersede_pending
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db, Paging, page, save
from studio_copilot.persistence.models import AgentRun, Conversation, Message, Student

router = APIRouter(tags=["Conversations"])


@router.post("/conversations", response_model=s.ConversationRead, status_code=201)
def create_conversation(body: s.ConversationCreate, db: Db):
    require(db, Student, body.student_id)
    return save(db, Conversation(**body.model_dump()))


@router.get("/conversations", response_model=s.Page[s.ConversationRead])
def list_conversations(db: Db, paging: Paging, student_id: UUID | None = None):
    statement = select(Conversation).order_by(Conversation.created_at, Conversation.id)
    if student_id:
        statement = statement.where(Conversation.student_id == student_id)
    return page(db, statement, paging)


@router.get("/conversations/{conversation_id}", response_model=s.ConversationRead)
def get_conversation(conversation_id: UUID, db: Db):
    return require(db, Conversation, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=s.ConversationRead)
def update_conversation(conversation_id: UUID, body: s.ConversationPatch, db: Db):
    record = require(db, Conversation, conversation_id, lock=True)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(record, name, value)
    return save(db, record)


@router.post(
    "/conversations/{conversation_id}/messages", response_model=s.MessageRead, status_code=201
)
def create_message(conversation_id: UUID, body: s.MessageCreate, db: Db):
    conversation = require(db, Conversation, conversation_id)
    guard_message(db, conversation.student_id)
    message = Message(conversation_id=conversation_id, **body.model_dump(exclude_none=True))
    db.add(message)
    db.flush()
    if body.kind == "student_email":
        supersede_pending(db, conversation_id)
    return save(db, message)


@router.get("/conversations/{conversation_id}/messages", response_model=s.Page[s.MessageRead])
def list_messages(conversation_id: UUID, db: Db, paging: Paging):
    require(db, Conversation, conversation_id)
    return page(
        db,
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.occurred_at, Message.created_at, Message.id),
        paging,
    )


@router.get("/messages/{message_id}", response_model=s.MessageRead)
def get_message(message_id: UUID, db: Db):
    return require(db, Message, message_id)


@router.patch("/messages/{message_id}", response_model=s.MessageRead)
def edit_draft(message_id: UUID, body: s.DraftPatch, db: Db):
    record = require(db, Message, message_id, lock=True)
    if record.kind != "assistant_draft":
        conflict("Only drafts can be edited; add a staff note to correct received information.")
    if db.scalar(select(AgentRun.id).where(AgentRun.draft_message_id == record.id)):
        conflict("Edit an agent draft through its review endpoint with the expected revision.")
    record.body = body.body
    return save(db, record)
