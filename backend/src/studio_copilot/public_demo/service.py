"""Drive the shared workflow with a private SQLite ledger and fictional records."""

import json
import re
import secrets
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from studio_copilot.administration.service import AdministrationError
from studio_copilot.agent.contracts import Review
from studio_copilot.agent.makeup import evidence_result, validated_candidate_ids
from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.question_resolutions import require_resolved_questions
from studio_copilot.agent.review_requirements import review_requirements
from studio_copilot.agent.workflow.graph import Workflow
from studio_copilot.public_demo.records import CASES, FictionalRecords
from studio_copilot.public_demo.trial_booking import TRIAL, latest_text, previous_offer, trial_draft

DAILY_RUN_LIMIT = 20
EXPIRES_IN = 3600
LEASE_SECONDS = 300
MAX_ATTEMPTS = 2
MAX_REVISION_ATTEMPTS = 20

DEMO_SIGNOFF = re.compile(
    r"(?im)(?:^|\n)[ \t]*(?:best(?: regards)?|kind regards|warm regards|regards|"
    r"warmly|sincerely|cheers|thanks|thank you)[,.!]?[ \t]*"
    r"(?:\n[ \t]*[^\n]{1,80}[ \t]*)?[ \t]*\Z"
)


def unsigned_demo_draft(body, state):
    """Remove generated sign-offs while preserving staff edits and booking wording."""
    body = DEMO_SIGNOFF.sub("", body).rstrip()
    name = str(state.get("context", {}).get("student", {}).get("name") or "").strip()
    aliases = {
        "[your name]",
        "[teacher name]",
        "[teacher's name]",
        "[studio name]",
        "merri ballet",
        "merri ballet team",
        "the merri ballet team",
        "studio team",
    }
    if name and name.casefold() != "new enquirer":
        aliases.update({name.casefold(), name.split()[0].casefold()})
    paragraphs = body.rsplit("\n\n", 1)
    if len(paragraphs) == 2 and paragraphs[-1].strip().casefold() in aliases:
        body = paragraphs[0].rstrip()
    return body or "Thanks for your message."


def evidence_questions(state):
    missing = []
    for item in state.get("evidence", []):
        if item["tool"] != "document_answer":
            continue
        result = item["result"]
        if result.get("status") != "answered":
            missing.append(
                {
                    "id": result["question_id"],
                    "label": result["question"],
                }
            )
    return missing


def supporting_evidence(state):
    evidence = []
    excluded = {
        item["session_id"]: item["reason"]
        for item in evidence_result(state["evidence"], "validate_makeup_candidates").get(
            "excluded", []
        )
    }
    for item in state["evidence"]:
        result = item.get("result", {})
        if item["tool"] == "verify_makeup_request":
            missed = result.get("missed_session")
            if missed and result.get("notice_acceptable"):
                evidence.append(
                    f"Absence notice: The notice for {missed['class_name']} was received "
                    "before the class started."
                )
            evidence.extend(result.get("issues", []))
            existing = result.get("existing_makeup")
            if existing:
                evidence.append(
                    f"Existing makeup booking: {existing['class_name']} at "
                    f"{existing['starts_at']}. Confirmed on the student's roster."
                )
        elif item["tool"] == "validate_makeup_candidates":
            if level := result.get("max_attended_level"):
                evidence.append(f"Student record: The highest attended class level is {level}.")
        elif item["tool"] == "search_sessions":
            for row in result.get("items", []):
                local = datetime.fromisoformat(row["starts_at"])
                count = row.get("remaining_places")
                if count is None:
                    continue
                status = (
                    " The student's makeup request is awaiting teacher approval."
                    if row.get("makeup_status") == "awaiting_review"
                    else ""
                )
                if excluded.get(row["id"]) == "above_attended_level":
                    status += " This class is above the student's recorded attendance level."
                elif excluded.get(row["id"]) in {
                    "requested_class_mismatch",
                    "requested_time_mismatch",
                }:
                    status += " This class does not match the requested session."
                evidence.append(
                    f"Class availability: {row['class_name']}, {local:%A %d %B %Y at %I:%M %p}, "
                    f"{row.get('location_name', 'the studio')}. "
                    f"{count} {'place' if count == 1 else 'places'} open.{status}"
                )
        elif item["tool"] == "document_answer":
            for claim in result.get("claims", []):
                evidence.append(claim["text"])
                for citation in claim.get("citations", []):
                    evidence.append(
                        f"{citation['title']} · revision {citation['revision']}: "
                        f"“{citation['quote']}”"
                    )
        elif item["tool"] == "get_timetable" and state["flow"] != "makeup":
            evidence.extend(
                f"Timetable: {row['name']} at {row['location']['name']}."
                for row in result.get("items", [])
            )
    evidence.extend(
        f"{item['label']}: Teacher information is needed." for item in evidence_questions(state)
    )
    if not evidence:
        evidence.extend(state.get("warnings", []))
    return list(dict.fromkeys(evidence))


