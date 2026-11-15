"""No PostgreSQL or paid model calls: test fixed-input live demo boundaries."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from studio_copilot.api import public_demo as api
from studio_copilot.public_demo.fixtures import CATALOG
from studio_copilot.public_demo.model import DemoModel, GeneratedDraft, Selection
from studio_copilot.public_demo.service import PublicDemo


class Fake:
    calls = []

    def call(self, scenario, stage, evidence):
        self.calls.append((scenario, stage, evidence))
        if stage == "evidence":
            return {"evidence": ["Fictional evidence"], "model": "fake"}
        return {"body": "Fresh fictional draft", "model": "fake"}

    def close(self):
        pass


@pytest.fixture
def demo(tmp_path):
    Fake.calls = []
    return PublicDemo(tmp_path / "ledger.sqlite", factory=Fake)


def create(demo, scenario="booking"):
    return demo.create(scenario, str(uuid4()))["token"]


def test_daily_admission_idempotency_and_shared_file(demo):
    request = str(uuid4())
    first = demo.create("booking", request)
    assert demo.create("booking", request) == first
    for _ in range(9):
        create(demo)
    other_worker = PublicDemo(demo.path, factory=Fake)
    with pytest.raises(HTTPException) as error:
        create(other_worker)
    assert error.value.status_code == 429
    assert not Fake.calls


def test_concurrent_admission_cannot_exceed_ten(demo):
    def admit(_):
        try:
            return create(PublicDemo(demo.path, factory=Fake))
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(admit, range(25)))
    assert sum(isinstance(result, str) for result in results) == 10
    assert results.count(429) == 15


def test_stages_are_ordered_cached_and_model_gets_only_fixed_evidence(demo):
    token = create(demo)
    with pytest.raises(HTTPException) as error:
        demo.execute(token, "draft")
    assert error.value.status_code == 409
    first = demo.execute(token, "evidence")
    assert demo.execute(token, "evidence") == first
    draft = demo.execute(token, "draft")
    assert demo.execute(token, "draft") == draft
    assert Fake.calls == [("booking", "evidence", []), ("booking", "draft", first["evidence"])]


def test_sent_failures_keep_attempt_reservation(demo):
    class Failure(Fake):
        def call(self, *_args):
            raise ValueError("private provider failure")

    demo.factory = Failure
    token = create(demo)
    for _ in range(2):
        with pytest.raises(HTTPException) as error:
            demo.execute(token, "evidence")
        assert error.value.status_code == 502
        assert "private" not in error.value.detail
    with pytest.raises(HTTPException) as error:
        demo.execute(token, "evidence")
    assert error.value.status_code == 429
    with demo.db() as db:
        assert db.execute("SELECT evidence_attempts FROM runs").fetchone()[0] == 2


def test_duplicate_inflight_cannot_start_another_call(demo):
    entered, release = Event(), Event()

    class Slow(Fake):
        def call(self, *args):
            entered.set()
            assert release.wait(5)
            return super().call(*args)

    demo.factory = Slow
    token = create(demo)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(demo.execute, token, "evidence")
        assert entered.wait(5)
        try:
            with pytest.raises(HTTPException) as error:
                demo.execute(token, "evidence")
            assert error.value.status_code == 409
        finally:
            release.set()
        assert future.result()["evidence"]
    assert len(Fake.calls) == 1


def test_expiry_and_melbourne_day_reset(tmp_path):
    # 23:59:50 Melbourne, 15 November 2026.
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = [datetime(2026, 11, 15, 23, 59, 50, tzinfo=ZoneInfo("Australia/Melbourne")).timestamp()]
    demo = PublicDemo(tmp_path / "ledger.sqlite", factory=Fake, clock=lambda: now[0])
    token = create(demo)
    now[0] += 20
    with pytest.raises(HTTPException) as error:
        demo.execute(token, "evidence")
    assert error.value.status_code == 410
    for _ in range(10):
        create(demo)
    now[0] += 3601
    with pytest.raises(HTTPException):
        demo.execute(token, "evidence")


def test_unknown_tokens_and_scenario_mismatch(demo):
    with pytest.raises(HTTPException) as error:
        demo.execute("not-a-token", "evidence")
    assert error.value.status_code == 404
    key = str(uuid4())
    demo.create("booking", key)
    with pytest.raises(HTTPException):
        demo.create("document", key)


@pytest.fixture
def client(monkeypatch, demo):
    monkeypatch.setenv("STUDIO_PUBLIC_LIVE_DEMO", "true")
    monkeypatch.setenv("STUDIO_PUBLIC_DEMO_DB", demo.path)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8010")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_MODEL", "fake-model")
    monkeypatch.setattr(api, "PublicDemo", lambda _path: demo)
    with TestClient(api.create_public_demo_app(), headers={"Origin": "http://localhost:8010"}) as c:
        yield c


def test_anonymous_api_is_separate_from_workspace_and_no_store(client):
    run = client.post(
        "/api/public-demo/runs", json={"scenario": "booking", "request_id": str(uuid4())}
    )
    assert run.status_code == 200
    assert run.headers["cache-control"] == "no-store"
    headers = {"Authorization": "Bearer " + run.json()["token"]}
    assert client.post("/api/public-demo/evidence", json={}, headers=headers).status_code == 200
    assert client.post("/api/public-demo/draft", json={}, headers=headers).json()["body"]
    assert client.get("/api/v1/students").status_code == 404


@pytest.mark.parametrize("origin", ["https://evil.invalid", ""])
def test_cross_origin_or_missing_origin_cannot_admit(client, demo, origin):
    response = client.post(
        "/api/public-demo/runs",
        json={"scenario": "booking", "request_id": str(uuid4())},
        headers={"Origin": origin},
    )
    assert response.status_code == 403
    with demo.db() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


def test_disabled_unconfigured_and_oversized_requests(client, monkeypatch, demo):
    body = {"scenario": "booking", "request_id": str(uuid4())}
    monkeypatch.setenv("STUDIO_PUBLIC_LIVE_DEMO", "false")
    assert client.post("/api/public-demo/runs", json=body).status_code == 503
    monkeypatch.setenv("STUDIO_PUBLIC_LIVE_DEMO", "true")
    monkeypatch.delenv("OPENAI_API_KEY")
    assert client.post("/api/public-demo/runs", json=body).status_code == 503
    assert client.post("/api/public-demo/runs", content=b"x" * 1025).status_code == 413
    assert not Fake.calls


def test_arbitrary_inputs_and_missing_tokens_are_rejected(client):
    assert (
        client.post(
            "/api/public-demo/runs", json={"scenario": "other", "request_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/public-demo/runs",
            json={"scenario": "booking", "request_id": str(uuid4()), "prompt": "untrusted"},
        ).status_code
        == 422
    )
    assert client.post("/api/public-demo/evidence", json={}).status_code == 401
    assert client.post("/api/public-demo/draft", json={"body": "untrusted"}).status_code == 422


def model_with(response):
    calls = []

    def parse(**kwargs):
        calls.append(kwargs)
        return response

    return DemoModel(
        client=SimpleNamespace(responses=SimpleNamespace(parse=parse)), model="fake"
    ), calls


def test_model_uses_fixed_catalog_and_checked_source_ids():
    response = SimpleNamespace(
        status="completed", output_parsed=Selection(ids=["clothing", "missing_fee"])
    )
    model, calls = model_with(response)
    result = model.call("document", "evidence", [])
    assert result["evidence"] == [
        CATALOG["document"]["clothing"],
        CATALOG["document"]["missing_fee"],
    ]
    assert calls[0]["store"] is False and calls[0]["max_output_tokens"] == 2000
    assert json.loads(calls[0]["input"])["facts"] == CATALOG["document"]
    response.output_parsed = Selection(ids=["made-up-source"])
    with pytest.raises(ValueError):
        model.call("document", "evidence", [])


@pytest.mark.parametrize("status,parsed", [("incomplete", None), ("completed", None)])
def test_model_handles_incomplete_and_refusal(status, parsed):
    model, _ = model_with(SimpleNamespace(status=status, output_parsed=parsed))
    with pytest.raises(ValueError):
        model.call("booking", "draft", ["fixed"])


def test_document_draft_always_requires_teacher_fee_decision():
    model, _ = model_with(
        SimpleNamespace(
            status="completed", output_parsed=GeneratedDraft(body="Socks are suitable.")
        )
    )
    result = model.call("document", "draft", [CATALOG["document"]["clothing"]])
    assert "Socks are suitable." in result["body"]
    assert result["body"].count("[Teacher decision needed: trial fee]") == 1


def test_public_router_is_integrated_without_unlocking_staff_api(client):
    from sqlalchemy import create_engine

    from studio_copilot.api.app import create_app

    with TestClient(
        create_app(engine=create_engine("sqlite://"), admin_token="test-token"),
        headers={"Origin": "http://localhost:8010"},
    ) as application:
        response = application.post(
            "/api/public-demo/runs", json={"scenario": "booking", "request_id": str(uuid4())}
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert application.get("/api/v1/students").status_code == 401
