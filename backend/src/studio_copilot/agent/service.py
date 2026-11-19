"""Synchronous local run lifecycle, serialized per student; no worker queue required."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from yaml import YAMLError

from studio_copilot.administration.service import AdministrationError, conflict, invalid, require
from studio_copilot.agent.contracts import Review
from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.agent.persistence.locking import student_lock
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.policy import load_policy
from studio_copilot.agent.question_resolutions import (
    QUESTION_LIMIT_FAILURE,
    QuestionLimitError,
    RevisionExtractionError,
    validate_resolution_update,
)
from studio_copilot.agent.tracing import workflow_trace
from studio_copilot.agent.workflow import Workflow
from studio_copilot.persistence.models import AgentRun, Conversation, Message, Student

logger = logging.getLogger(__name__)


def latest_email(db, conversation_id):
    return db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.kind == "student_email",
        )
        .order_by(Message.occurred_at.desc(), Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )


def supersede_pending(db, conversation_id):
    latest = latest_email(db, conversation_id)
    if latest is None:
        return
    for run in db.scalars(
        select(AgentRun).where(
            AgentRun.conversation_id == conversation_id,
            AgentRun.status.in_(["running", "awaiting_review", "failed"]),
            AgentRun.approved_response_id.is_(None),
            AgentRun.source_message_id != latest.id,
        )
    ):
        run.status = "superseded"


class AgentService:
    def __init__(self, engine, model, *, checkpoints=None, policy_path: Path | None = None):
        self.engine, self.model = engine, model
        self.checkpoints = checkpoints or (lambda: postgres_checkpointer(engine))
        self.policy_path = policy_path

    def get(self, run_id):
        with Session(self.engine, expire_on_commit=False) as db:
            return require(db, AgentRun, run_id)

    def _student(self, conversation_id):
        with Session(self.engine) as db:
            return require(db, Conversation, conversation_id).student_id

    def start(self, conversation_id: UUID, source_message_id: UUID):
        with student_lock(self.engine, self._student(conversation_id)):
            with Session(self.engine, expire_on_commit=False) as db, db.begin():
                existing = db.scalar(
                    select(AgentRun).where(AgentRun.source_message_id == source_message_id)
                )
                run = self._create_run(db, conversation_id, source_message_id)
                run_id = run.id
            if not existing:
                self._drive(run_id, {"run_id": str(run_id)})
            return self.get(run_id)

    def _policy(self):
        try:
            policy = load_policy(self.policy_path)
            policy.pop("explanation", None)
            return policy
        except (OSError, ValueError, YAMLError) as error:
            raise AdministrationError(
                503, "policy_unavailable", "The policy resource is invalid or unavailable."
            ) from error

    def _create_run(self, db, conversation_id, source_message_id, *, policy=None, new_sender=False):
        """Create a run inside the caller's transaction while holding the student lock."""
        source = require(db, Message, source_message_id)
        if source.conversation_id != conversation_id or source.kind != "student_email":
            invalid("Source must be a student email in this conversation.")
        existing = db.scalar(select(AgentRun).where(AgentRun.source_message_id == source.id))
        if existing is not None:
            return existing
        if latest_email(db, conversation_id).id != source.id:
            conflict("Start the agent from the latest student email in this conversation.")
        supersede_pending(db, conversation_id)
        run = AgentRun(
            conversation_id=conversation_id,
            source_message_id=source.id,
            policy_snapshot=policy if policy is not None else self._policy(),
            interpretation={"intake": {"new_sender": True}} if new_sender else {},
        )
        db.add(run)
        db.flush()
        return run

    def receive_email(self, sender: str, body: str):
        """Persist an incoming email and run its workflow under one student lock."""
        sender = sender.strip().lower()
        policy = self._policy()
        # Serialize first contact before a student ID exists. The distinct namespace
        # keeps these keys independent from ordinary student locks.
        sender_key = uuid5(NAMESPACE_URL, "studio-copilot/incoming-email/" + sender)
        with student_lock(self.engine, sender_key):
            with Session(self.engine) as db:
                student_id = db.scalar(
                    select(Student.id).where(func.lower(Student.email) == sender)
                )
            new_sender = student_id is None
            student_id = student_id or uuid4()
            with student_lock(self.engine, student_id):
                with Session(self.engine) as db, db.begin():
                    if new_sender:
                        db.add(Student(id=student_id, display_name="New enquirer", email=sender))
                        db.flush()
                    conversation = db.scalar(
                        select(Conversation)
                        .where(Conversation.student_id == student_id)
                        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
                        .limit(1)
                    )
                    if conversation is None:
                        conversation = Conversation(student_id=student_id)
                        db.add(conversation)
                        db.flush()
                    source = Message(
                        conversation_id=conversation.id,
                        kind="student_email",
                        body=body,
                        occurred_at=datetime.now(UTC),
                    )
                    db.add(source)
                    db.flush()
                    run = self._create_run(
                        db, conversation.id, source.id, policy=policy, new_sender=new_sender
                    )
                    run_id = run.id
                self._drive(run_id, {"run_id": str(run_id)})
                return self.get(run_id)

    def review(self, run_id: UUID, review: Review):
        run = self.get(run_id)
        with student_lock(self.engine, self._student(run.conversation_id)):
            run = self.get(run_id)
            if run.status == "approved" and review.action == "approve":
                with Session(self.engine) as db:
                    body = require(db, Message, run.approved_response_id).body
                if review.expected_revision == run.revision and (
                    review.body is None or review.body == body
                ):
                    return run
            close_failed = (
                run.status == "failed"
                and run.approved_response_id is None
                and review.action == "reject"
            )
            if (
                run.status != "awaiting_review" and not close_failed
            ) or review.expected_revision != run.revision:
                conflict("This draft is no longer awaiting this review revision.")
            with Session(self.engine) as db:
                if latest_email(db, run.conversation_id).id != run.source_message_id:
                    conflict("A newer student email has superseded this draft.")
            if review.action == "revise":
                if (
                    not review.feedback
                    and not review.question_resolutions
                    and not review.regenerate
                ):
                    invalid(
                        "Revision requires teacher feedback, a question decision, "
                        "or a regeneration request."
                    )
                validate_resolution_update(
                    run.interpretation,
                    run.draft_details,
                    [item.model_dump(mode="json") for item in review.question_resolutions],
                )
            if review.action == "reject":
                # Do not checkpoint the rejection payload or create a rejection audit/message.
                with self.checkpoints() as saver:
                    saver.delete_thread(str(run_id))
                with Session(self.engine) as db, db.begin():
                    require(db, AgentRun, run_id, lock=True).status = "closed"
                return self.get(run_id)
            if review.action == "approve":
                # Capacity conflicts leave the review/checkpoint untouched. Booking and
                # teacher response commit together before asynchronous memory recovery.
                WorkflowStore(self.engine).approve(str(run_id), review.body)
            self._drive(
                run_id,
                Command(resume=review.model_dump()),
                phase="revision" if review.action == "revise" else "review",
            )
            return self.get(run_id)

    def retry(self, run_id: UUID):
        run = self.get(run_id)
        with student_lock(self.engine, self._student(run.conversation_id)):
            run = self.get(run_id)
            if run.status not in {"failed", "running", "finalizing"}:
                conflict("Only interrupted or failed processing can be retried.")
            if (
                run.approved_response_id is None
                and run.draft_details.get("failure_code") == QUESTION_LIMIT_FAILURE
            ):
                conflict(
                    "This enquiry exceeds the question limit. Close it and review it manually."
                )
            with Session(self.engine) as db:
                if (
                    run.approved_response_id is None
                    and latest_email(db, run.conversation_id).id != run.source_message_id
                ):
                    conflict("A newer email has superseded this run.")
            self._drive(run_id, None, phase="retry")
            return self.get(run_id)

    def _drive(self, run_id, input_value, *, phase="start"):
        with workflow_trace(run_id, phase) as trace:
            self._drive_traced(run_id, input_value, trace)

    def _drive_traced(self, run_id, input_value, trace):
        config = {"configurable": {"thread_id": str(run_id)}, "recursion_limit": 30}
        try:
            with Session(self.engine) as db, db.begin():
                run = require(db, AgentRun, run_id, lock=True)
                run.status = "finalizing" if run.approved_response_id else "running"
                run.error = None
                finalizing = run.approved_response_id is not None
                approved_revision = run.revision
            with self.checkpoints() as saver:
                graph = Workflow(self.engine, self.model).compile(saver)
                snapshot = graph.get_state(config)
                if (
                    input_value is None
                    and finalizing
                    and snapshot.values
                    and not any(t.interrupts for t in snapshot.tasks)
                ):
                    # A draft may have committed before its initial review interrupt
                    # was checkpointed. Advance safely to the interrupt (or finish an
                    # already resumed approval), then restore its durable decision.
                    graph.invoke(None, config)
                    snapshot = graph.get_state(config)
                if input_value is None and finalizing and any(t.interrupts for t in snapshot.tasks):
                    # A crash may occur after committing the booking/response but before
                    # the review interrupt consumes the approval command.
                    input_value = Command(
                        resume={
                            "action": "approve",
                            "expected_revision": approved_revision,
                            "body": WorkflowStore(self.engine).approved_response(str(run_id)),
                        }
                    )
                if input_value is None and not snapshot.values:
                    if finalizing:
                        raise RuntimeError("The approval checkpoint is unavailable.")
                    input_value = {"run_id": str(run_id)}
                # Recover a crash between persisting the draft and reaching its interrupt.
                if isinstance(input_value, Command) and not any(
                    t.interrupts for t in snapshot.tasks
                ):
                    graph.invoke(None, config)
                graph.invoke(input_value, config)
                if any(task.interrupts for task in graph.get_state(config).tasks):
                    with Session(self.engine) as db, db.begin():
                        run = require(db, AgentRun, run_id, lock=True)
                        if run.approved_response_id is None:
                            run.status = "awaiting_review"
        except AdministrationError:
            trace.fail()
            raise
        except (QuestionLimitError, RevisionExtractionError) as error:
            trace.fail()
            with Session(self.engine) as db, db.begin():
                run = require(db, AgentRun, run_id, lock=True)
                if run.status not in {"approved", "closed", "superseded"}:
                    run.status = "failed"
                    if isinstance(error, QuestionLimitError):
                        run.draft_details = {
                            **run.draft_details,
                            "failure_code": QUESTION_LIMIT_FAILURE,
                        }
                    run.error = (
                        "The combined question checklist exceeds 20 questions. "
                        "Close this review and handle the enquiry manually."
                        if isinstance(error, QuestionLimitError)
                        else "The revised enquiry could not be interpreted. "
                        "Review the enquiry manually or retry extraction."
                    )
        except Exception as error:
            trace.fail()
            # No provider exception strings, prompts, or credentials in logs/API errors.
            logger.error(
                "agent_run_failed",
                extra={"run_id": str(run_id), "error_type": type(error).__name__},
            )
            with Session(self.engine) as db, db.begin():
                run = require(db, AgentRun, run_id, lock=True)
                if run.status not in {"approved", "closed", "superseded"}:
                    run.status = "failed"
                    run.error = "Processing failed. Check configuration and retry this run."
