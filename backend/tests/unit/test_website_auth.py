"""Owner access is tested without Google, PostgreSQL, or model requests."""

import base64
import json
import time
from unittest.mock import AsyncMock

import pytest
from authlib.integrations.base_client.errors import OAuthError
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from joserfc.errors import InvalidClaimError
from sqlalchemy import create_engine

from studio_copilot.api.app import create_app
from studio_copilot.api.auth import OwnerSettings

SECRET = "test-session-secret-which-is-longer-than-32-characters"
OWNER = "owner@example.test"


@pytest.fixture
def owner_app(monkeypatch):
    for name, value in {
        "OWNER_EMAIL": OWNER,
        "GOOGLE_CLIENT_ID": "google-test-client",
        "GOOGLE_CLIENT_SECRET": "google-test-secret",
        "SESSION_SECRET": SECRET,
        "PUBLIC_BASE_URL": "https://studio.example.test",
    }.items():
        monkeypatch.setenv(name, value)
    return create_app(create_engine("sqlite://"), admin_token="test-admin")


def session_cookie(*, email=OWNER, expires_at=None):
    payload = {
        "owner": {
            "email": email,
            "name": "Owner",
            "sub": "google-subject",
            "expires_at": time.time() + 60 if expires_at is None else expires_at,
        },
        "csrf": "csrf-for-test",
    }
    value = base64.b64encode(json.dumps(payload).encode())
    return TimestampSigner(SECRET).sign(value).decode()


def test_owner_session_is_private_and_expires(owner_app):
    with TestClient(owner_app, base_url="https://studio.example.test") as client:
        assert client.get("/auth/me").json() == {"authenticated": False, "login_available": True}
        assert client.get("/api/v1/students").status_code == 401
        client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
        identity = client.get("/auth/me").json()
        assert identity["authenticated"] is True
        assert identity["user"]["email"] == OWNER
        assert identity["csrf_token"] == "csrf-for-test"
        assert "test-admin" not in json.dumps(identity)
        assert client.get("/auth/me").headers["cache-control"] == "no-store"
        for cookie in [
            session_cookie(email="visitor@example.test"),
            session_cookie(expires_at=time.time() - 1),
            session_cookie() + "forged",
        ]:
            client.cookies.clear()
            client.cookies.set("studio_owner", cookie, domain="studio.example.test", path="/")
            assert client.get("/auth/me").json()["authenticated"] is False
            assert client.get("/api/v1/agent-runs").status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/incoming-emails",
        "/api/v1/agent-runs/00000000-0000-0000-0000-000000000000/review",
        "/api/v1/agent-runs/00000000-0000-0000-0000-000000000000/retry",
    ],
)
def test_anonymous_cannot_call_agent_actions(owner_app, path):
    with TestClient(owner_app) as client:
        assert client.post(path, json={}).status_code == 401


def test_browser_cannot_write_official_records_and_requires_csrf(owner_app):
    with TestClient(owner_app, base_url="https://studio.example.test") as client:
        client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
        valid = {"origin": "https://studio.example.test", "x-csrf-token": "csrf-for-test"}
        for path in ["/api/v1/students", "/api/v1/enrolments", "/api/v1/conversations"]:
            assert client.post(path, json={}, headers=valid).status_code == 403
        assert (
            client.patch(
                "/api/v1/students/00000000-0000-0000-0000-000000000000", json={}, headers=valid
            ).status_code
            == 403
        )
        for headers in [
            {},
            {"origin": "https://evil.example", "x-csrf-token": "csrf-for-test"},
            {"origin": "https://studio.example.test", "x-csrf-token": "wrong"},
        ]:
            assert (
                client.post("/api/v1/incoming-emails", json={}, headers=headers).status_code == 403
            )
        # Passing authentication reaches validation, without invoking the model.
        assert (
            client.post(
                "/api/v1/conversations/not-a-uuid/agent-runs", json={}, headers=valid
            ).status_code
            == 403
        )
        # Logout requires the same cross-site protection and clears the session.
        assert client.post("/auth/logout").status_code == 403
        assert client.post("/auth/logout", headers=valid).status_code == 200
        assert client.get("/auth/me").json()["authenticated"] is False


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "visitor", "email": "visitor@example.test", "email_verified": True},
        {"sub": "owner", "email": OWNER, "email_verified": False},
        {"email": OWNER, "email_verified": True},
    ],
)
def test_google_callback_rejects_non_owner_or_unverified_claims(owner_app, claims):
    owner_app.state.google_oauth.authorize_access_token = AsyncMock(
        return_value={"userinfo": claims}
    )
    with TestClient(owner_app, base_url="https://studio.example.test") as client:
        assert client.get("/auth/callback").status_code == 403
        assert client.get("/auth/me").json()["authenticated"] is False


def test_google_callback_uses_verified_claims_and_never_stores_provider_token(owner_app):
    owner_app.state.google_oauth.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {"sub": "owner-sub", "email": OWNER.upper(), "email_verified": True},
            "access_token": "provider-secret-never-store-this",
        }
    )
    with TestClient(owner_app, base_url="https://studio.example.test") as client:
        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/workspace"
        cookie = response.headers["set-cookie"]
        assert all(flag in cookie.lower() for flag in ["httponly", "secure", "samesite=lax"])
        signed = client.cookies.get("studio_owner")
        payload = json.loads(base64.b64decode(TimestampSigner(SECRET).unsign(signed)))
        assert "provider-secret" not in json.dumps(payload)
        assert payload["owner"]["sub"] == "owner-sub"
        assert client.get("/auth/me").json()["authenticated"] is True


@pytest.mark.parametrize(
    "failure",
    [
        OAuthError("invalid_state", "sensitive-provider-detail"),
        InvalidClaimError("sensitive-provider-detail"),
    ],
)
def test_oauth_protocol_failure_is_safe(owner_app, failure):
    owner_app.state.google_oauth.authorize_access_token = AsyncMock(side_effect=failure)
    with TestClient(owner_app) as client:
        response = client.get("/auth/callback")
        assert response.status_code == 401
        assert "sensitive-provider-detail" not in response.text


def test_no_oauth_configuration_keeps_public_mode_available(monkeypatch):
    for name in ["OWNER_EMAIL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SESSION_SECRET"]:
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app(create_engine("sqlite://"), admin_token="test")) as client:
        assert client.get("/auth/me").json() == {"authenticated": False, "login_available": False}
        assert client.get("/auth/login").status_code == 503


@pytest.mark.parametrize(
    "base", ["http://public.example", "https://a.example/path", "https://a.example?q=x"]
)
def test_shared_deployment_requires_an_https_origin(monkeypatch, base):
    monkeypatch.setenv("PUBLIC_BASE_URL", base)
    with pytest.raises(RuntimeError, match="HTTPS origin"):
        OwnerSettings.from_env()
