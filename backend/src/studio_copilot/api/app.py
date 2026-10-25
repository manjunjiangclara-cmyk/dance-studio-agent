"""Run with uvicorn studio_copilot.api.app:app --host 127.0.0.1."""

import os
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

from studio_copilot.administration.service import AdministrationError
from studio_copilot.api import conversations, enrolments, students, timetable
from studio_copilot.api.common import Db
from studio_copilot.persistence.database import make_engine, make_session_factory

bearer = HTTPBearer(auto_error=False)


def require_admin(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    if credential is None or not compare_digest(
        credential.credentials.encode(), request.app.state.admin_token.encode()
    ):
        raise HTTPException(
            401, "A valid admin bearer token is required.", headers={"WWW-Authenticate": "Bearer"}
        )


def create_app(engine: Engine | None = None, *, admin_token: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        token = admin_token if admin_token is not None else os.environ.get("ADMIN_API_TOKEN")
        if not token:
            raise RuntimeError("Set ADMIN_API_TOKEN before starting the staff API.")
        database = engine if engine is not None else make_engine()
        application.state.admin_token = token
        application.state.session_factory = make_session_factory(database)
        try:
            yield
        finally:
            if engine is None:
                database.dispose()

    application = FastAPI(
        title="Ballet Studio Administration API",
        version="0.2.0",
        description="Local staff administration with synthetic data. No AI or email sending.",
        lifespan=lifespan,
    )

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

    for router in [students.router, timetable.router, enrolments.router, conversations.router]:
        application.include_router(router, prefix="/api/v1", dependencies=[Depends(require_admin)])
    return application


app = create_app()
