"""Document CRUD, validation, and owner access."""

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import Document
from tests.unit.test_website_auth import session_cookie


def payload(text="Studio information", **overrides):
    return {
        "title": " Welcome ",
        "filename": "welcome.md",
        "content_base64": base64.b64encode(text.encode()).decode(),
    } | overrides


@pytest.fixture
def client(monkeypatch):
    for name, value in {
        "OWNER_EMAIL": "owner@example.test",
        "GOOGLE_CLIENT_ID": "test",
        "GOOGLE_CLIENT_SECRET": "test",
        "SESSION_SECRET": "test-session-secret-which-is-longer-than-32-characters",
        "PUBLIC_BASE_URL": "https://studio.example.test",
    }.items():
        monkeypatch.setenv(name, value)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Document.__table__.create(engine)
    with TestClient(
        create_app(engine, admin_token="test"), base_url="https://studio.example.test"
    ) as test_client:
        yield test_client
    engine.dispose()


def test_crud_persists_and_validates(client):
    headers = {"Authorization": "Bearer test"}
    assert client.get("/api/v1/documents", headers=headers).json() == []
    response = client.post("/api/v1/documents", headers=headers, json=payload("你好"))
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Welcome"
    path = "/api/v1/documents/" + created["id"]
    assert client.get(path, headers=headers).json()["content"] == "你好"
    assert "content" not in client.get("/api/v1/documents", headers=headers).json()[0]
    changed = client.put(
        path, headers=headers, json=payload("Updated", title="New", filename="new.txt")
    )
    assert changed.status_code == 200
    for body in [
        payload(title=" "),
        payload(filename="data.pdf"),
        payload(filename="../x.md"),
        payload(content_base64="//8="),
        payload(content_base64="!!!"),
        payload(content_base64=base64.b64encode(b"x" * 1_000_001).decode()),
        payload("nul\0byte"),
    ]:
        assert client.put(path, headers=headers, json=body).status_code == 422
    assert client.get(path, headers=headers).json()["content"] == "Updated"
    assert client.delete(path, headers=headers).status_code == 200
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404


def test_owner_requires_login_origin_and_csrf(client):
    path = "/api/v1/documents"
    assert client.get(path).status_code == 401
    assert client.post(path, json=payload()).status_code == 401
    client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
    assert client.get(path).status_code == 200
    for headers in [
        {},
        {"origin": "https://evil.test", "x-csrf-token": "csrf-for-test"},
        {"origin": "https://studio.example.test", "x-csrf-token": "wrong"},
    ]:
        assert client.post(path, json=payload(), headers=headers).status_code == 403
    valid = {"origin": "https://studio.example.test", "x-csrf-token": "csrf-for-test"}
    created = client.post(path, json=payload(), headers=valid)
    assert created.status_code == 201
    item = path + "/" + created.json()["id"]
    assert client.put(item, json=payload("change")).status_code == 403
    assert client.delete(item).status_code == 403
    assert client.get(item).json()["content"] == "Studio information"
    assert client.delete(item, headers=valid).status_code == 200
