import pytest
from sqlalchemy.orm import Session

from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.agent.service import AgentService

from .helpers import FakeModel, review, start

pytestmark = pytest.mark.integration


def test_failed_approval_memory_can_retry_without_duplicate_response(rig, scenario):
    client, model, _, _ = rig
    run = start(rig, scenario)
    model.fail_reconcile = True
    failed = review(client, run, "approve", body="Saturday options need review.").json()
    assert failed["status"] == "failed", failed
    assert failed["approved_response_id"]
    model.fail_reconcile = False
    retried = client.post(f"/api/v1/agent-runs/{run['id']}/retry").json()
    assert retried["status"] == "approved", retried
    assert retried["approved_response_id"] == failed["approved_response_id"]


def test_failed_interpretation_can_retry(rig, scenario):
    client, model, _, _ = rig
    model.fail_interpret = True
    result = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/agent-runs",
        json={"source_message_id": str(scenario["source"])},
    ).json()
    assert result["status"] == "failed", result
    model.fail_interpret = False
    assert (
        client.post(f"/api/v1/agent-runs/{result['id']}/retry").json()["status"]
        == "awaiting_review"
    )


def test_postgres_checkpoint_survives_service_recreation(db_engine, scenario):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    service = AgentService(db_engine, FakeModel())
    run = service.start(scenario["conversation"], scenario["source"])
    assert run.status == "awaiting_review", run.error
    # New model, graph, service and connection: only persisted state links the review.
    fresh = AgentService(db_engine, FakeModel())
    from studio_copilot.agent.contracts import Review

    approved = fresh.review(
        run.id, Review(action="approve", expected_revision=1, body="Teacher reviewed.")
    )
    assert approved.status == "approved", approved.error
    from alembic import command

    from tests.support import migration_config

    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.check(config)


def test_postgres_rejection_removes_all_run_checkpoints(db_engine, scenario):
    from studio_copilot.agent.contracts import Review

    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    service = AgentService(db_engine, FakeModel())
    run = service.start(scenario["conversation"], scenario["source"])
    assert run.status == "awaiting_review"
    closed = service.review(run.id, Review(action="reject", expected_revision=1))
    assert closed.status == "closed"
    with postgres_checkpointer(db_engine) as saver:
        assert saver.get_tuple({"configurable": {"thread_id": str(run.id)}}) is None
    with Session(db_engine) as db:
        from sqlalchemy import text

        for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            count = db.scalar(
                text(f"SELECT count(*) FROM {table} WHERE thread_id = :thread"),
                {"thread": str(run.id)},
            )
            assert count == 0


def test_missing_checkpoint_setup_is_recoverable(db_engine, scenario):
    service = AgentService(db_engine, FakeModel())
    run = service.start(scenario["conversation"], scenario["source"])
    assert run.status == "failed"
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    recovered = service.retry(run.id)
    assert recovered.status == "awaiting_review", recovered.error


def test_database_tool_failure_produces_a_draft_instead_of_looping(rig, scenario, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    def unavailable(*args, **kwargs):
        raise SQLAlchemyError("synthetic database failure")

    monkeypatch.setattr("studio_copilot.agent.workflow.queries.execute_tool", unavailable)
    run = start(rig, scenario)
    assert rig[1].query_count == 1
    assert run["draft_details"]["warnings"]
    assert "synthetic database failure" not in str(run)
