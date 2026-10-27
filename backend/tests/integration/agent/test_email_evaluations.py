"""Evaluation setup and orchestration exercise the actual intake API without a provider."""

import os
from contextlib import nullcontext
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from evaluations.cases import POLICY, Scenario, Setup
from evaluations.fixtures import isolated_database, seed_studio
from evaluations.runner import run_scenario
from studio_copilot.agent.policy import load_policy
from studio_copilot.agent.service import AgentService
from studio_copilot.persistence.models import Enrolment, Message, Student

from .helpers import FakeModel

pytestmark = pytest.mark.integration


def setup(registered=True, status=None):
    return Setup.model_validate(
        {
            "student": {
                "registered": registered,
                "highest_level": "Level 2" if registered else None,
            },
            "enrolments": (
                [{"class_key": "monday_level_2", "status": status, "starts_on": "{term_start}"}]
                if status
                else []
            ),
            "sessions": ["absence", "thursday", "saturday"],
        }
    )


@pytest.mark.parametrize("status", ["active", "cancelled", None])
def test_setup_persists_only_explicit_current_enrolments(db_engine, status):
    fixture = seed_studio(db_engine, setup(status=status))
    with Session(db_engine) as db:
        student = db.get(Student, UUID(fixture["student_id"]))
        assert student.email == fixture["sender"]
        enrolments = list(db.scalars(select(Enrolment).where(Enrolment.student_id == student.id)))
        assert [e.status for e in enrolments] == ([status] if status else [])
        if enrolments:
            assert enrolments[0].starts_on.isoformat() == fixture["dates"]["term_start"]
            assert (
                enrolments[0].regular_class.name
                == fixture["catalog"]["classes"]["monday_level_2"]["name"]
            )


def test_new_sender_is_absent_until_intake(db_engine):
    fixture = seed_studio(db_engine, setup(registered=False))
    assert fixture["student_id"] is None
    with Session(db_engine) as db:
        assert db.scalar(select(Student).where(Student.email == fixture["sender"])) is None


def test_disposable_evaluation_schema_is_removed_after_failure(db_engine):
    schema = None
    with pytest.raises(RuntimeError, match="Controlled failure"):
        with isolated_database(os.environ["TEST_DATABASE_URL"]) as engine:
            with engine.connect() as connection:
                schema = connection.scalar(text("SELECT current_schema()"))
            seed_studio(engine, setup(status="active"))
            with Session(db_engine) as db:
                assert db.scalar(select(Student)) is None
            raise RuntimeError("Controlled failure")
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_namespace WHERE nspname=:schema"), {"schema": schema}
            )
            == 0
        )


class DateModel(FakeModel):
    def interpret_makeup(self, context):
        result = super().interpret_makeup(context)
        # These emails contain explicit ISO dates, preserving real intake timestamps.
        result.absence_date = context["source"]["body"].split("absence=")[1].split()[0]
        result.preferred_date = context["source"]["body"].split("preferred=")[1].split()[0]
        return result


def test_runner_stops_at_review_and_followup_supersedes_without_teacher_writes(
    db_engine, monkeypatch, tmp_path
):
    mutable_policy = tmp_path / "studio.yaml"
    mutable_policy.write_text(
        'version: local\nabsence_notice_before_start: false\nexplanation: "Refunds are 50%."\n'
    )
    monkeypatch.setenv("STUDIO_POLICY_PATH", str(mutable_policy))
    saver = InMemorySaver()
    monkeypatch.setattr(
        "evaluations.runner.AgentService",
        lambda engine, model, **kwargs: AgentService(
            engine, model, checkpoints=lambda: nullcontext(saver), **kwargs
        ),
    )
    expected = {
        "status": "awaiting_review",
        "interpretation": {"flow": "makeup", "routing": {"intents": ["absence", "makeup"]}},
    }
    scenario = Scenario.model_validate(
        {
            "id": "followup_test",
            "description": "Consecutive emails",
            "setup": setup(status="active").model_dump(),
            "rubric": ["Teacher reviews both drafts"],
            "steps": [
                {"input": {"body": body}, "expected": expected}
                for body in [
                    "absence={absence_date} preferred={thursday_date} Thursday please",
                    "absence={absence_date} preferred={saturday_date} Saturday please",
                ]
            ],
        }
    )
    model = DateModel()
    result = run_scenario(db_engine, scenario, model)
    assert result["passed"], result
    assert len(result["runs"]) == 2
    assert all(run["status"] == "awaiting_review" for run in result["runs"])
    assert all(run["policy_snapshot"] == load_policy(POLICY) for run in result["runs"])
    assert result["runs"][0]["conversation_id"] == result["runs"][1]["conversation_id"]
    assert any(c["name"] == "earlier_run_superseded" and c["passed"] for c in result["checks"])
    assert (
        len([m for m in model.routing_contexts[-1]["history"] if m["kind"] == "student_email"]) == 2
    )
    assert model.contexts[0]["enrolments"]
    assert result["database_after"]["responses"] == {}
    with Session(db_engine) as db:
        assert list(db.scalars(select(Message).where(Message.kind == "teacher_response"))) == []


def test_approve_twice_is_an_api_idempotency_test_not_an_email_scenario(rig, scenario, db_engine):
    from studio_copilot.agent.contracts import Review

    from .helpers import start

    client = rig[0]
    run = start(rig, scenario)
    payload = Review(
        action="approve",
        expected_revision=run["revision"],
        body="Your teacher has reviewed this request.",
    ).model_dump()
    endpoint = f"/api/v1/agent-runs/{run['id']}/review"
    first = client.post(endpoint, json=payload)
    second = client.post(endpoint, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "approved"
    assert first.json()["approved_response_id"] == second.json()["approved_response_id"]
    with Session(db_engine) as db:
        responses = list(db.scalars(select(Message).where(Message.kind == "teacher_response")))
        assert len(responses) == 1
        assert responses[0].body == payload["body"]
