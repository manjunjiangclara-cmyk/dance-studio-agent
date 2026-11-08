"""Production controls use fake providers, clocks and local ASGI clients only."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import Mock

import pytest

from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.operations import (
    Budget,
    EventSink,
    Limits,
    OperationsError,
    QueryEmbeddingCache,
)
from tests.unit.test_documents import client as client
from tests.unit.test_documents import payload
from tests.unit.test_website_auth import session_cookie


@pytest.fixture(autouse=True)
def no_external_telemetry(monkeypatch):
    monkeypatch.setenv("STUDIO_LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


def unit_vector(index=0):
    return [float(position == index) for position in range(1536)]


@pytest.mark.parametrize(
    "field", ["max_api_requests", "max_estimated_input_tokens", "max_output_tokens_total"]
)
@pytest.mark.parametrize("value", [-1, True, 1.5, "1"])
def test_limits_reject_ambiguous_or_negative_values(field, value):
    with pytest.raises((OperationsError, ValueError)):
        Limits(**{field: value})


def test_budget_concurrent_reservations_cannot_overspend_and_unknown_usage_stays_charged():
    budget = Budget(
        Limits(max_api_requests=7, max_estimated_input_tokens=70, max_output_tokens_total=14)
    )
    barrier = threading.Barrier(20)

    def reserve(_):
        barrier.wait(timeout=5)
        try:
            budget.reserve(10, 2)
            return True
        except OperationsError as error:
            assert error.code == "budget_exceeded"
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        assert sum(pool.map(reserve, range(20))) == 7
    snapshot = budget.snapshot()
    assert snapshot["attempts"] == 7
    assert snapshot["reserved_input_tokens"] == 70
    assert snapshot["reserved_output_tokens"] == 14
    assert snapshot["unknown_usage_calls"] == 7


def test_budget_actual_usage_does_not_refund_reservations_and_finish_is_single_use():
    budget = Budget(
        Limits(max_api_requests=2, max_estimated_input_tokens=20, max_output_tokens_total=8)
    )
    first = budget.reserve(10, 4)
    first.finish(input_tokens=3, output_tokens=1)
    second = budget.reserve(10, 4)
    second.finish()
    snapshot = budget.snapshot()
    assert snapshot["input_tokens"] == 3 and snapshot["output_tokens"] == 1
    assert snapshot["unknown_usage_calls"] == 1
    with pytest.raises(OperationsError):
        budget.reserve(1)
    first.finish(input_tokens=100, output_tokens=100)
    assert budget.snapshot()["input_tokens"] == 3


def test_plan_exceeding_limits_fails_without_spending_and_zero_call_plan_is_valid():
    budget = Budget(
        Limits(max_api_requests=0, max_estimated_input_tokens=0, max_output_tokens_total=0)
    )
    budget.check_plan(0, 0, 0)
    with pytest.raises(OperationsError) as caught:
        budget.check_plan(1, 1, 0)
    assert caught.value.code == "budget_exceeded"
    assert budget.snapshot()["attempts"] == 0


def test_cache_exact_unicode_profile_scope_isolation_and_defensive_vectors():
    cache = QueryEmbeddingCache()
    profile = EmbeddingProfile()
    compute = Mock(return_value=unit_vector())
    first, hit = cache.get_or_compute("run-a", profile, "Café\r\n", compute)
    assert not hit
    first[0] = 0.0
    second, hit = cache.get_or_compute("run-a", profile, "Café\r\n", compute)
    assert hit and second == unit_vector()
    for scope, changed_profile, text in [
        ("run-b", profile, "Café\r\n"),
        ("run-a", replace(profile, endpoint="https://other.example/v1"), "Café\r\n"),
        ("run-a", profile, "Café\r\n"),
        ("run-a", profile, "Café\n"),
    ]:
        assert not cache.get_or_compute(scope, changed_profile, text, compute)[1]
    assert compute.call_count == 5


def test_cache_ttl_and_lru_are_bounded_with_fake_clock():
    now = [0.0]
    cache = QueryEmbeddingCache(max_entries=2, ttl=300, clock=lambda: now[0])
    profile = EmbeddingProfile()
    compute = Mock(return_value=unit_vector())
    for query in ["a", "b", "a", "c"]:
        cache.get_or_compute("run", profile, query, compute)
    assert compute.call_count == 3
    assert cache.get_or_compute("run", profile, "a", compute)[1]
    assert not cache.get_or_compute("run", profile, "b", compute)[1]
    now[0] = 299.99
    assert cache.get_or_compute("run", profile, "b", compute)[1]
    now[0] = 300.0
    assert not cache.get_or_compute("run", profile, "b", compute)[1]


def test_cache_concurrent_same_query_computes_once():
    cache = QueryEmbeddingCache()
    started = threading.Event()
    release = threading.Event()
    count = [0]
    lock = threading.Lock()

    def compute():
        with lock:
            count[0] += 1
        started.set()
        assert release.wait(timeout=5)
        return unit_vector()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(cache.get_or_compute, "run", EmbeddingProfile(), "same", compute)
            for _ in range(8)
        ]
        assert started.wait(timeout=5)
        release.set()
        results = [future.result(timeout=5) for future in futures]
    assert count == [1]
    assert sum(hit for _, hit in results) == 7
    assert all(value == unit_vector() for value, _ in results)


def test_failed_or_invalid_vectors_are_not_cached():
    cache = QueryEmbeddingCache()
    profile = EmbeddingProfile()
    compute = Mock(side_effect=[RuntimeError("private source"), [0.0] * 1536, unit_vector()])
    with pytest.raises(RuntimeError):
        cache.get_or_compute("run", profile, "same", compute)
    with pytest.raises(Exception):
        cache.get_or_compute("run", profile, "same", compute)
    assert not cache.get_or_compute("run", profile, "same", compute)[1]
    assert cache.get_or_compute("run", profile, "same", compute)[1]
    assert compute.call_count == 3


def test_telemetry_never_exports_unknown_fields_or_raw_exceptions(tmp_path, caplog):
    path = tmp_path / "events.jsonl"
    exported = []
    sink = EventSink(events_file=path, exporter=exported.append)
    secret = "PRIVATE-STUDENT-AND-POLICY-SENTINEL"
    sink.emit(
        "00000000-0000-0000-0000-000000000001",
        "retrieval",
        "api",
        query=secret,
        filename=secret,
        prompt=secret,
        answer=secret,
        vector=[secret],
        exception=RuntimeError(secret),
        error_code=secret,
        seconds=0.012,
        items=1,
    )
    text = path.read_text()
    assert secret not in text and secret not in json.dumps(exported)
    assert secret not in caplog.text
    assert len(exported) == 1


def test_telemetry_export_failure_is_isolated(tmp_path):
    def broken(_event):
        raise RuntimeError("private exporter failure")

    sink = EventSink(events_file=tmp_path / "events.jsonl", exporter=broken)
    sink.emit("00000000-0000-0000-0000-000000000001", "generation", "api", seconds=0.001)


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
def test_document_read_acl_matrix(client, headers):
    created = client.post(
        "/api/v1/documents", headers={"Authorization": "Bearer test"}, json=payload()
    ).json()
    path = "/api/v1/documents/" + created["id"]
    for suffix in ["", "/metadata", "/revisions", "/revisions/1/preview"]:
        assert client.get(path + suffix, headers=headers).status_code == 401
    assert client.get("/api/v1/documents", headers=headers).status_code == 401


def test_owner_can_read_all_revision_surfaces_without_write_permission(client):
    created = client.post(
        "/api/v1/documents", headers={"Authorization": "Bearer test"}, json=payload()
    ).json()
    client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
    path = "/api/v1/documents/" + created["id"]
    for suffix in ["", "/metadata", "/revisions", "/revisions/1/preview"]:
        assert client.get(path + suffix).status_code == 200
    assert client.delete(path).status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/documents/upload"),
        ("PUT", "/api/v1/documents/00000000-0000-0000-0000-000000000001/upload"),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"authorization": "Bearer wrong"}])
def test_upload_auth_rejection_does_not_read_body(client, method, path, headers):
    messages = []

    async def receive():
        pytest.fail("Unauthorized upload body was read")

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("studio.example.test", 443),
        "client": ("127.0.0.1", 1234),
        "headers": [(key.encode(), value.encode()) for key, value in headers.items()],
    }
    asyncio.run(client.app(scope, receive, send))
    assert (
        next(message["status"] for message in messages if message["type"] == "http.response.start")
        == 401
    )


def test_upload_rate_limit_checks_before_receiving_and_recovers_after_window(client):
    from studio_copilot.documents.operations.admission import UploadLimiter

    now = [0.0]
    client.app.state.document_upload_limiter = UploadLimiter(
        limit=1, window=60, clock=lambda: now[0]
    )
    first = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": "Bearer test"},
        files={"file": ("test.md", b"Good text")},
        data={"title": "Test"},
    )
    assert first.status_code == 201
    messages = []

    async def receive():
        pytest.fail("Rate-limited upload body was read")

    async def send(message):
        messages.append(message)

    path = "/api/v1/documents/" + first.json()["id"] + "/upload"
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "PUT",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("studio.example.test", 443),
        "client": ("127.0.0.1", 1234),
        "headers": [(b"authorization", b"Bearer test")],
    }
    asyncio.run(client.app(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    assert start["status"] == 429
    assert b"retry-after" in dict(start["headers"])
    now[0] = 60.0
    assert (
        client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": "Bearer test"},
            files={"file": ("next.md", b"Next text")},
            data={"title": "Next"},
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "limits,reservation",
    [
        (Limits(max_estimated_input_tokens=9), (10, 0)),
        (Limits(max_output_tokens_total=3), (1, 4)),
    ],
)
def test_each_budget_dimension_denies_before_attempt(limits, reservation):
    budget = Budget(limits)
    with pytest.raises(OperationsError) as caught:
        budget.reserve(*reservation)
    assert caught.value.code == "budget_exceeded"
    assert budget.snapshot()["attempts"] == 0


def test_unknown_usage_cannot_be_reclassified_by_late_duplicate_finish():
    budget = Budget()
    ticket = budget.reserve(100)
    ticket.finish()
    ticket.finish(input_tokens=10, output_tokens=0)
    assert budget.snapshot()["unknown_usage_calls"] == 1
    assert budget.snapshot()["input_tokens"] == 0


def test_cache_entries_never_retain_plaintext_queries():
    cache = QueryEmbeddingCache()
    private_query = "PRIVATE-QUERY-SENTINEL-Café"
    cache.get_or_compute("run", EmbeddingProfile(), private_query, unit_vector)
    assert private_query not in repr(cache.entries)
    assert private_query not in repr(cache.pending)


def test_concurrent_cache_failure_reaches_waiters_without_poisoning_retry(monkeypatch):
    from concurrent.futures import Future

    from studio_copilot.documents.operations import cache as cache_module

    waiter_started = threading.Event()
    compute_started = threading.Event()
    release = threading.Event()

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiter_started.set()
            return super().result(timeout)

    monkeypatch.setattr(cache_module, "Future", ObservedFuture)
    cache = QueryEmbeddingCache()
    compute = Mock()

    def fail():
        compute()
        compute_started.set()
        assert release.wait(timeout=5)
        raise RuntimeError("private provider failure")

    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(cache.get_or_compute, "run", EmbeddingProfile(), "same", fail)
        assert compute_started.wait(timeout=5)
        waiter = pool.submit(cache.get_or_compute, "run", EmbeddingProfile(), "same", fail)
        assert waiter_started.wait(timeout=5)
        release.set()
        for future in [owner, waiter]:
            with pytest.raises(RuntimeError, match="private provider failure"):
                future.result(timeout=5)
    assert compute.call_count == 1
    assert not cache.get_or_compute("run", EmbeddingProfile(), "same", unit_vector)[1]


@pytest.mark.parametrize(
    "operation,stage,status",
    [
        ("PRIVATE-POLICY", "api", "success"),
        ("generation", "PRIVATE-POLICY", "success"),
        ("generation", "api", "PRIVATE-POLICY"),
    ],
)
def test_telemetry_rejects_uncontrolled_event_names(tmp_path, operation, stage, status):
    exported = []
    sink = EventSink(events_file=tmp_path / "events.jsonl", exporter=exported.append)
    sink.emit("00000000-0000-0000-0000-000000000001", operation, stage, status)
    assert exported == []


def test_telemetry_rejects_invalid_counters_and_duration(tmp_path):
    exported = []
    sink = EventSink(events_file=tmp_path / "events.jsonl", exporter=exported.append)
    sink.emit(
        "00000000-0000-0000-0000-000000000001",
        "generation",
        "api",
        attempts=True,
        input_tokens=-1,
        output_tokens="100",
        seconds=float("nan"),
        unknown_usage_calls=1,
    )
    assert len(exported) == 1
    assert "attempts" not in exported[0]
    assert "input_tokens" not in exported[0]
    assert "output_tokens" not in exported[0]
    assert "seconds" not in exported[0]
    assert exported[0]["unknown_usage_calls"] == 1


def test_embedding_retries_each_reserve_budget_and_stop_before_extra_request(monkeypatch):
    from studio_copilot.documents.embedding import provider as embedding_provider
    from studio_copilot.documents.operations.runtime import Task, task
    from tests.unit.test_embedding_provider import embedder, status_error

    monkeypatch.setattr(embedding_provider, "estimate", lambda text: 7)
    subject, create = embedder(status_error(503), status_error(503), status_error(503))
    control = Task(limits=Limits(max_api_requests=2))
    with task(control=control), pytest.raises(OperationsError) as caught:
        subject.embed(["private input"])
    assert caught.value.code == "budget_exceeded"
    assert create.call_count == 2
    usage = control.budget.snapshot()
    assert usage["attempts"] == 2
    assert usage["reserved_input_tokens"] == 14
    assert usage["unknown_usage_calls"] == 2


def test_embedding_retry_success_keeps_failed_attempt_usage_unknown(monkeypatch):
    from studio_copilot.documents.embedding import provider as embedding_provider
    from studio_copilot.documents.operations.runtime import Task, task
    from tests.unit.test_embedding_provider import embedder, response, status_error

    monkeypatch.setattr(embedding_provider, "estimate", lambda text: 7)
    subject, create = embedder(status_error(503), response(unit_vector(), usage=5))
    control = Task()
    with task(control=control):
        assert subject.embed(["private input"])[1] == 5
    assert create.call_count == 2
    usage = control.budget.snapshot()
    assert usage["attempts"] == 2
    assert usage["reserved_input_tokens"] == 14
    assert usage["input_tokens"] == 5
    assert usage["unknown_usage_calls"] == 1


def test_operation_summary_is_aggregate_only_and_refuses_overwrite(tmp_path):
    from studio_copilot.documents.operations.report import summarize

    events = tmp_path / "events.jsonl"
    sink = EventSink(events_file=events, exporter=lambda event: None)
    operation_id = "00000000-0000-0000-0000-000000000001"
    sink.emit(operation_id, "retrieval", "cache", cache_hits=1, seconds=1)
    sink.emit(operation_id, "retrieval", "cache", cache_misses=1, seconds=3)
    sink.emit(operation_id, "retrieval", "cache", "failure", unknown_usage_calls=1, seconds=2)
    sink.close()
    output = tmp_path / "summary"
    result = summarize(events, output)
    group = result["groups"]["retrieval/cache"]
    assert group["events"] == 3 and group["failures"] == 1
    assert group["failure_rate"] == pytest.approx(1 / 3)
    assert group["cache_hit_rate"] == 0.5
    assert group["p50_seconds"] == 2 and group["p95_seconds"] == 3
    assert group["duration_samples"] == 3 and group["small_sample"]
    assert operation_id not in (output / "summary.json").read_text()
    with pytest.raises(OperationsError) as caught:
        summarize(events, output)
    assert caught.value.code == "output_exists"


def test_generation_transport_failure_is_one_charged_unknown_attempt(monkeypatch):
    from studio_copilot.documents.generation import provider as generation_provider
    from studio_copilot.documents.generation.contracts import GenerationError
    from studio_copilot.documents.operations.runtime import Task, task
    from tests.unit.test_generation_provider import client

    monkeypatch.setattr(generation_provider, "generation_estimate", lambda *args: 11)
    sdk = client(failure=RuntimeError("PRIVATE-FAILURE-SENTINEL"))
    provider = generation_provider.GenerationProvider(client=sdk, model="fixture-model")
    control = Task()
    with task(control=control), pytest.raises(GenerationError) as caught:
        provider.generate({"question": "PRIVATE-QUESTION-SENTINEL", "evidence": []})
    assert caught.value.code == "provider_error"
    assert len(sdk.responses.calls) == 1
    snapshot = control.budget.snapshot()
    assert snapshot["attempts"] == 1 and snapshot["unknown_usage_calls"] == 1
    assert snapshot["reserved_input_tokens"] > 0
    assert snapshot["reserved_output_tokens"] == 4000


def test_generation_budget_exhaustion_sends_no_request_and_does_not_become_abstention(monkeypatch):
    from studio_copilot.documents.generation import provider as generation_provider
    from studio_copilot.documents.operations.runtime import Task, task
    from tests.unit.test_generation_provider import client

    monkeypatch.setattr(generation_provider, "generation_estimate", lambda *args: 11)
    sdk = client()
    provider = generation_provider.GenerationProvider(client=sdk, model="fixture-model")
    control = Task(limits=Limits(max_api_requests=0))
    with task(control=control), pytest.raises(OperationsError) as caught:
        provider.generate({"question": "PRIVATE-QUESTION-SENTINEL", "evidence": []})
    assert caught.value.code == "budget_exceeded"
    assert sdk.responses.calls == []


def test_generation_batch_budget_failure_preserves_success_and_uses_shared_worker_budget(
    tmp_path, monkeypatch
):
    from studio_copilot.documents.generation import evaluation
    from studio_copilot.documents.generation import provider as generation_provider
    from studio_copilot.documents.generation.contracts import Candidate
    from studio_copilot.documents.operations.runtime import Task, task
    from tests.unit.test_generation_engine import candidate
    from tests.unit.test_generation_evidence import Characters, artifact
    from tests.unit.test_generation_provider import client
    from tests.unit.test_generation_workflow import evidence_set

    evidence = evidence_set(tmp_path, monkeypatch)
    gold_sentinel = "PRIVATE-GOLD-ANSWER-AND-LABEL-SENTINEL"
    labels = evaluation.load_cases()
    labels["cases"][0]["reference_answer"] = gold_sentinel
    labels["cases"][0]["required_facts"].append(dict(patterns=[[gold_sentinel]]))

    def estimate(instructions, payload, schema):
        return 100 if schema is Candidate else 200

    monkeypatch.setattr(evaluation, "generation_estimate", estimate)
    monkeypatch.setattr(generation_provider, "generation_estimate", estimate)
    clients = []

    def factory():
        sdk = client()
        sdk.responses.response.output_parsed = candidate(artifact())
        clients.append(sdk)
        return generation_provider.GenerationProvider(client=sdk, model="fixture-model")

    control = Task(limits=Limits(max_estimated_input_tokens=200))
    output = tmp_path / "result"
    with task(control=control):
        manifest = evaluation.evaluate_directory(
            evidence,
            output,
            Characters(),
            allow_api=True,
            compare_verification=True,
            provider_factory=factory,
            workers=1,
        )
    assert manifest["complete"] is False
    assert manifest["requests"] == 1
    assert sum(len(sdk.responses.calls) for sdk in clients) == 1
    assert gold_sentinel not in repr([sdk.responses.calls for sdk in clients])
    records = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
    assert len(records) == 4
    assert sum(row["result"]["execution_status"] == "completed" for row in records) == 1
    failed = [row for row in records if row["result"]["execution_status"] == "failed"]
    assert all(row["result"]["error_code"] == "budget_exceeded" for row in failed)
    assert all(row["result"]["status"] is None for row in failed)
    assert (output / "reports.jsonl").exists()
    assert control.budget.snapshot()["attempts"] == 1


def test_langsmith_constructor_failure_never_leaks_content_or_breaks_operation(monkeypatch, caplog):
    import langsmith.run_trees

    secret = "PRIVATE-TRACE-TRANSPORT-SENTINEL"
    captured = []

    def broken_run(**kwargs):
        captured.append(kwargs)
        raise RuntimeError(secret)

    monkeypatch.setenv("STUDIO_LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "fake-never-sent")
    monkeypatch.setattr(langsmith.run_trees, "RunTree", broken_run)
    sink = EventSink()
    sink.emit(
        "00000000-0000-0000-0000-000000000001",
        "generation",
        "api",
        query=secret,
        prompt=secret,
        error_code="provider_error",
    )
    assert len(captured) == 1
    assert captured[0]["inputs"] == {}
    assert secret not in json.dumps(captured)
    assert secret not in caplog.text


@pytest.mark.parametrize(
    "logger_name",
    ["langsmith.client", "langsmith.run_helpers", "langsmith._internal._background_thread"],
)
def test_async_trace_sdk_logs_redact_arguments_exception_stack_and_extra(logger_name, caplog):
    import logging

    private = "PRIVATE-SDK-RESPONSE-AND-EXCEPTION-SENTINEL"
    logger = logging.getLogger(logger_name)
    caplog.set_level(logging.WARNING, logger=logger_name)
    try:
        raise RuntimeError(private)
    except RuntimeError:
        logger.warning(
            "Response body %s",
            private,
            exc_info=True,
            stack_info=True,
            extra={"provider_response": private},
        )
    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.WARNING
    assert record.getMessage() == "trace_sdk_event"
    assert record.exc_info is None and record.exc_text is None and record.stack_info is None
    assert private not in caplog.text
    assert private not in repr(record.__dict__)
