"""Anonymous fixed-input demo API, separate from the authenticated staff API."""

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict

from studio_copilot.public_demo.service import PublicDemo


class LimitedRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def limited(request):
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 1024:
                    raise HTTPException(413, "Demo request too large.")
                chunks.append(chunk)
            request._body = b"".join(chunks)
            return await handler(request)

        return limited


router = APIRouter(prefix="/api/public-demo", tags=["Public demo"], route_class=LimitedRoute)


class CreateRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["booking", "document"]
    request_id: UUID


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


def service(request: Request):
    if os.environ.get("STUDIO_PUBLIC_LIVE_DEMO") != "true":
        raise HTTPException(503, "Live demo is unavailable. Try the recorded example.")
    if request.headers.get("origin") != request.app.state.owner_settings.base_url:
        raise HTTPException(403, "Open the live demo from its configured website.")
    if not os.environ.get("OPENAI_MODEL") or not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Live demo is not configured. Try the recorded example.")
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


@router.post("/runs")
def create(request: Request, body: CreateRun):
    return service(request).create(body.scenario, str(body.request_id))


@router.post("/evidence")
def evidence(request: Request, body: Empty):
    return service(request).execute(token(request), "evidence")


@router.post("/draft")
def draft(request: Request, body: Empty):
    return service(request).execute(token(request), "draft")


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
