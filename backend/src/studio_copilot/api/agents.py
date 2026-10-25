from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from studio_copilot.administration.service import AdministrationError, require
from studio_copilot.agent.contracts import ModelError, Review
from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.service import AgentService
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db
from studio_copilot.persistence.models import AgentRun

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
    return agent.receive_email(str(body.sender), body.body)
