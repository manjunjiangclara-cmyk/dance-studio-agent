"""Run with uvicorn studio_copilot.api.app:app --host 127.0.0.1."""

import os
import secrets
from contextlib import asynccontextmanager
from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from studio_copilot.administration.service import AdministrationError
from studio_copilot.agent.telemetry import configure_logging
from studio_copilot.api import (
    agents,
    auth,
    conversations,
    database,
    enrolments,
    policy,
    students,
    timetable,
)
from studio_copilot.api.common import Db
from studio_copilot.api.website import install_website
from studio_copilot.persistence.database import make_engine, make_session_factory

bearer = HTTPBearer(auto_error=False)


def require_admin(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    if credential is not None:
        if compare_digest(credential.credentials.encode(), request.app.state.admin_token.encode()):
            return
        raise HTTPException(401, "A valid admin bearer token is required.")
    auth.require_browser_access(request)


def create_app(
    engine: Engine | None = None, *, admin_token: str | None = None, agent_service=None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configure_logging()
        token = admin_token if admin_token is not None else os.environ.get("ADMIN_API_TOKEN")
        if not token:
            raise RuntimeError("Set ADMIN_API_TOKEN before starting the staff API.")
        database = engine if engine is not None else make_engine()
        application.state.admin_token = token
        application.state.engine = database
        application.state.agent_service = agent_service
        application.state.session_factory = make_session_factory(database)
        try:
            yield
        finally:
            if engine is None:
                database.dispose()

    application = FastAPI(
        title="Dance Studio Administration API",
        version="0.3.0",
        description="Staff administration and teacher-reviewed AI drafts. No email delivery.",
        lifespan=lifespan,
    )
    owner_settings = auth.OwnerSettings.from_env()
    auth.configure_oauth(application, owner_settings)
    application.add_middleware(
        SessionMiddleware,
        secret_key=owner_settings.session_secret or secrets.token_urlsafe(32),
        session_cookie="studio_owner",
        max_age=8 * 60 * 60,
        same_site="lax",
        https_only=owner_settings.base_url.startswith("https://"),
    )
    application.include_router(auth.router)

    @application.middleware("http")
    async def browser_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith(("/api/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(AdministrationError)
    async def administration_error(_request: Request, error: AdministrationError):
        return JSONResponse(
            status_code=error.status,
            content={"error": {"code": error.code, "message": error.message}},
        )

    @application.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, _error: IntegrityError):
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "conflict",
                    "message": "The change conflicts with an existing record or constraint.",
                }
            },
        )

    @application.exception_handler(OperationalError)
    async def database_unavailable(_request: Request, _error: OperationalError):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": "The database is temporarily unavailable.",
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": [
                        {
                            "location": list(item["loc"]),
                            "message": item["msg"],
                            "type": item["type"],
                        }
                        for item in error.errors()
                    ],
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException):
        return JSONResponse(
            status_code=error.status_code,
            headers=error.headers,
            content={
                "error": {
                    "code": "unauthorized" if error.status_code == 401 else "http_error",
                    "message": str(error.detail),
                }
            },
        )

    @application.get("/health", tags=["Health"])
    def health(db: Db):
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    for router in [
        students.router,
        timetable.router,
        enrolments.router,
        conversations.router,
        agents.router,
        database.router,
        policy.router,
    ]:
        application.include_router(router, prefix="/api/v1", dependencies=[Depends(require_admin)])
    install_website(application)
    return application


app = create_app()
