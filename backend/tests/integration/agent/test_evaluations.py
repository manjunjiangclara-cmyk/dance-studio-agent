"""Harness regressions use real API, graph, PostgreSQL and persisted checkpoints."""

import os
import re
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import Draft, MakeupInterpretation, ToolTurn
from studio_copilot.agent.makeup import overlapping_session
from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.agent.persistence.locking import student_lock
from studio_copilot.persistence.models import ClassSession, Student
from workflow_evaluations.cases import load_scenarios
from workflow_evaluations.fixtures import isolated_database, seed_studio
from workflow_evaluations.runner import grade_run, run_scenario

from .helpers import FakeModel, turn

pytestmark = pytest.mark.integration


class EmailScenarioModel(FakeModel):
    """A controlled model for harness testing; this does not evaluate language quality."""

    def interpret_makeup(self, context):
        body = context["source"]["body"]
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", body)
        earlier_emails = [
            message for message in context["history"] if message["kind"] == "student_email"
        ]
        absence_email = earlier_emails[0] if earlier_emails else context["source"]
        absence = re.search(r"\d{4}-\d{2}-\d{2}", absence_email["body"]).group()
        return MakeupInterpretation(
            request_summary="Synthetic makeup request",
            absence_date=absence,
            absence_message_id=absence_email["id"],
            preferred_date=dates[-1],
            preferred_weekday="Saturday" if "Saturday" in body else "Thursday",
            location_preference=None,
            missing_details=[],
            enduring_preferences=[],
        )

    def choose_tools(self, context, transcript):
        if transcript:
            return ToolTurn(calls=[], output=[])
        preferred = context["interpretation"]["preferred_date"]
        return turn(
            "search_sessions",
            {
                "from_date": preferred,
                "to_date": preferred,
                "weekday": None,
                "level": "Level 2",
                "location_id": None,
            },
        )

    def draft(self, context):
        sessions = [
            session
            for evidence in context["evidence"]
            if evidence["tool"] == "search_sessions"
            for session in evidence["result"].get("items", [])
        ]
        validated_ids = {
            session_id
            for evidence in context["evidence"]
            if evidence["tool"] == "validate_makeup_candidates"
            for session_id in evidence["result"].get("valid_session_ids", [])
        }
        proposal = next((s["id"] for s in sessions if s["id"] in validated_ids), None)
        if context["teacher_feedback"]:
            proposal = None
        return Draft(
            body="A synthetic teacher-reviewable reply.",
            rationale="Test fixture.",
            questions=[],
            references=["session:" + proposal] if proposal else [],
            booking_session_id=proposal,
        )


@pytest.mark.parametrize(
    "case_id",
    [
        "makeup_approval",
        "followup_correction",
        "teacher_revision",
        "makeup_rejection",
        "persistent_review",
        "capacity_changes",
        "missing_session_membership",
        "already_booked_target",
        "already_full",
        "makeup_rule_bypass_injection",
    ],
)
def test_email_evaluation_harness_runs_complete_lifecycle(db_engine, case_id):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    case = next(item for item in load_scenarios() if item.id == case_id)
    result = run_scenario(db_engine, case, EmailScenarioModel())
    failures = [check for check in result["checks"] if not check["passed"]]
    assert result["passed"], {"error_type": result.get("error_type"), "failures": failures}
    assert result["runs"]
    assert result["human_review"] == "pending"
    stages = [snapshot["stage"] for snapshot in result["memory_snapshots"]]
    for index in range(1, len(case.emails) + 1):
        assert f"email_{index}:memory_before_draft" in stages
        assert f"email_{index}:memory_after_intake" in stages


