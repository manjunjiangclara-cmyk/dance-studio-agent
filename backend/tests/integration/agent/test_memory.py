from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Enrolment, Message, Student

from .helpers import review, start

pytestmark = pytest.mark.integration


def test_memory_before_query_and_approval_stores_final_response(
    rig, scenario, db_engine, monkeypatch
):
    client, model, service, saver = rig

    def memory_exists(context):
        with Session(db_engine) as db:
            student = db.get(Student, scenario["student"])
            assert "Thursday" in student.ai_summary
            assert student.context["staff_note"] == "Preserve me"
            request = student.context["_agent_memory"]["requests"][str(scenario["conversation"])]
            assert request["source_message_id"] == str(scenario["source"])
            assert request["kind"] == "student_stated"

    from studio_copilot.agent.workflow import queries

    gather = queries.gather_makeup

    def gather_after_memory(engine, state):
        memory_exists(state["context"])
        return gather(engine, state)

    monkeypatch.setattr(queries, "gather_makeup", gather_after_memory)
    run = start(rig, scenario)
    repeated = service.start(scenario["conversation"], scenario["source"])
    assert str(repeated.id) == run["id"]
    assert model.query_count == 0
    result = review(client, run, "approve", body="Friday instead; I will check suitable options.")
    assert result.status_code == 200, result.text
    approved = result.json()
    assert approved["status"] == "approved"
    response_id = approved["approved_response_id"]
    message = client.get(f"/api/v1/messages/{response_id}").json()
    assert message["kind"] == "teacher_response"
    assert message["body"] == "Friday instead; I will check suitable options."
    assert (
        review(client, approved, "approve", body=message["body"]).json()["approved_response_id"]
        == response_id
    )
    with Session(db_engine) as db:
        student = db.get(Student, scenario["student"])
        assert "Friday" in student.ai_summary and "Thursday" not in student.ai_summary
        assert student.context["staff_note"] == "Preserve me"
        request = student.context["_agent_memory"]["requests"][str(scenario["conversation"])]
        assert request["source_message_id"] == response_id and request["kind"] == "teacher_reviewed"
        assert student.highest_level == "Level 2"
        assert db.scalar(select(func.count()).select_from(Enrolment)) == 1
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
            )
            == 1
        )
    assert (
        client.patch(f"/api/v1/messages/{response_id}", json={"body": "rewrite"}).status_code == 409
    )


def test_followup_supersedes_draft_and_memory_uses_history(rig, scenario):
    client, model, _, _ = rig
    old = start(rig, scenario)
    email = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={
            "kind": "student_email",
            "body": "Actually, Saturday instead.",
            "occurred_at": "2027-02-07T11:00:00+11:00",
        },
    ).json()
    assert client.get(f"/api/v1/agent-runs/{old['id']}").json()["status"] == "superseded"
    assert review(client, old, "approve").status_code == 409
    updated = dict(scenario, source=UUID(email["id"]))
    new = start(rig, updated)
    assert new["interpretation"]["preferred_weekday"] == "Saturday"
    profile = client.get(f"/api/v1/students/{scenario['student']}").json()
    assert "Saturday" in profile["ai_summary"] and "Thursday" not in profile["ai_summary"]
    assert profile["context"]["_agent_memory"]["preferences"] == {}
    assert {m["kind"] for m in model.contexts[-1]["history"]} == {
        "student_email",
        "assistant_draft",
    }


def test_memory_is_loaded_across_conversations(rig, scenario, db_engine):
    client, model, _, _ = rig
    run = start(rig, scenario)
    assert review(client, run, "approve").json()["status"] == "approved"
    conversation = client.post(
        "/api/v1/conversations", json={"student_id": str(scenario["student"])}
    ).json()
    email = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"kind": "student_email", "body": "Saturday please"},
    ).json()
    next_scenario = dict(scenario, conversation=UUID(conversation["id"]), source=UUID(email["id"]))
    start(rig, next_scenario)
    memory = model.contexts[-1]["student"]["context"]["_agent_memory"]
    assert memory["preferences"]["travel"]["value"] == "public transport"
    assert memory["requests"][str(scenario["conversation"])]["approved_response_id"]