class PublicDemo:
    def __init__(
        self,
        path,
        *,
        factory=OpenAIModel,
        clock=time.time,
        daily_run_limit=DAILY_RUN_LIMIT,
        records=None,
    ):
        self.path = str(path)
        self.factory = factory
        self.clock = clock
        self.daily_run_limit = daily_run_limit
        self.records = records if records is not None else FictionalRecords()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS graph_runs (
                request_id TEXT PRIMARY KEY, token TEXT NOT NULL UNIQUE,
                scenario TEXT NOT NULL, day TEXT NOT NULL, created REAL NOT NULL,
                lease TEXT, busy_until REAL NOT NULL DEFAULT 0,
                evidence_attempts INTEGER NOT NULL DEFAULT 0,
                draft_attempts INTEGER NOT NULL DEFAULT 0,
                revision_attempts INTEGER NOT NULL DEFAULT 0,
                teacher_answers TEXT, draft TEXT, interpretation TEXT, evidence TEXT,
                revision_answers TEXT, revision INTEGER, decision TEXT, approval TEXT
            )""")

            columns = {row[1] for row in db.execute("PRAGMA table_info(graph_runs)")}
            if "revision_attempts" not in columns:
                db.execute(
                    "ALTER TABLE graph_runs ADD COLUMN revision_attempts INTEGER NOT NULL DEFAULT 0"
                )
            if "revision_answers" not in columns:
                db.execute("ALTER TABLE graph_runs ADD COLUMN revision_answers TEXT")

            db.execute("""CREATE TABLE IF NOT EXISTS walkthrough_inputs (
                request_id TEXT PRIMARY KEY, student TEXT NOT NULL, email_body TEXT NOT NULL,
                previous_run TEXT UNIQUE, context TEXT NOT NULL,
                FOREIGN KEY(request_id) REFERENCES graph_runs(request_id)
            )""")

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            with db:
                yield db

    @contextmanager
    def checkpoints(self):
        with SqliteSaver.from_conn_string(self.path) as saver:
            yield saver

    @property
    def model_name(self):
        import os

        return os.environ.get("OPENAI_MODEL") or "shared workflow"

    def _day(self, now):
        return datetime.fromtimestamp(now, ZoneInfo("Australia/Melbourne")).date().isoformat()

    def _prune(self, db, now):
        # Both current and pre-migration data expire without migrating saved conversations.
        expired = [
            row["request_id"]
            for row in db.execute(
                "SELECT request_id FROM graph_runs "
                "WHERE (created < ? OR day != ?) AND busy_until <= ?",
                (now - EXPIRES_IN, self._day(now), now),
            )
        ]
        tables = {row["name"] for row in db.execute("SELECT name FROM sqlite_master")}
        for table in ("checkpoints", "writes"):
            if table in tables:
                db.executemany(f"DELETE FROM {table} WHERE thread_id = ?", [(x,) for x in expired])
        db.executemany(
            "DELETE FROM walkthrough_inputs WHERE request_id = ?", [(x,) for x in expired]
        )
        db.executemany(
            "UPDATE graph_runs SET teacher_answers = NULL, draft = NULL, interpretation = NULL, "
            "evidence = NULL, decision = NULL, approval = NULL WHERE request_id = ?",
            [(x,) for x in expired],
        )
        db.execute(
            "DELETE FROM graph_runs WHERE created < ? AND busy_until <= ?", (now - 4 * 86400, now)
        )
        if "turns" in tables and "threads" in tables:
            cutoff = now - 4 * 86400
            db.execute(
                "DELETE FROM turns WHERE thread_token IN "
                "(SELECT token FROM threads WHERE created < ?)",
                (cutoff,),
            )
            db.execute("DELETE FROM threads WHERE created < ?", (cutoff,))
        if "runs" in tables:
            db.execute("DELETE FROM runs WHERE created < ?", (now - 4 * 86400,))

    def create(self, scenario, request_id):
        if scenario not in CASES:
            raise HTTPException(422, "Choose a fictional example.")
        return self._create(scenario, request_id)

    def create_walkthrough(self, request_id, student, email_body, previous_token=None):
        if student != "new" and student not in self.records.students:
            raise HTTPException(422, "Choose a fictional student.")
        return self._create("walkthrough", request_id, student, email_body, previous_token)

    def _create(self, scenario, request_id, student=None, email_body=None, previous_token=None):
        now = self.clock()
        day = self._day(now)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._prune(db, now)
            previous = None
            if previous_token is not None:
                previous = db.execute(
                    "SELECT runs.*, inputs.student, inputs.context FROM graph_runs AS runs "
                    "JOIN walkthrough_inputs AS inputs USING (request_id) WHERE runs.token = ?",
                    (previous_token,),
                ).fetchone()
                if previous is None:
                    raise HTTPException(410, "This walkthrough conversation is no longer active.")
                self._require_current(previous)
                if previous["student"] != student or not previous["approval"]:
                    raise HTTPException(
                        409, "Continue with the same sender after approving the reply."
                    )
            previous_id = previous["request_id"] if previous is not None else None
            row = db.execute(
                "SELECT * FROM graph_runs WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row:
                self._require_current(row)
                if row["scenario"] != scenario:
                    raise HTTPException(409, "This run already uses a different example.")
                if scenario == "walkthrough":
                    saved = db.execute(
                        "SELECT student, email_body, previous_run FROM walkthrough_inputs "
                        "WHERE request_id = ?",
                        (request_id,),
                    ).fetchone()
                    if tuple(saved) != (student, email_body, previous_id):
                        raise HTTPException(409, "This run already uses a different email.")
                return {"token": row["token"], "scenario": scenario}
            if (
                previous is not None
                and db.execute(
                    "SELECT 1 FROM walkthrough_inputs WHERE previous_run = ?", (previous_id,)
                ).fetchone()
            ):
                raise HTTPException(409, "This conversation already has a follow-up.")
            if self.daily_run_limit is not None:
                count = db.execute(
                    "SELECT count(*) FROM graph_runs WHERE day = ?", (day,)
                ).fetchone()[0]
                if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'runs'").fetchone():
                    count += db.execute(
                        "SELECT count(*) FROM runs WHERE day = ?", (day,)
                    ).fetchone()[0]
                if count >= self.daily_run_limit:
                    raise HTTPException(
                        429, f"Today's {self.daily_run_limit} live demo runs are used."
                    )
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO graph_runs (request_id, token, scenario, day, created) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    request_id,
                    token,
                    scenario,
                    day,
                    previous["created"] if previous is not None else now,
                ),
            )
            if scenario == "walkthrough":
                prior = json.loads(previous["context"]) if previous is not None else None
                approval = json.loads(previous["approval"]) if previous is not None else {}
                reply = approval.get("body")
                prior_evidence = json.loads(previous["evidence"]) if previous is not None else ()
                offer = (
                    previous_offer(self.records, prior, reply, prior_evidence) if prior else None
                )
                context = self.records.walkthrough_context(
                    student,
                    request_id,
                    email_body,
                    prior=prior,
                    reply=reply,
                    prior_evidence=prior_evidence,
                )
                context["previous_trial_offer"] = offer
                context["trial_interest"] = bool(
                    context.get("trial_interest") or TRIAL.search(latest_text(email_body))
                )
                if approval.get("booking_kind") == "trial":
                    context.setdefault("simulated_trials", []).append(
                        approval["booking"]["session"]["id"]
                    )
                db.execute(
                    "INSERT INTO walkthrough_inputs (request_id, student, email_body, "
                    "previous_run, context) VALUES (?, ?, ?, ?, ?)",
                    (request_id, student, email_body, previous_id, json.dumps(context)),
                )
        return {"token": token, "scenario": scenario}

    def _require_current(self, row):
        now = self.clock()
        if now - row["created"] >= EXPIRES_IN or self._day(now) != row["day"]:
            raise HTTPException(410, "This demo run expired. Refresh to start again.")

    @contextmanager
    def _lease(self, token):
        now = self.clock()
        lease = secrets.token_hex(16)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM graph_runs WHERE token = ?", (token,)).fetchone()
            if row is None:
                raise HTTPException(
                    410, "This demo run is no longer active. Refresh to start again."
                )
            self._require_current(row)
            if row["busy_until"] > now:
                raise HTTPException(409, "This run is still processing. Retry shortly.")
            db.execute(
                "UPDATE graph_runs SET lease = ?, busy_until = ? WHERE token = ?",
                (lease, now + LEASE_SECONDS, token),
            )
        try:
            yield row
        finally:
            with self.db() as db:
                db.execute(
                    "UPDATE graph_runs SET lease = NULL, busy_until = 0 "
                    "WHERE token = ? AND lease = ?",
                    (token, lease),
                )

    def execute(self, token, stage, *, teacher_answers=(), revision=None, body=None):
        if stage not in {"evidence", "draft", "revise", "approve"}:
            raise ValueError("Invalid demo stage")
        with self._lease(token) as row:
            model = self.factory()
            store = DemoStore(self, row)
            config = {"configurable": {"thread_id": row["request_id"]}, "recursion_limit": 30}
            try:
                with self.checkpoints() as saver:
                    graph = Workflow(
                        None,
                        model,
                        store=store,
                        records=self.records,
                        evidence_review=evidence_questions,
                        draft_override=lambda state: trial_draft(self.records, state),
                        draft_transform=unsigned_demo_draft,
                    ).compile(saver)
                    return self._drive(graph, config, row, stage, teacher_answers, revision, body)
            except AdministrationError as error:
                raise HTTPException(error.status, error.message) from error
            except HTTPException:
                raise
            except Exception as error:
                # The durable checkpoint is retained for a stage retry after a model failure.
                raise HTTPException(
                    502, "The demo could not finish this step. Please retry."
                ) from error
            finally:
                client = getattr(model, "client", None)
                if client is not None:
                    client.close()

    def _drive(self, graph, config, row, stage, teacher_answers, revision, body):
        snapshot = graph.get_state(config)
        state = snapshot.values
        interrupts = [interrupt.value for task in snapshot.tasks for interrupt in task.interrupts]
        at_evidence = any(value.get("stage") == "evidence" for value in interrupts)
        if stage == "evidence":
            if (
                row["approval"]
                and (saved := json.loads(row["approval"])).get("booking_kind") == "trial"
            ):
                return self._automatic_trial_result(saved)
            if not at_evidence and not state.get("draft"):
                self._attempt(row, "evidence")
                graph.invoke(None if state else {"run_id": row["request_id"]}, config)
                state = graph.get_state(config).values
            questions = evidence_questions(state)
            if not questions and (proposal := trial_draft(self.records, state)) is not None:
                if not state.get("draft"):
                    self._drive(graph, config, row, "draft", (), None, None)
                    state = graph.get_state(config).values
                if proposal.references == state["draft"].get("references"):
                    trial_approval = self._drive(
                        graph, config, row, "approve", (), state["attempt"], proposal.body
                    )
                    return self._automatic_trial_result(trial_approval)
            return {
                "evidence": supporting_evidence(state),
                "missing_information": [item["label"] for item in questions],
                "review_requirements": review_requirements(
                    state.get("flow"),
                    state.get("interpretation", {}),
                    state.get("evidence", []),
                    state.get("draft"),
                    missing_teacher_information=bool(questions and not state.get("draft")),
                ),
                "model": self.model_name,
            }
        if stage == "draft":
            if not state or "evidence" not in state:
                raise HTTPException(409, "Find supporting evidence before generating a draft.")
            if row["teacher_answers"] is not None and json.loads(row["teacher_answers"]) != list(
                teacher_answers
            ):
                raise HTTPException(409, "Retry with the original teacher answers.")
            if not state.get("draft"):
                any_questions = evidence_questions(state)
                resolutions = self._resolutions(any_questions, teacher_answers)
                self._attempt(row, "draft", teacher_answers=teacher_answers)
                graph.invoke(Command(resume=resolutions) if at_evidence else None, config)
                state = graph.get_state(config).values
            elif snapshot.next and not interrupts and not state.get("decision"):
                graph.invoke(None, config)
                state = graph.get_state(config).values
            return self._draft_response(state)
        if stage == "revise":
            if not state.get("draft") or not any(
                "revision" in value and "draft" in value for value in interrupts
            ):
                raise HTTPException(409, "There is no draft awaiting teacher answers.")
            questions = draft_teacher_questions(state)
            answer_history = json.loads(row["revision_answers"] or "{}")
            if isinstance(answer_history, list):
                answer_history = {}
            submitted = list(teacher_answers)
            resolved_ids = {
                str(item["question_id"])
                for item in [
                    *(state.get("question_resolutions") or []),
                    *(state["draft"].get("question_resolutions") or []),
                ]
            }
            if revision is None:
                raise HTTPException(422, "Include the draft revision with the teacher answers.")
            if revision != state["attempt"]:
                previous_revision = answer_history.get(str(revision))
                if (
                    previous_revision is not None
                    and previous_revision.get("answers") == submitted
                    and set(previous_revision.get("question_ids", [])) <= resolved_ids
                ):
                    return self._draft_response(state)
                raise HTTPException(409, "These teacher answers belong to an older draft revision.")
            if not questions:
                raise HTTPException(409, "This draft has no unresolved teacher questions.")
            question_ids = [item["id"] for item in questions]
            revision_key = str(revision)
            saved_revision = answer_history.get(revision_key)
            if saved_revision is not None and (
                saved_revision.get("answers") != submitted
                or saved_revision.get("question_ids") != question_ids
            ):
                raise HTTPException(409, "Retry with the original teacher answers.")
            resolutions = self._resolutions(questions, teacher_answers)
            if saved_revision is None:
                if row["revision_attempts"] >= MAX_REVISION_ATTEMPTS:
                    raise HTTPException(429, "This step has reached its retry limit.")
                answer_history[revision_key] = {
                    "answers": submitted,
                    "question_ids": question_ids,
                }
                with self.db() as db:
                    db.execute(
                        "UPDATE graph_runs SET revision_attempts = revision_attempts + 1, "
                        "revision_answers = ? WHERE request_id = ?",
                        (json.dumps(answer_history), row["request_id"]),
                    )
            answered_ids = {
                str(item["question_id"])
                for item in state["draft"].get("question_resolutions") or []
            }
            if any(item["id"] not in answered_ids for item in questions):
                review = Review(
                    action="revise",
                    expected_revision=state["attempt"],
                    question_resolutions=resolutions,
                )
                graph.invoke(Command(resume=review.model_dump(mode="json")), config)
                state = graph.get_state(config).values
            return self._draft_response(state)
        if not state.get("draft") or revision != state.get("attempt"):
            raise HTTPException(409, "Approval must match the current draft revision.")
        approved_body = body if body is not None else state["draft"]["body"]
        decision = {"action": "approve", "expected_revision": revision, "body": approved_body}
        if row["decision"] and json.loads(row["decision"]) != decision:
            raise HTTPException(409, "An approval for this draft is already in progress.")
        if row["approval"]:
            return json.loads(row["approval"])
        store = DemoStore(self, row)
        # Prevent a publication between validation and the durable graph decision.
        with store.document_approval_guard(state):
            store.check_approval(state, approved_body)
            with self.db() as db:
                db.execute(
                    "UPDATE graph_runs SET decision = ? WHERE request_id = ?",
                    (json.dumps(decision), row["request_id"]),
                )
            if not interrupts and not state.get("decision"):
                graph.invoke(None, config)
                snapshot = graph.get_state(config)
                interrupts = [value for task in snapshot.tasks for value in task.interrupts]
            graph.invoke(Command(resume=decision) if interrupts else None, config)
            with self.db() as db:
                saved = db.execute(
                    "SELECT approval FROM graph_runs WHERE request_id = ?", (row["request_id"],)
                ).fetchone()[0]
            return json.loads(saved)

    def _automatic_trial_result(self, approval):
        session = approval["booking"]["session"]
        description = (
            f"{session['className']}, {session['date']} at {session['time']}, {session['location']}"
        )
        return {
            "evidence": [f"Verified trial: {description}."],
            "missing_information": [],
            "review_requirements": [],
            "automatic_approval": approval,
            "model": self.model_name,
        }

    def _draft_response(self, state):
        return {
            "body": state["draft"]["body"],
            "revision": state["attempt"],
            "booking_proposed": bool(state["draft"].get("booking_session_id")),
            "missing_information": [item["label"] for item in draft_teacher_questions(state)],
            "review_requirements": review_requirements(
                state.get("flow"), state["interpretation"], state["evidence"], state["draft"]
            ),
            "model": self.model_name,
        }

    def _attempt(self, row, stage, *, teacher_answers=None):
        field = f"{stage}_attempts"
        if row[field] >= MAX_ATTEMPTS:
            raise HTTPException(429, "This step has reached its retry limit.")
        with self.db() as db:
            db.execute(
                f"UPDATE graph_runs SET {field} = {field} + 1, "
                "teacher_answers = COALESCE(teacher_answers, ?) WHERE request_id = ?",
                (
                    json.dumps(teacher_answers) if teacher_answers is not None else None,
                    row["request_id"],
                ),
            )

    @staticmethod
    def _resolutions(questions, answers):
        if len(answers) != len(questions) or any(not a.strip() or len(a) > 2000 for a in answers):
            raise HTTPException(422, "Enter one answer or deferral for each question.")
        return [
            {
                "question_id": question["id"],
                "decision": "defer"
                if answer == "I will confirm this information later."
                else "answer",
                "answer": None if answer == "I will confirm this information later." else answer,
            }
            for question, answer in zip(questions, answers, strict=True)
        ]


def draft_teacher_questions(state):
    """Return unresolved teacher decisions from the shared graph's draft checklist."""
    draft = state.get("draft") or {}
    required = set(draft.get("required_question_ids") or [])
    required.update(
        str(answer["question_id"])
        for answer in draft.get("answers", [])
        if answer.get("status") == "needs_teacher" and answer.get("question_id")
    )
    resolved = {str(item["question_id"]) for item in draft.get("question_resolutions") or []}
    labels = {
        str(answer["question_id"]): answer["question"]
        for answer in draft.get("answers", [])
        if answer.get("question_id")
    }
    labels.update(
        {
            str(question_id): question
            for question, question_id in state.get("interpretation", {})
            .get("question_ids", {})
            .items()
        }
    )
    return [
        {"id": question_id, "label": labels.get(question_id, "Teacher information")}
        for question_id in sorted(required - resolved)
    ]


