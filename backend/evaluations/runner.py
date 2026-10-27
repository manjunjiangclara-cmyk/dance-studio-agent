"""Evaluate incoming emails through the real API and graph, stopping at teacher review."""

import json
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from studio_copilot.persistence.models import (
    ClassSession,
    Enrolment,
    Message,
    Student,
)

from .cases import POLICY, Scenario, render
from .fixtures import CANARY, seed_studio
from .grading import grade_run
from .model import MeasuredModel


def database_snapshot(engine) -> dict:
    with Session(engine) as db:
        return {
            "rosters": {
                str(s.id): sorted(str(student.id) for student in s.students)
                for s in db.scalars(select(ClassSession))
            },
            "enrolments": sorted(
                (
                    str(e.id),
                    str(e.student_id),
                    str(e.class_id),
                    str(e.starts_on),
                    str(e.ends_on),
                    e.status,
                )
                for e in db.scalars(select(Enrolment))
            ),
            "responses": {
                str(m.id): m.body
                for m in db.scalars(select(Message).where(Message.kind == "teacher_response"))
            },
        }


def run_scenario(engine, scenario: Scenario, model) -> dict:
    started = monotonic()
    result = {
        "case": scenario.id,
        "description": scenario.description,
        "checks": [],
        "inputs": [],
        "runs": [],
        "expected": [],
        "rubric": scenario.rubric,
        "human_review": "pending",
    }

    def check(name, actual, expected):
        result["checks"].append(
            {"name": name, "passed": actual == expected, "expected": expected, "actual": actual}
        )

    try:
        fixture = seed_studio(engine, scenario.setup)
        result["fixture"] = fixture
        before = database_snapshot(engine)
        service = AgentService(engine, model, policy_path=POLICY)
        app = create_app(engine, admin_token="synthetic-eval-token", agent_service=service)
        with TestClient(app, headers={"Authorization": "Bearer synthetic-eval-token"}) as client:
            previous = None
            for index, step in enumerate(scenario.steps):
                payload = {
                    "from": fixture["sender"],
                    "body": render(step.input.body, fixture["dates"]),
                }
                result["inputs"].append(payload)
                result["expected"].append(
                    render(step.expected.model_dump(exclude_unset=True), fixture["dates"])
                )
                response = client.post("/api/v1/incoming-emails", json=payload)
                check(f"email_{index + 1}:http", response.status_code, 200)
                if response.status_code != 200:
                    result["intake_error"] = response.json()
                    break
                run = response.json()
                result["runs"].append(run)
                result["checks"].extend(
                    {**c, "name": f"email_{index + 1}:" + c["name"]}
                    for c in grade_run(run, step, fixture)
                )
                check(f"email_{index + 1}:no_business_changes", database_snapshot(engine), before)
                with Session(engine) as db:
                    source = db.get(Message, UUID(run["source_message_id"]))
                    check(f"email_{index + 1}:stored_email", source.body, payload["body"])
                if previous:
                    check("same_conversation", run["conversation_id"], previous["conversation_id"])
                    old = client.get("/api/v1/agent-runs/" + previous["id"]).json()
                    check("earlier_run_superseded", old["status"], "superseded")
                previous = run
                if run["status"] != "awaiting_review":
                    break
        result["database_after"] = database_snapshot(engine)
        check("all_email_steps_executed", len(result["runs"]), len(scenario.steps))
        with Session(engine) as db:
            students = list(
                db.scalars(select(Student).where(Student.id != UUID(fixture["canary_id"])))
            )
            result["memory_after"] = [
                {"student_id": str(s.id), "summary": s.ai_summary, "context": s.context}
                for s in students
            ]
        serialized = json.dumps(result["memory_after"]).lower()
        for marker in [CANARY, "private-canary@example.com"]:
            check("no_private_data_in_memory:" + marker, marker.lower() in serialized, False)
    except Exception as error:
        # Provider and database exception messages may contain credentials; retain types only.
        result["error_type"] = type(error).__name__
        check("scenario_completed_without_exception", type(error).__name__, None)
    if isinstance(model, MeasuredModel):
        result["model_calls"] = model.calls
        result["model_failures"] = model.failures
        check("within_model_call_budget", model.exhausted, False)
        check("all_model_calls_completed", all(c["completed"] for c in model.calls), True)
        check("all_model_steps_succeeded", model.failures, [])
    result["passed"] = bool(result["checks"]) and all(c["passed"] for c in result["checks"])
    result["latency_ms"] = round((monotonic() - started) * 1000)
    return result


def build_report(results, model_name: str, dataset_hash: str) -> dict:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "model": model_name,
        "dataset_sha256": dataset_hash,
        "evaluation": "live_email_workflow",
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "human_review": "pending; automated checks do not establish draft quality",
        "results": results,
    }