def test_evaluation_records_two_committed_memory_updates(db_engine):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    case = next(item for item in load_scenarios() if item.id == "makeup_approval")
    result = run_scenario(db_engine, case, EmailScenarioModel())
    assert result["passed"], [c for c in result["checks"] if not c["passed"]]
    snapshots = {snapshot["stage"]: snapshot for snapshot in result["memory_snapshots"]}
    run = result["runs"][0]
    conversation_id = run["conversation_id"]
    for stage in [
        "email_1:memory_before_draft",
        "email_1:memory_after_intake",
        "before_teacher_review",
    ]:
        memory = snapshots[stage]["context"]["_agent_memory"]
        request = memory["requests"][conversation_id]
        assert request["source_message_id"] == run["source_message_id"]
        assert request["kind"] == "student_stated"
        assert not memory.get("approved_responses")
        assert snapshots[stage]["context"]["staff_note"] == "Synthetic evaluation fixture"
    approved = result["reviews"][0]["result"]
    response_id = approved["approved_response_id"]
    reviewed_memory = snapshots["memory_after_approval"]["context"]["_agent_memory"]
    request = reviewed_memory["requests"][conversation_id]
    assert request["source_message_id"] == response_id
    assert request["kind"] == "teacher_reviewed"
    final_body = run["draft_details"]["body"]
    assert final_body in request["request_summary"]
    assert reviewed_memory["approved_responses"][response_id]["conversation_id"] == conversation_id


def test_evaluation_detects_memory_written_only_after_drafting(db_engine, monkeypatch):
    from studio_copilot.agent.persistence.store import WorkflowStore
    from studio_copilot.agent.workflow.nodes import WorkflowNodes

    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    remember = WorkflowStore.remember_student
    persist = WorkflowNodes.persist_draft
    pending = {}

    def delay(self, run_id, *args):
        pending[run_id] = (self, args)

    def persist_with_late_memory(self, state):
        store, args = pending.pop(state["run_id"])
        remember(store, state["run_id"], *args)
        return persist(self, state)

    monkeypatch.setattr(WorkflowStore, "remember_student", delay)
    monkeypatch.setattr(WorkflowNodes, "persist_draft", persist_with_late_memory)
    result = run_scenario(db_engine, load_scenarios()[0], EmailScenarioModel())
    checks = {check["name"]: check["passed"] for check in result["checks"]}
    assert not result["passed"]
    assert not checks["email_1:memory_before_draft:request_source"]
    assert checks["email_1:memory_after_intake:request_source"]
    assert checks["memory_after_approval:request_kind"]
    assert result["reviews"][0]["result"]["status"] == "approved"


def test_evaluation_detects_missing_memory_after_successful_approval(db_engine, monkeypatch):
    from studio_copilot.agent.persistence import store

    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    save = store._save_memory

    def skip_approved_memory(*args, **kwargs):
        if not kwargs.get("approved"):
            return save(*args, **kwargs)

    monkeypatch.setattr(store, "_save_memory", skip_approved_memory)
    result = run_scenario(db_engine, load_scenarios()[0], EmailScenarioModel())
    checks = {check["name"]: check["passed"] for check in result["checks"]}
    assert not result["passed"]
    assert result["reviews"][0]["result"]["status"] == "approved"
    assert checks["email_1:memory_after_intake:request_kind"]
    assert not checks["memory_after_approval:request_source"]
    assert not checks["memory_after_approval:request_kind"]
    assert not checks["memory_after_approval:approved_response_entry"]


def test_evaluation_detects_reconciliation_using_the_wrong_response_body(db_engine, monkeypatch):
    from studio_copilot.agent.persistence.store import WorkflowStore

    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    monkeypatch.setattr(
        WorkflowStore, "approved_response", lambda *args: "The draft was substituted by mistake."
    )
    result = run_scenario(db_engine, load_scenarios()[0], EmailScenarioModel())
    checks = {check["name"]: check["passed"] for check in result["checks"]}
    assert not result["passed"]
    assert result["reviews"][0]["result"]["status"] == "approved"
    assert checks["approved_body_matches_teacher_response"]
    assert checks["memory_after_approval:request_summary"]
    assert not checks["approval_input_matches_stored_teacher_response"]


def test_evaluation_schema_is_isolated_and_removed_after_failure(db_engine):
    schema = None
    with pytest.raises(RuntimeError, match="Controlled evaluation failure"):
        with isolated_database(os.environ["TEST_DATABASE_URL"]) as engine:
            with engine.connect() as connection:
                schema = connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("eval_")
            seed_studio(engine, "normal")
            with Session(db_engine) as db:
                assert db.scalar(select(func.count()).select_from(Student)) == 0
            raise RuntimeError("Controlled evaluation failure")
    with db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_namespace WHERE nspname = :schema"),
                {"schema": schema},
            )
            == 0
        )


