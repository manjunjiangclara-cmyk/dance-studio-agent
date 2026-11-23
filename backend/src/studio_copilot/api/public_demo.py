"""Anonymous fictional demo API, separate from the authenticated staff API."""

import os
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from studio_copilot.public_demo.fixtures import PUBLIC_DOCUMENTS
from studio_copilot.public_demo.records import FictionalRecords
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
    scenario: Literal["booking", "document", "noah", "riley"]
    request_id: UUID


class WalkthroughRun(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    student: UUID | Literal["new"]
    email_body: str = Field(min_length=1, max_length=2000)
    previous_token: str | None = Field(default=None, max_length=100)


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    body: str | None = Field(default=None, min_length=1, max_length=20_000)


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    teacher_answers: list[str] = Field(default_factory=list, max_length=9)


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


def service(request: Request):
    if os.environ.get("STUDIO_PUBLIC_LIVE_DEMO") != "true":
        raise HTTPException(503, "Live demo is unavailable. Please try again later.")
    base_url = request.app.state.owner_settings.base_url
    if request.headers.get("origin") != base_url:
        raise HTTPException(403, "Open the live demo from its configured website.")
    if not os.environ.get("OPENAI_MODEL") or not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Live demo is not configured. Please try again later.")
    path = os.environ.get("STUDIO_PUBLIC_DEMO_DB")
    if not path:
        raise HTTPException(503, "Live demo allowance storage is not configured.")
    # Construction is idempotent and SQLite serializes initialization across workers.
    if urlsplit(base_url).hostname in {"localhost", "127.0.0.1", "::1"}:
        return PublicDemo(path, daily_run_limit=None)
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


@router.get("/cases/{scenario}")
def example_case(scenario: Literal["booking", "document", "noah", "riley"]):
    return {"messages": FictionalRecords().context(scenario)["history"]}


@router.post("/runs")
def create(request: Request, body: CreateRun):
    return service(request).create(body.scenario, str(body.request_id))


@router.post("/walkthrough/runs")
def create_walkthrough_run(request: Request, body: WalkthroughRun):
    return service(request).create_walkthrough(
        str(body.request_id), str(body.student), body.email_body, body.previous_token
    )


@router.post("/evidence")
def evidence(request: Request, body: Empty):
    return service(request).execute(token(request), "evidence")


@router.post("/draft")
def draft(request: Request, body: DraftInput):
    return service(request).execute(token(request), "draft", teacher_answers=body.teacher_answers)


@router.post("/approve")
def approve(request: Request, body: ApprovalInput):
    return service(request).execute(
        token(request), "approve", revision=body.revision, body=body.body
    )


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
