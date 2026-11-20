"""Persistent admission and bounded stage execution in a separate SQLite ledger.

A shared local file serializes all processes of the demo service. No application database
or LangGraph checkpoints are accessed. Multi-host replicas require a single demo service.
"""

import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from studio_copilot.public_demo.fixtures import CUSTOM_STUDENTS
from studio_copilot.public_demo.model import DemoModel
from studio_copilot.public_demo.trial import initial_state, strip_quotes, update_state

DAILY_RUN_LIMIT = 20


class PublicDemo:
    def __init__(self, path, *, factory=DemoModel, clock=time.time):
        self.path, self.factory, self.clock = str(path), factory, clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS runs (
                request_id TEXT PRIMARY KEY, token TEXT UNIQUE NOT NULL,
                scenario TEXT NOT NULL, day TEXT NOT NULL, created REAL NOT NULL,
                evidence TEXT, draft TEXT, evidence_attempts INTEGER NOT NULL DEFAULT 0,
                draft_attempts INTEGER NOT NULL DEFAULT 0, busy_until REAL NOT NULL DEFAULT 0,
                lease TEXT
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(runs)")}
            for column in ("student", "email_body", "draft_answers"):
                if column not in columns:
                    db.execute(f"ALTER TABLE runs ADD COLUMN {column} TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS threads (
                token TEXT PRIMARY KEY, student TEXT NOT NULL, created REAL NOT NULL,
                day TEXT NOT NULL, state TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS turns (
                request_id TEXT PRIMARY KEY REFERENCES runs(request_id),
                thread_token TEXT NOT NULL REFERENCES threads(token),
                original_body TEXT NOT NULL, accepted_reply TEXT
            )""")
            turn_columns = {row["name"] for row in db.execute("PRAGMA table_info(turns)")}
            if "offer_confirmed" not in turn_columns:
                db.execute(
                    "ALTER TABLE turns ADD COLUMN offer_confirmed INTEGER NOT NULL DEFAULT 0"
                )
        Path(path).chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, scenario, request_id, *, student=None, email_body=None):
        if scenario == "custom":
            if (
                student not in CUSTOM_STUDENTS
                or not isinstance(email_body, str)
                or not email_body.strip()
                or len(email_body) > 2000
            ):
                raise HTTPException(
                    422, "Select a fictional student and write up to 2,000 characters."
                )
        elif (
            scenario not in {"booking", "document"} or student is not None or email_body is not None
        ):
            raise HTTPException(422, "Unsupported demo input.")
        now = self.clock()
        day = datetime.fromtimestamp(now, ZoneInfo("Australia/Melbourne")).date().isoformat()
        with self.db() as db:
            db.execute("DELETE FROM runs WHERE created < ?", (now - 3 * 86400,))
            existing = db.execute(
                "SELECT * FROM runs WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                if existing["student"] != student or existing["email_body"] != email_body:
                    raise HTTPException(409, "This request already belongs to a different email.")
                if (
                    existing["scenario"] != scenario
                    or now - existing["created"] > 3600
                    or existing["day"] != day
                ):
                    raise HTTPException(410, "This demo run expired. Restart the demo.")
                return {"token": existing["token"], "scenario": scenario}
            if (
                db.execute("SELECT count(*) FROM runs WHERE day = ?", (day,)).fetchone()[0]
                >= DAILY_RUN_LIMIT
            ):
                raise HTTPException(
                    429,
                    f"Today's {DAILY_RUN_LIMIT} live demo runs are used. Please return tomorrow.",
                )
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO runs (request_id, token, scenario, day, created, student, email_body) "
                "VALUES (?,?,?,?,?,?,?)",
                (request_id, token, scenario, day, now, student, email_body),
            )
        return {"token": token, "scenario": scenario}

    def create_thread(self, student):
        if student not in CUSTOM_STUDENTS:
            raise HTTPException(422, "Select a fictional student.")
        now = self.clock()
        day = datetime.fromtimestamp(now, ZoneInfo("Australia/Melbourne")).date().isoformat()
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute(
                "DELETE FROM turns WHERE thread_token IN "
                "(SELECT token FROM threads WHERE created < ?)",
                (now - 3 * 86400,),
            )
            db.execute("DELETE FROM threads WHERE created < ?", (now - 3 * 86400,))
            db.execute("DELETE FROM runs WHERE created < ?", (now - 3 * 86400,))
            db.execute(
                "INSERT INTO threads VALUES (?,?,?,?,?)",
                (token, student, now, day, json.dumps(initial_state())),
            )
        return {"token": token}

    def _thread(self, db, token):
        row = db.execute("SELECT * FROM threads WHERE token = ?", (token,)).fetchone()
        if not row:
            raise HTTPException(404, "Conversation not found.")
        now = self.clock()
        day = datetime.fromtimestamp(now, ZoneInfo("Australia/Melbourne")).date().isoformat()
        if now - row["created"] > 3600 or row["day"] != day:
            raise HTTPException(410, "This conversation expired. Start a new one.")
        return row

    def thread_view(self, token):
        with self.db() as db:
            thread = self._thread(db, token)
            rows = db.execute(
                """SELECT t.request_id, t.original_body, t.accepted_reply,
                r.evidence, r.draft, r.draft_answers FROM turns t
                JOIN runs r ON r.request_id=t.request_id
                WHERE t.thread_token=? ORDER BY r.rowid""",
                (token,),
            ).fetchall()
            return {
                "student": thread["student"],
                "state": json.loads(thread["state"]),
                "turns": [
                    {
                        "request_id": r["request_id"],
                        "email": r["original_body"],
                        "reply": r["accepted_reply"],
                        "evidence": json.loads(r["evidence"]) if r["evidence"] else None,
                        "draft": json.loads(r["draft"]) if r["draft"] else None,
                        "draft_answers": json.loads(r["draft_answers"])
                        if r["draft_answers"] is not None
                        else None,
                    }
                    for r in rows
                ],
            }

    def add_turn(self, token, request_id, body):
        clean = strip_quotes(body)
        if not clean or len(body) > 2000:
            raise HTTPException(422, "Write up to 2,000 characters of new email text.")
        now = self.clock()
        with self.db() as db:
            thread = self._thread(db, token)
            existing = db.execute(
                "SELECT * FROM turns WHERE request_id=?", (request_id,)
            ).fetchone()
            if existing:
                if existing["thread_token"] != token or existing["original_body"] != body:
                    raise HTTPException(409, "This request belongs to another email.")
                return {"request_id": request_id}
            if db.execute("SELECT 1 FROM runs WHERE request_id=?", (request_id,)).fetchone():
                raise HTTPException(409, "This request belongs to another run.")
            pending = db.execute(
                "SELECT count(*) FROM turns WHERE thread_token=? AND accepted_reply IS NULL",
                (token,),
            ).fetchone()[0]
            if pending:
                raise HTTPException(409, "Accept the previous reply before adding another email.")
            if (
                db.execute("SELECT count(*) FROM turns WHERE thread_token=?", (token,)).fetchone()[
                    0
                ]
                >= 10
            ):
                raise HTTPException(429, "This conversation has reached its ten-email limit.")
            if (
                db.execute("SELECT count(*) FROM runs WHERE day=?", (thread["day"],)).fetchone()[0]
                >= DAILY_RUN_LIMIT
            ):
                raise HTTPException(
                    429,
                    f"Today's {DAILY_RUN_LIMIT} live demo runs are used. Please return tomorrow.",
                )
            run_token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO runs (request_id, token, scenario, day, created, student, email_body) "
                "VALUES (?,?,?,?,?,?,?)",
                (request_id, run_token, "custom", thread["day"], now, thread["student"], clean),
            )
            db.execute(
                "INSERT INTO turns (request_id, thread_token, original_body) VALUES (?,?,?)",
                (request_id, token, body),
            )
        return {"request_id": request_id}

    def thread_execute(self, token, request_id, stage, *, teacher_answers=None):
        with self.db() as db:
            self._thread(db, token)
            row = db.execute(
                "SELECT r.token FROM turns t JOIN runs r ON r.request_id=t.request_id "
                "WHERE t.thread_token=? AND t.request_id=?",
                (token, request_id),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Email not found.")
            run_token = row["token"]
        return self.execute(run_token, stage, teacher_answers=teacher_answers)

    def accept_reply(self, token, request_id, reply, offer_confirmed=False):
        if not reply.strip() or len(reply) > 5000:
            raise HTTPException(422, "A reply of up to 5,000 characters is required.")
        with self.db() as db:
            thread = self._thread(db, token)
            row = db.execute(
                "SELECT t.accepted_reply, t.offer_confirmed, r.draft FROM turns t JOIN runs r "
                "ON r.request_id=t.request_id WHERE t.thread_token=? AND t.request_id=?",
                (token, request_id),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Email not found.")
            if not row["draft"]:
                raise HTTPException(409, "Generate a draft first.")
            if row["accepted_reply"] is not None:
                if (
                    row["accepted_reply"] != reply
                    or bool(row["offer_confirmed"]) != offer_confirmed
                ):
                    raise HTTPException(409, "This reply has already been accepted.")
                return {"accepted": True}
            if offer_confirmed and json.loads(thread["state"])["booking_status"] != "offered":
                raise HTTPException(409, "There is no class offer to confirm.")
            db.execute(
                "UPDATE turns SET accepted_reply=?, offer_confirmed=? WHERE request_id=?",
                (reply, int(offer_confirmed), request_id),
            )
        return {"accepted": True}

    def approve_mock(self, token, revision):
        with self.db() as db:
            row = self._thread(db, token)
            state = json.loads(row["state"])
            if state["revision"] != revision:
                raise HTTPException(409, "The proposal has changed; review it again.")
            if state["booking_status"] == "approved_mock":
                return {"state": state}
            if state["booking_status"] != "awaiting_approval":
                raise HTTPException(409, "No trial request is ready for approval.")
            if db.execute(
                "SELECT 1 FROM turns WHERE thread_token=? AND accepted_reply IS NULL", (token,)
            ).fetchone():
                raise HTTPException(409, "Accept the draft before approving the request.")
            state.update(booking_status="approved_mock", next_action="complete")
            db.execute("UPDATE threads SET state=? WHERE token=?", (json.dumps(state), token))
            return {"state": state}

    def execute(self, token, stage, *, teacher_answers=None):
        now = self.clock()
        lease = secrets.token_hex(16)
        # stage is a server-owned literal from separate endpoint functions, never user SQL.
        if stage not in {"evidence", "draft"}:
            raise ValueError("Unknown stage")
        with self.db() as db:
            row = db.execute("SELECT * FROM runs WHERE token = ?", (token,)).fetchone()
            if row is None:
                raise HTTPException(404, "Demo run not found.")
            day = datetime.fromtimestamp(now, ZoneInfo("Australia/Melbourne")).date().isoformat()
            if now - row["created"] > 3600 or row["day"] != day:
                raise HTTPException(410, "This demo run expired. Restart the demo.")
            if stage == "draft" and not row["evidence"]:
                raise HTTPException(409, "Find supporting evidence before generating a draft.")
            answers = teacher_answers or []
            if stage == "draft":
                missing = (
                    ["Trial fee"]
                    if row["scenario"] == "document"
                    else json.loads(row["evidence"]).get("missing_information", [])
                    if row["scenario"] == "custom" and row["evidence"]
                    else []
                )
                if len(answers) != len(missing) or any(
                    not isinstance(answer, str) or not answer.strip() or len(answer) > 2000
                    for answer in answers
                ):
                    raise HTTPException(
                        422, "Provide a response for each missing item before generating."
                    )
                answers = [answer.strip() for answer in answers]
                encoded_answers = json.dumps(answers, ensure_ascii=False)
                if row["draft_answers"] is not None and row["draft_answers"] != encoded_answers:
                    raise HTTPException(
                        409,
                        "This draft attempt already has different teacher responses. "
                        "Start a new run.",
                    )
            if row[stage]:
                return json.loads(row[stage])
            if row["busy_until"] > now:
                raise HTTPException(409, "This demo is processing. Wait before retrying.")
            if row[f"{stage}_attempts"] >= 2:
                raise HTTPException(
                    429, "This step's two attempts are used. Please try another example later."
                )
            db.execute(
                f"UPDATE runs SET {stage}_attempts = {stage}_attempts + 1, "
                "busy_until = ?, lease = ? WHERE token = ?",
                (now + 60, lease, token),
            )
            if stage == "draft":
                db.execute(
                    "UPDATE runs SET draft_answers = ? WHERE token = ?", (encoded_answers, token)
                )
            thread_info = db.execute(
                """SELECT t.thread_token, th.state FROM turns t
                JOIN threads th ON th.token=t.thread_token WHERE t.request_id=?""",
                (row["request_id"],),
            ).fetchone()
            thread_context = {}
            if thread_info:
                self._thread(db, thread_info["thread_token"])
                history = db.execute(
                    """SELECT r.email_body, t.accepted_reply, t.offer_confirmed FROM turns t
                    JOIN runs r ON r.request_id=t.request_id WHERE t.thread_token=?
                    AND t.accepted_reply IS NOT NULL
                    ORDER BY r.rowid""",
                    (thread_info["thread_token"],),
                ).fetchall()
                thread_context = {
                    "thread_history": [
                        {"email": h["email_body"], "reply": h["accepted_reply"]} for h in history
                    ],
                    "workflow_state": json.loads(thread_info["state"]),
                }
            scenario = row["scenario"]
            evidence_result = json.loads(row["evidence"]) if row["evidence"] else {}
            evidence = evidence_result.get("evidence", [])
        model = None
        try:
            model = self.factory()
            if scenario == "custom":
                result = model.call(
                    scenario,
                    stage,
                    evidence,
                    context={
                        "student": row["student"],
                        "email_body": row["email_body"],
                        **thread_context,
                        **(
                            {"student_information": evidence_result["student_information"]}
                            if stage == "draft" and evidence_result.get("student_information")
                            else {}
                        ),
                        **(
                            {"teacher_answers": list(zip(missing, answers))}
                            if stage == "draft" and missing
                            else {}
                        ),
                    },
                )
            elif scenario == "document" and stage == "draft":
                result = model.call(
                    scenario,
                    stage,
                    evidence,
                    context={"teacher_answers": list(zip(missing, answers))},
                )
            else:
                result = model.call(scenario, stage, evidence)
            if thread_info and stage == "evidence":
                state = update_state(
                    json.loads(thread_info["state"]),
                    result.get("workflow_extraction", {}),
                    row["email_body"],
                    bool(history[-1]["offer_confirmed"]) if history else False,
                )
                patterns = {
                    "experience_level": r"experience|level",
                    "preferred_day": r"day|availability",
                    "customer_name": r"name",
                }
                information = result.get("student_information", [])
                information = [
                    item
                    for item in information
                    if not any(
                        state.get(field) and re.search(pattern, item, re.I)
                        for field, pattern in patterns.items()
                    )
                ]
                labels = {
                    "experience_level": "Dance experience",
                    "preferred_day": "Preferred day",
                    "customer_name": "Customer name",
                }
                for field in state["missing_information"]:
                    if not any(re.search(patterns[field], item, re.I) for item in information):
                        information.append(labels[field])
                result["student_information"] = information
            with self.db() as db:
                saved = db.execute(
                    f"UPDATE runs SET {stage} = ?, busy_until = 0, lease = NULL "
                    "WHERE token = ? AND lease = ?",
                    (json.dumps(result), token, lease),
                )
                if saved.rowcount == 1 and thread_info and stage == "evidence":
                    db.execute(
                        "UPDATE threads SET state=? WHERE token=?",
                        (json.dumps(state), thread_info["thread_token"]),
                    )
                if saved.rowcount != 1:
                    raise HTTPException(
                        409, "This attempt was superseded. Retry to load its result."
                    )
            return result
        except HTTPException:
            raise
        except Exception as error:
            # Attempts are never refunded, including timeouts, refusals and invalid output.
            with self.db() as db:
                db.execute(
                    "UPDATE runs SET busy_until = 0, lease = NULL WHERE token = ? AND lease = ?",
                    (token, lease),
                )
            raise HTTPException(
                502, "The live AI step could not complete. You can retry once."
            ) from error
        finally:
            if model is not None:
                try:
                    model.close()
                except Exception:
                    pass
