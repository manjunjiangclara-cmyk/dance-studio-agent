from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select

from studio_copilot.administration.service import AdministrationError, require
from studio_copilot.agent.contracts import ModelError, Review
from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.service import AgentService
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db, Paging
from studio_copilot.persistence.models import AgentRun, Conversation, Student

router = APIRouter(tags=["Agent"])


def get_agent(request: Request):
    if request.app.state.agent_service is not None:
        yield request.app.state.agent_service
        return
    try:
        model = OpenAIModel()
    except ModelError as error:
        raise AdministrationError(503, "agent_unavailable", str(error)) from error
    try:
        yield AgentService(request.app.state.engine, model)
    finally:
        model.client.close()


Agent = Annotated[AgentService, Depends(get_agent)]


@router.get("/agent-runs", response_model=s.Page[s.AgentRunSummary])
def list_runs(
    db: Db,
    paging: Paging,
    status: Literal[
        "running", "awaiting_review", "finalizing", "approved", "closed", "superseded", "failed"
    ]
    | None = None,
    student_id: UUID | None = None,
    conversation_id: UUID | None = None,
    q: str | None = None,
):
    statement = (
        select(AgentRun, Student)
        .join(Conversation, AgentRun.conversation_id == Conversation.id)
        .join(Student, Conversation.student_id == Student.id)
    )
    for column, value in [
        (AgentRun.status, status),
        (Conversation.student_id, student_id),
        (AgentRun.conversation_id, conversation_id),
    ]:
        if value is not None:
            statement = statement.where(column == value)
    if q and q.strip():
        statement = statement.where(
            or_(
                Student.display_name.icontains(q.strip(), autoescape=True),
                Student.email.icontains(q.strip(), autoescape=True),
            )
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    limit, offset = paging
    records = db.execute(
        statement.order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    for run, student in records:
        summary = run.interpretation.get("request_summary", "")
        items.append(
            {
                **{
                    key: getattr(run, key)
                    for key in (
                        "id",
                        "created_at",
                        "updated_at",
                        "conversation_id",
                        "source_message_id",
                        "status",
                        "revision",
                        "error",
                    )
                },
                "student_id": student.id,
                "student_name": student.display_name,
                "student_email": student.email,
                "request_summary": summary if isinstance(summary, str) else "",
                "routing": run.interpretation.get("routing"),
                "flow": run.interpretation.get("flow"),
            }
        )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/conversations/{conversation_id}/agent-runs", response_model=s.AgentRunRead)
def start(conversation_id: UUID, body: s.AgentStart, agent: Agent):
    return agent.start(conversation_id, body.source_message_id)


@router.get("/agent-runs/{run_id}", response_model=s.AgentRunRead)
def get_run(run_id: UUID, db: Db):
    return require(db, AgentRun, run_id)


@router.post("/agent-runs/{run_id}/review", response_model=s.AgentRunRead)
def review_run(run_id: UUID, body: Review, agent: Agent):
    return agent.review(run_id, body)


@router.post("/agent-runs/{run_id}/retry", response_model=s.AgentRunRead)
def retry_run(run_id: UUID, agent: Agent):
    return agent.retry(run_id)


@router.post("/incoming-emails", response_model=s.AgentRunRead)
def receive_email(body: s.IncomingEmail, agent: Agent):
    """Receive an email, resolve its sender and conversation, and generate a reviewable draft."""
    return agent.receive_email(
        str(body.sender), body.body, thread_id=body.thread_id, subject=body.subject
    )