class DemoStore:
    """Shared graph persistence interface, scoped to one fictional run."""

    def __init__(self, demo, row):
        self.demo, self.row = demo, row

    def load_context(self, run_id):
        if self.row["scenario"] != "walkthrough":
            return {**self.demo.records.context(self.row["scenario"]), "public_demo": True}
        with self.demo.db() as db:
            result = db.execute(
                "SELECT context FROM walkthrough_inputs WHERE request_id = ?", (run_id,)
            ).fetchone()
        return {**json.loads(result["context"]), "public_demo": True}

    def save_routing(self, run_id, routing, flow):
        pass

    def remember_student(self, run_id, interpretation, routing, flow):
        data = {**interpretation.model_dump(mode="json"), "flow": flow}
        with self.demo.db() as db:
            db.execute(
                "UPDATE graph_runs SET interpretation = ? WHERE request_id = ?",
                (json.dumps(data), run_id),
            )

    def save_revision_interpretation(self, run_id, interpretation):
        prior = json.loads(self.row["interpretation"] or "{}")
        data = {**interpretation.model_dump(mode="json"), "flow": prior.get("flow", "enquiry")}
        with self.demo.db() as db:
            db.execute(
                "UPDATE graph_runs SET interpretation = ? WHERE request_id = ?",
                (json.dumps(data), run_id),
            )

    def save_draft(self, run_id, attempt, draft, evidence, warnings):
        with self.demo.db() as db:
            db.execute(
                "UPDATE graph_runs SET revision = ?, draft = ?, evidence = ? WHERE request_id = ?",
                (attempt, json.dumps(draft), json.dumps(evidence), run_id),
            )

    @contextmanager
    def document_approval_guard(self, state):
        references = state["draft"].get("references") or []
        if not any(ref.startswith(("document:", "public-document:")) for ref in references):
            yield
            return
        from sqlalchemy import text

        from studio_copilot.public_demo import document_index

        engine = None
        try:
            engine = document_index.engine_from_env()
            with engine.begin() as connection:
                # Index publication takes the exclusive form of this lock. Keep the
                # shared lock until the SQLite approval is committed.
                connection.execute(text("SELECT pg_advisory_xact_lock_shared(582910743)"))
                yield
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                409, "The demo document sources changed or are unavailable. Regenerate the draft."
            ) from error
        finally:
            if engine is not None:
                engine.dispose()

    def check_approval(self, state, body):
        draft = state["draft"]
        require_resolved_questions(
            SimpleNamespace(
                interpretation={**state["interpretation"], "flow": state["flow"]},
                draft_details=draft,
                evidence=state["evidence"],
            )
        )
        references = draft.get("references") or []
        if any(ref.startswith(("document:", "public-document:")) for ref in references):
            from sqlalchemy.orm import Session

            from studio_copilot.documents import online
            from studio_copilot.public_demo import document_index

            engine = None
            try:
                engine = document_index.engine_from_env()
                config = document_index.configuration(engine)
                sources = [
                    source
                    for item in state["evidence"]
                    if item.get("tool") == "document_answer"
                    for source in item["result"].get("sources", [])
                ]
                if not sources or any(ref.startswith("public-document:") for ref in references):
                    raise online.OnlineError("source_changed")
                as_of = (
                    datetime.fromisoformat(state["context"]["source"]["occurred_at"])
                    .astimezone(ZoneInfo("Australia/Melbourne"))
                    .date()
                )
                with Session(engine) as db:
                    online.check_identities(db, config, sources, as_of)
            except Exception as error:
                raise HTTPException(
                    409,
                    "The demo document sources changed or are unavailable. Regenerate the draft.",
                ) from error
            finally:
                if engine is not None:
                    engine.dispose()
        if any(ref.startswith("public-trial:") for ref in references):
            trial = trial_draft(self.demo.records, state)
            if trial is None or trial.references != references or body != trial.body:
                raise HTTPException(409, "The verified trial session or confirmation changed.")
            return trial.references[0].removeprefix("public-trial:")
        proposal = draft.get("booking_session_id")
        if not proposal:
            return
        if body != draft["body"]:
            raise HTTPException(409, "The proposed booking wording must match the reviewed draft.")
        if UUID(proposal) not in validated_candidate_ids(state["evidence"]):
            raise HTTPException(409, "The proposed booking has no verified session.")
        refreshed = self.demo.records.makeup(state)
        if UUID(proposal) not in validated_candidate_ids(refreshed["evidence"]):
            raise HTTPException(409, "The fictional session is no longer eligible.")

    def approve(self, run_id, body):
        response_id = str(uuid5(UUID(run_id), "demo-teacher-response"))
        with self.demo.db() as db:
            row = db.execute("SELECT * FROM graph_runs WHERE request_id = ?", (run_id,)).fetchone()
            draft = json.loads(row["draft"])
            interpretation = json.loads(row["interpretation"])
            state = {
                "run_id": run_id,
                "draft": draft,
                "evidence": json.loads(row["evidence"]),
                "interpretation": interpretation,
                "flow": interpretation["flow"],
                "context": self.load_context(run_id),
            }
            if row["approval"] is None:
                with self.document_approval_guard(state):
                    trial_id = self.check_approval(state, body)
                    proposal = draft.get("booking_session_id")
                    approval = {
                        "status": "approved_mock",
                        "revision": row["revision"],
                        "body": body,
                        "booking_simulated": bool(trial_id or proposal),
                    }
                    if trial_id or proposal:
                        approval["booking_kind"] = "trial" if trial_id else "makeup"
                        approval["booking"] = self._booking(
                            trial_id or proposal, state["context"]["student"]
                        )
                    db.execute(
                        "UPDATE graph_runs SET approval = ? WHERE request_id = ?",
                        (json.dumps(approval), run_id),
                    )
                    db.commit()
        return response_id

    def _booking(self, session_id, student):
        records = self.demo.records
        session = records.session(session_id)
        local = session.starts_at.astimezone(ZoneInfo(session.regular_class.location.timezone))
        return {
            "student": {"id": student["id"], "name": student["name"]},
            "session": {
                "id": session_id,
                "className": session.regular_class.name,
                "date": f"{local:%A} {local.day} {local:%B %Y}",
                "time": local.strftime("%I:%M %p").lstrip("0").replace(":00", "").lower(),
                "location": session.regular_class.location.name,
                "capacity": session.capacity,
                "students": [
                    {"id": row["id"], "name": row["display_name"]}
                    for row in records.students.values()
                    if UUID(row["id"]) in session.students
                ],
            },
        }

    def approved_response(self, run_id):
        with self.demo.db() as db:
            return json.loads(
                db.execute(
                    "SELECT approval FROM graph_runs WHERE request_id = ?", (run_id,)
                ).fetchone()[0]
            )["body"]

    def approved_booking(self, run_id):
        # A simulated approval is never a confirmed booking in student memory.
        return None

    def remember_approval(self, run_id, memory):
        pass
