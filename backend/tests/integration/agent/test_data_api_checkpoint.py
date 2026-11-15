"""Actual application workflow, local business DB, PostgreSQL-backed Data API double."""

from contextlib import nullcontext
from uuid import uuid4

import pytest
from langgraph.checkpoint.base import empty_checkpoint
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from experiments.data_api.checkpoints import DataAPISaver
from experiments.data_api.leases import Leases, StaleOwner
from experiments.data_api.sql import DataSQL
from studio_copilot.agent.contracts import Review
from studio_copilot.agent.service import AgentService
from studio_copilot.persistence.models import Message
from tests.data_api_support import LocalDataClient

from .helpers import FakeModel

pytestmark = pytest.mark.integration


@pytest.fixture
def data_api(db_engine):
    import psycopg

    url = db_engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    client = LocalDataClient(lambda: psycopg.connect(url))
    sql = DataSQL(client, "local-protocol-double", "no-aws-secret")
    schema = "data_api_" + uuid4().hex
    sql.query(f"CREATE SCHEMA {schema}")
    try:
        yield sql, schema, client
    finally:
        assert not client.connections
        sql.query(f"DROP SCHEMA {schema} CASCADE")


def saver_for(data_api, **kwargs):
    sql, schema, _ = data_api
    saver = DataAPISaver(sql, schema, **kwargs)
    saver.setup()
    return saver


def test_actual_workflow_resumes_with_new_data_api_saver(db_engine, scenario, data_api):
    def service():
        return AgentService(
            db_engine, FakeModel(), checkpoints=lambda: nullcontext(saver_for(data_api))
        )

    run = service().start(scenario["conversation"], scenario["source"])
    assert run.status == "awaiting_review", run.error
    revised = service().review(
        run.id,
        Review(action="revise", expected_revision=run.revision, feedback="Please use Saturday."),
    )
    assert revised.status == "awaiting_review" and revised.revision == 2, revised.error
    approved = service().review(
        run.id,
        Review(action="approve", expected_revision=revised.revision, body="Teacher reviewed."),
    )
    assert approved.status == "approved", approved.error


def test_committed_approval_recovery_does_not_duplicate_response(db_engine, scenario, data_api):
    model = FakeModel()
    model.fail_reconcile = True
    service = AgentService(db_engine, model, checkpoints=lambda: nullcontext(saver_for(data_api)))
    run = service.start(scenario["conversation"], scenario["source"])
    failed = service.review(run.id, Review(action="approve", expected_revision=1, body="Approved."))
    assert failed.status == "failed" and failed.approved_response_id
    fresh = AgentService(
        db_engine, FakeModel(), checkpoints=lambda: nullcontext(saver_for(data_api))
    )
    recovered = fresh.retry(run.id)
    assert recovered.status == "approved"
    assert recovered.approved_response_id == failed.approved_response_id
    with Session(db_engine) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
            )
            == 1
        )


def test_chunked_typed_checkpoint_replay_and_pending_writes(data_api):
    saver = saver_for(data_api)
    checkpoint = empty_checkpoint()
    checkpoint["channel_values"] = {"unicode": "芭蕾💃" * 100_000, "bytes": b"\xff\x00" * 40_000}
    config = {"configurable": {"thread_id": "large", "checkpoint_ns": "review"}}
    saved = saver.put(config, checkpoint, {"step": 0}, {})
    data_api[2].lose_commit = True
    with pytest.raises(TimeoutError):
        saver.put_writes(saved, [("draft", "first")], "task")
    saver.put_writes(saved, [("draft", "second")], "task")
    saver.put(config, checkpoint, {"step": 0}, {})
    result = saver_for(data_api).get_tuple(saved)
    assert result.checkpoint == checkpoint
    assert result.pending_writes == [("task", "draft", "first")]
    assert list(saver.list(config, limit=1))[0].checkpoint == checkpoint
    assert data_api[2].max_row_bytes < 64 * 1024
    assert data_api[0].max_result_bytes < 1024 * 1024
    saver.delete_thread("large")
    assert saver.get_tuple(config) is None


def test_partial_checkpoint_rolls_back_and_stale_owner_cannot_publish(data_api):
    saver = saver_for(data_api)
    checkpoint = empty_checkpoint()
    config = {"configurable": {"thread_id": "failure"}}
    data_api[2].fail_part = True
    with pytest.raises(RuntimeError):
        saver.put(config, checkpoint, {}, {})
    assert saver.get_tuple(config) is None
    leases = Leases(data_api[0], data_api[1])
    leases.setup()
    claim = leases.acquire("student", "worker-a")
    leases.release(claim)
    newer = leases.acquire("student", "worker-b")
    assert newer.token > claim.token
    stale = saver_for(data_api, leases=leases, claim=claim)
    with pytest.raises(StaleOwner):
        stale.put(config, checkpoint, {}, {})
    assert saver.get_tuple(config) is None


def test_pending_write_order_parent_history_and_thread_isolation(data_api):
    saver = saver_for(data_api)
    config = {"configurable": {"thread_id": "history"}}
    first = empty_checkpoint()
    parent = saver.put(config, first, {"step": 1}, {})
    second = empty_checkpoint()
    saved = saver.put(parent, second, {"step": 2}, {})
    saver.put_writes(saved, [("value", 10 + i) for i in range(12)], "z-task", task_path="first")
    saver.put_writes(saved, [("value", "last")], "a-task", task_path="second")
    restored = saver.get_tuple(saved)
    assert restored.parent_config == parent
    assert [v for _, _, v in restored.pending_writes] == [*range(10, 22), "last"]
    assert [item.checkpoint["id"] for item in saver.list(config)] == [second["id"], first["id"]]
    assert saver.get_tuple(parent).checkpoint == first
    assert saver.get_tuple({"configurable": {"thread_id": "different"}}) is None
    assert list(saver.list(config, before=saved))[0].checkpoint == first