def test_evaluation_senders_do_not_share_global_intake_locks(db_engine):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    shared_sender = uuid5(NAMESPACE_URL, "studio-copilot/incoming-email/alex@example.com")
    with student_lock(db_engine, shared_sender):
        result = run_scenario(db_engine, load_scenarios()[0], EmailScenarioModel())
    assert result["passed"], [c for c in result["checks"] if not c["passed"]]
    assert result["inputs"][0]["from"] != "alex@example.com"


def test_overlapping_booking_fixture_and_adjacent_boundary(db_engine):
    from datetime import timedelta
    from uuid import UUID

    case = next(c for c in load_scenarios() if c.id == "makeup_overlapping_existing_booking")
    fixture = seed_studio(db_engine, case.fixture, case.setup)
    with Session(db_engine) as db:
        target = db.get(ClassSession, UUID(fixture["sessions"]["thursday"]))
        other = db.get(ClassSession, UUID(fixture["sessions"]["conflicting_booking"]))
        student_id = UUID(fixture["student_id"])
        assert student_id not in target.students
        assert student_id in other.students
        assert other.starts_at == target.starts_at + timedelta(minutes=30)
        assert target.starts_at < other.starts_at < target.ends_at < other.ends_at
        assert overlapping_session(db, student_id, target)
        other.starts_at = target.ends_at
        other.ends_at = other.starts_at + timedelta(hours=1)
        db.flush()
        assert not overlapping_session(db, student_id, target)


def test_overlap_scenario_catches_incorrect_duplicate_claim(db_engine):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    case = next(c for c in load_scenarios() if c.id == "makeup_overlapping_existing_booking")
    result = run_scenario(db_engine, case, EmailScenarioModel())
    run = result["runs"][0]
    assert run["draft_details"]["booking_session_id"] is None
    run["draft_details"]["body"] = "Our records already list you in the requested session."
    checks = grade_run(run, case.emails[0].expect, result["fixture"])
    failed = {check["name"] for check in checks if not check["passed"]}
    assert failed == {"draft_contradicts_scenario:already list you in the requested session"}


@pytest.mark.parametrize("mode", ["good", "no_citation", "contradiction"])
def test_checklist_answer_evaluation_checks_model_input_and_raw_draft(db_engine, mode):
    from studio_copilot.agent.contracts import EnquiryAnswer, EnquiryInterpretation, Routing

    class ChecklistModel(FakeModel):
        def __init__(self, mode):
            super().__init__()
            self.mode = mode
            self.routing = Routing(
                intents=["general_enquiry"],
                action="information_only",
                request_summary="Clothing question",
                needs_clarification=False,
                reason="The student requests information.",
            )

        def interpret_enquiry(self, context):
            return EnquiryInterpretation(
                request_summary="Clothing question",
                missing_details=[],
                enduring_preferences=[],
                questions=["What should I wear?"],
                requested_actions=[],
            )

        def choose_tools(self, context, transcript):
            return ToolTurn(calls=[], output=[])

        def draft(self, context):
            decisions = context.get("question_resolutions", [])
            decision = decisions[0] if decisions else None
            answer = (
                "Comfortable clothes and shoes are not suitable; wear a black leotard."
                if decision and self.mode == "contradiction"
                else decision["answer"]
                if decision
                else "The teacher needs to check."
            )
            return Draft(
                body=answer if decision else "I will check the clothing requirements.",
                rationale="Synthetic test.",
                questions=[],
                references=[],
                answers=[
                    EnquiryAnswer(
                        question="What should I wear?",
                        status="answered" if decision else "needs_teacher",
                        answer=answer,
                        references=(
                            ["teacher_answer:" + decision["question_id"]]
                            if decision and self.mode != "no_citation"
                            else []
                        ),
                    )
                ],
            )

    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    scenario = next(s for s in load_scenarios() if s.id == "enquiry_checklist_answer_redraft")
    result = run_scenario(db_engine, scenario, ChecklistModel(mode))
    checks = {item["name"]: item["passed"] for item in result["checks"]}
    assert result["passed"] == (mode == "good"), result
    assert checks["model_cites_teacher_answer_for_question"] == (mode != "no_citation")
    assert checks["raw_answer_excludes:not suitable"] == (mode != "contradiction")
    assert checks["teacher_answer_in_final_draft"]
    assert result["checklist_model_drafts"][0]["question_resolutions"][0]["question"] == (
        "What should I wear?"
    )
