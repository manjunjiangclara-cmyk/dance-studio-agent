"""Policy editing exercises the real file resource without a database or model."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from studio_copilot.agent.policy import Policy, load_policy, save_policy
from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from tests.unit import test_website_auth as auth_tests

owner_app = auth_tests.owner_app
session_cookie = auth_tests.session_cookie

ORIGINAL = {
    "version": "1",
    "level_order": [],
    "absence_notice_before_start": True,
    "explanation": "Notice must arrive before class.",
}
UPDATED = {
    "version": "2",
    "level_order": ["Beginner", "Intermediate", "Advanced"],
    "absence_notice_before_start": False,
    "explanation": "Teacher reviews the request.\nNo automatic entitlement.",
}


@pytest.fixture
def resource(tmp_path, monkeypatch):
    path = tmp_path / "studio.yaml"
    monkeypatch.setenv("STUDIO_POLICY_PATH", str(path))
    save_policy(Policy(**ORIGINAL))
    return path


def test_roundtrip_matches_new_agent_policy_and_preserves_loaded_snapshot(resource):
    service = AgentService(None, None, policy_path=resource)
    snapshot = service._policy()
    app = create_app(create_engine("sqlite://"), admin_token="test", agent_service=service)
    with TestClient(app, headers={"Authorization": "Bearer test"}) as client:
        assert client.get("/api/v1/policy").json() == ORIGINAL
        response = client.put("/api/v1/policy", json=UPDATED)
        assert response.status_code == 200
        assert response.json() == UPDATED
        assert client.get("/api/v1/policy").json() == UPDATED
    assert load_policy(resource) == service._policy() == UPDATED
    assert snapshot == ORIGINAL


@pytest.mark.parametrize(
    "patch",
    [
        {"version": " "},
        {"explanation": ""},
        {"version": "v" * 101},
        {"explanation": "x" * 10001},
        {"absence_notice_before_start": "false"},
        {"credit_limit": 2},
        {"level_order": ["Beginner", "beginner"]},
        {"level_order": [""]},
    ],
)
def test_invalid_policy_keeps_file_unchanged(resource, patch):
    before = resource.read_bytes()
    with TestClient(
        create_app(create_engine("sqlite://"), admin_token="test"),
        headers={"Authorization": "Bearer test"},
    ) as client:
        response = client.put("/api/v1/policy", json=ORIGINAL | patch)
        assert response.status_code == 422
    assert resource.read_bytes() == before


def test_owner_policy_write_requires_csrf_and_exact_permission(owner_app, resource):
    with TestClient(owner_app, base_url="https://studio.example.test") as client:
        assert client.get("/api/v1/policy").status_code == 401
        assert client.put("/api/v1/policy", json=UPDATED).status_code == 401
        client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
        assert client.get("/api/v1/policy").json() == ORIGINAL
        for headers in [
            {},
            {"origin": "https://evil.test", "x-csrf-token": "csrf-for-test"},
            {"origin": "https://studio.example.test", "x-csrf-token": "wrong"},
        ]:
            assert client.put("/api/v1/policy", json=UPDATED, headers=headers).status_code == 403
            assert load_policy() == ORIGINAL
        headers = {"origin": "https://studio.example.test", "x-csrf-token": "csrf-for-test"}
        assert client.put("/api/v1/policy", json=UPDATED, headers=headers).status_code == 200
        assert client.post("/api/v1/students", json={}, headers=headers).status_code == 403


def test_injected_service_path_takes_precedence(resource, tmp_path):
    alternate = tmp_path / "alternate.yaml"
    save_policy(Policy(**UPDATED), alternate)
    app = create_app(
        create_engine("sqlite://"),
        admin_token="test",
        agent_service=SimpleNamespace(policy_path=alternate),
    )
    with TestClient(app, headers={"Authorization": "Bearer test"}) as client:
        assert client.get("/api/v1/policy").json() == UPDATED
        assert client.put("/api/v1/policy", json=ORIGINAL).status_code == 200
    assert load_policy(alternate) == ORIGINAL
    assert load_policy(resource) == ORIGINAL


def test_unavailable_and_invalid_policy_have_safe_errors(resource):
    app = create_app(create_engine("sqlite://"), admin_token="test")
    with TestClient(app, headers={"Authorization": "Bearer test"}) as client:
        for contents in ["invalid: [", "secret: sensitive-content"]:
            resource.write_text(contents)
            response = client.get("/api/v1/policy")
            assert response.status_code == 503
            assert "sensitive-content" not in response.text
        resource.unlink()
        assert client.get("/api/v1/policy").status_code == 503


def test_failed_replace_keeps_original_and_cleans_temporary(resource, monkeypatch):
    before = resource.read_bytes()

    def fail_replace(*args):
        raise OSError("private filesystem detail")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with TestClient(
        create_app(create_engine("sqlite://"), admin_token="test"),
        headers={"Authorization": "Bearer test"},
    ) as client:
        response = client.put("/api/v1/policy", json=UPDATED)
        assert response.status_code == 503
        assert "private filesystem" not in response.text
    assert resource.read_bytes() == before
    assert list(resource.parent.iterdir()) == [resource]
