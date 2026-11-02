"""Google owner login and narrow browser-session permissions.

The existing bearer credential remains an administration credential. A browser
session grants inspection, explicit agent workflow actions, policy editing,
and attendance recording.
"""

import os
import re
import secrets
import time
from dataclasses import dataclass
from hmac import compare_digest
from urllib.parse import urlsplit

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from joserfc.errors import JoseError

router = APIRouter(prefix="/auth", tags=["Owner sign-in"])
AGENT_WRITE = re.compile(
    r"/api/v1/(incoming-emails|agent-runs/[0-9a-fA-F-]{36}/(review|retry)"
    r"|conversations/[0-9a-fA-F-]{36}/agent-runs)"
)


@dataclass(frozen=True)
class OwnerSettings:
    email: str
    client_id: str
    client_secret: str
    session_secret: str
    base_url: str

    @property
    def enabled(self) -> bool:
        return bool(self.email and self.client_id and self.client_secret and self.session_secret)

    @classmethod
    def from_env(cls):
        base = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        parsed = urlsplit(base)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or (parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"})
        ):
            raise RuntimeError("PUBLIC_BASE_URL must be an HTTPS origin (HTTP is local-only).")
        settings = cls(
            os.environ.get("OWNER_EMAIL", "").strip().lower(),
            os.environ.get("GOOGLE_CLIENT_ID", ""),
            os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            os.environ.get("SESSION_SECRET", ""),
            base,
        )
        if settings.session_secret and len(settings.session_secret) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 random characters.")
        return settings


def owner(request: Request) -> dict | None:
    settings = request.app.state.owner_settings
    user = request.session.get("owner")
    if (
        not settings.enabled
        or not isinstance(user, dict)
        or user.get("email") != settings.email
        or not isinstance(user.get("expires_at"), (float, int))
        or user["expires_at"] <= time.time()
    ):
        return None
    return user


def require_csrf(request: Request) -> None:
    expected = request.session.get("csrf", "")
    supplied = request.headers.get("x-csrf-token", "")
    if (
        not expected
        or not compare_digest(expected, supplied)
        or request.headers.get("origin") != request.app.state.owner_settings.base_url
    ):
        raise HTTPException(403, "Refresh the workspace before submitting this action.")


def require_browser_access(request: Request) -> None:
    if owner(request) is None:
        raise HTTPException(401, "Owner sign-in is required.")
    if request.method in {"GET", "HEAD"}:
        return
    policy_write = request.method == "PUT" and request.url.path == "/api/v1/policy"
    document_write = (
        (
            request.method == "POST"
            and request.url.path in {"/api/v1/documents", "/api/v1/documents/upload"}
        )
        or (
            request.method in {"PUT", "DELETE"}
            and re.fullmatch(
                r"/api/v1/documents/[0-9a-fA-F-]{36}(?:/(?:upload|text))?", request.url.path
            )
        )
        or (
            request.method == "PATCH"
            and re.fullmatch(r"/api/v1/documents/[0-9a-fA-F-]{36}/metadata", request.url.path)
        )
    )
    agent_write = request.method == "POST" and AGENT_WRITE.fullmatch(request.url.path)
    attendance_write = request.method == "PUT" and re.fullmatch(
        r"/api/v1/sessions/[0-9a-fA-F-]{36}/attendance/[0-9a-fA-F-]{36}", request.url.path
    )
    if not (policy_write or document_write or agent_write or attendance_write):
        raise HTTPException(403, "The owner workspace cannot change studio records directly.")
    require_csrf(request)


def configure_oauth(application, settings: OwnerSettings) -> None:
    application.state.owner_settings = settings
    oauth = OAuth()
    oauth.register(
        "google",
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
    )
    application.state.google_oauth = oauth.google


@router.get("/me")
def me(request: Request):
    user = owner(request)
    if user is None:
        return {"authenticated": False, "login_available": request.app.state.owner_settings.enabled}
    return {
        "authenticated": True,
        "user": {"email": user["email"], "name": user.get("name", "Owner")},
        "csrf_token": request.session["csrf"],
    }


@router.get("/login")
async def login(request: Request):
    settings = request.app.state.owner_settings
    if not settings.enabled:
        raise HTTPException(503, "Owner Google sign-in has not been configured.")
    return await request.app.state.google_oauth.authorize_redirect(
        request, settings.base_url + "/auth/callback", prompt="select_account"
    )


@router.get("/callback")
async def callback(request: Request):
    settings = request.app.state.owner_settings
    if not settings.enabled:
        raise HTTPException(503, "Owner Google sign-in has not been configured.")
    try:
        token = await request.app.state.google_oauth.authorize_access_token(request)
        user = token.get("userinfo", {})
        if (
            not user.get("sub")
            or user.get("email_verified") is not True
            or str(user.get("email", "")).lower() != settings.email
        ):
            request.session.clear()
            raise HTTPException(403, "This Google account is not the configured owner.")
    except (OAuthError, JoseError) as error:
        request.session.clear()
        raise HTTPException(
            401, "Google sign-in could not be verified. Please sign in again."
        ) from error
    request.session.clear()
    request.session["owner"] = {
        "sub": user["sub"],
        "email": settings.email,
        "name": str(user.get("name", "Owner"))[:200],
        "expires_at": time.time() + 8 * 60 * 60,
    }
    request.session["csrf"] = secrets.token_urlsafe(32)
    return RedirectResponse("/workspace", status_code=303)


@router.post("/logout")
def logout(request: Request):
    require_csrf(request)
    request.session.clear()
    return {"authenticated": False}
