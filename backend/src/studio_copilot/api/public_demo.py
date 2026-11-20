"""Anonymous fixed-input demo API, separate from the authenticated staff API."""

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_copilot.public_demo.fixtures import CUSTOM_STUDENTS, PUBLIC_DOCUMENTS
from studio_copilot.public_demo.service import PublicDemo


class LimitedRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def limited(request):
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 120000:
                    raise HTTPException(413, "Demo request too large.")
                chunks.append(chunk)
            request._body = b"".join(chunks)
            return await handler(request)

        return limited


router = APIRouter(prefix="/api/public-demo", tags=["Public demo"], route_class=LimitedRoute)


class CreateRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["booking", "document", "custom"]
    request_id: UUID
    student: str | None = Field(default=None, max_length=36)
    email_body: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_custom_email(self):
        if self.scenario == "custom":
            if (
                self.student not in CUSTOM_STUDENTS
                or not self.email_body
                or not self.email_body.strip()
            ):
                raise ValueError("Select a fictional student and write an email.")
        elif self.student is not None or self.email_body is not None:
            raise ValueError("Guided scenarios use fixed inputs.")
        return self


class CreateThread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student: str = Field(max_length=36)


class TurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    email_body: str = Field(min_length=1, max_length=2000)


class ReplyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    teacher_answers: list[str] = Field(default_factory=list, max_length=9)


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


def service(request: Request):
    if os.environ.get("STUDIO_PUBLIC_LIVE_DEMO") != "true":
        raise HTTPException(503, "Live demo is unavailable. Please try again later.")
    if request.headers.get("origin") != request.app.state.owner_settings.base_url:
        raise HTTPException(403, "Open the live demo from its configured website.")
    if not os.environ.get("OPENAI_MODEL") or not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Live demo is not configured. Please try again later.")
    path = os.environ.get("STUDIO_PUBLIC_DEMO_DB")
    if not path:
        raise HTTPException(503, "Live demo allowance storage is not configured.")
    # Construction is idempotent and SQLite serializes initialization across workers.
    return PublicDemo(path)


def token(request):
    value = request.headers.get("authorization", "")
    if not value.startswith("Bearer ") or len(value) > 100:
        raise HTTPException(401, "A demo-run token is required.")
    return value[7:]


@router.get("/documents")
def documents():
    return [
        {
            **document,
            "current_revision": document["revision"],
            "byte_size": len(document["content"].encode("utf-8")),
            "ingestion_status": "ready",
            "updated_at": None,
            "sha256": "",
            "hash_origin": "stored_text_utf8",
            "effective_from": None,
            "effective_to": None,
        }
        for document in PUBLIC_DOCUMENTS
    ]


@router.post("/threads")
def create_thread(request: Request, body: CreateThread):
    return service(request).create_thread(body.student)


@router.post("/threads/current")
def get_thread(request: Request, body: Empty):
    return service(request).thread_view(token(request))


@router.post("/threads/current/turns")
def add_turn(request: Request, body: TurnInput):
    return service(request).add_turn(token(request), str(body.request_id), body.email_body)


@router.post("/threads/current/turns/{turn_id}/evidence")
def thread_evidence(request: Request, turn_id: UUID, body: Empty):
    return service(request).thread_execute(token(request), str(turn_id), "evidence")


@router.post("/threads/current/turns/{turn_id}/draft")
def thread_draft(request: Request, turn_id: UUID, body: DraftInput):
    return service(request).thread_execute(
        token(request), str(turn_id), "draft", teacher_answers=body.teacher_answers
    )


@router.post("/threads/current/turns/{turn_id}/accept")
def accept_reply(request: Request, turn_id: UUID, body: ReplyInput):
    return service(request).accept_reply(token(request), str(turn_id), body.body)


@router.post("/threads/current/approve")
def approve_mock(request: Request, body: ApprovalInput):
    return service(request).approve_mock(token(request), body.revision)


@router.post("/runs")
def create(request: Request, body: CreateRun):
    return service(request).create(
        body.scenario, str(body.request_id), student=body.student, email_body=body.email_body
    )


@router.post("/evidence")
def evidence(request: Request, body: Empty):
    return service(request).execute(token(request), "evidence")


@router.post("/draft")
def draft(request: Request, body: DraftInput):
    return service(request).execute(token(request), "draft", teacher_answers=body.teacher_answers)


def create_public_demo_app():
    """Optional standalone local preview, without a workspace database connection."""
    from types import SimpleNamespace

    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    application.state.owner_settings = SimpleNamespace(
        base_url=os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    )
    application.include_router(router)

    @application.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return application
