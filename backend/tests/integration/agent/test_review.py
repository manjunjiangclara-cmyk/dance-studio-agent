from uuid import UUID

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import AgentRun, Message, Student

from .helpers import review, start

pytestmark = pytest.mark.integration


def test_makeup_response_can_regenerate_without_feedback(rig, scenario, db_engine):
    client, model, _, _ = rig
    run = start(rig, scenario)

    response = review(client, run, "revise", regenerate=True)
    assert response.status_code == 200, response.text
    regenerated = response.json()
    assert regenerated["status"] == "awaiting_review"
    assert regenerated["revision"] == run["revision"] + 1
    assert regenerated["draft_message_id"] != run["draft_message_id"]
    assert regenerated["approved_response_id"] is None
    assert model.query_count == 0  # Makeup lookups remain deterministic.
    with Session(db_engine) as db:
        assert db.get(AgentRun, UUID(run["id"])).approved_response_id is None
        assert {message.kind for message in db.scalars(select(Message))} == {
            "student_email",
            "assistant_draft",
        }


def test_revision_is_explicit_and_rejection_leaves_no_record_or_checkpoint(
    rig, scenario, db_engine
):
    client, model, _, saver = rig
    run = start(rig, scenario)
    revised = review(client, run, "revise", feedback="Ask about travel preferences.")
    assert revised.status_code == 200, revised.text
    newer = revised.json()
    assert newer["revision"] == 2 and newer["draft_message_id"] != run["draft_message_id"]
    assert model.query_count == 0  # Required makeup lookups are deterministic.
    assert review(client, run, "approve").status_code == 409
    assert review(client, newer, "reject").json()["status"] == "closed"
    assert saver.get_tuple({"configurable": {"thread_id": run["id"]}}) is None
    with Session(db_engine) as db:
        assert {m.kind for m in db.scalars(select(Message))} == {"student_email", "assistant_draft"}
        assert "Teacher approved" not in db.get(Student, scenario["student"]).ai_summary
        assert db.get(AgentRun, UUID(run["id"])).approved_response_id is None


@pytest.mark.parametrize("final_action", ["approve", "reject"])
def test_all_generated_draft_revisions_stay_protected(rig, scenario, db_engine, final_action):
    client = rig[0]
    run = start(rig, scenario)
    revised = review(client, run, "revise", feedback="Ask about travel preferences.")
    assert revised.status_code == 200, revised.text
    newer = revised.json()
    drafts = [run["draft_message_id"], newer["draft_message_id"]]
    original_bodies = {mid: client.get(f"/api/v1/messages/{mid}").json()["body"] for mid in drafts}

    def assert_protected():
        for message_id in drafts:
            response = client.patch(f"/api/v1/messages/{message_id}", json={"body": "Rewrite"})
            assert response.status_code == 409, response.text
            assert (
                client.get(f"/api/v1/messages/{message_id}").json()["body"]
                == original_bodies[message_id]
            )

    assert_protected()
    assert review(client, newer, final_action).status_code == 200
    assert_protected()
    with Session(db_engine) as db:
        assert all(db.get(Message, UUID(mid)).review_managed for mid in drafts)
    manual = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={"kind": "assistant_draft", "body": "Manual draft"},
    )
    assert manual.status_code == 201
    edited = client.patch(f"/api/v1/messages/{manual.json()['id']}", json={"body": "Manual edit"})
    assert edited.status_code == 200
    assert edited.json()["body"] == "Manual edit"


def test_upgrade_protects_legacy_revisions_without_retained_ownership(rig, scenario, db_engine):
    client = rig[0]
    run = start(rig, scenario)
    revised = review(client, run, "revise", feedback="Ask about travel preferences.").json()
    manual = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/messages",
        json={"kind": "assistant_draft", "body": "Legacy manual draft"},
    ).json()
    # Recreate the old schema, where the current pointer is the only saved ownership.
    with db_engine.begin() as connection:
        from pathlib import Path
        from runpy import run_path

        migration = run_path(
            str(
                Path(__file__).parents[3]
                / "migrations"
                / "versions"
                / "92a4b7c1d803_track_generated_draft_ownership.py"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration["downgrade"]()
            migration["upgrade"]()
    for message_id in [run["draft_message_id"], revised["draft_message_id"], manual["id"]]:
        assert (
            client.patch(f"/api/v1/messages/{message_id}", json={"body": "Rewrite"}).status_code
            == 409
        )
    with Session(db_engine) as db:
        assert not db.get(Message, scenario["source"]).review_managed
