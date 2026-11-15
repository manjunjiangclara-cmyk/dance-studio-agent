"""Persistent admission and bounded stage execution in a separate SQLite ledger.

A shared local file serializes all processes of the demo service. No application database
or LangGraph checkpoints are accessed. Multi-host replicas require a single demo service.
"""

import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from studio_copilot.public_demo.model import DemoModel

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
            for column in ("student", "email_body"):
                if column not in columns:
                    db.execute(f"ALTER TABLE runs ADD COLUMN {column} TEXT")
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
                student not in {"alex", "jules"}
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

    def execute(self, token, stage):
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
            if row[stage]:
                return json.loads(row[stage])
            if row["busy_until"] > now:
                raise HTTPException(409, "This demo is processing. Wait before retrying.")
            if stage == "draft" and not row["evidence"]:
                raise HTTPException(409, "Find supporting evidence before generating a draft.")
            if row[f"{stage}_attempts"] >= 2:
                raise HTTPException(
                    429, "This step's two attempts are used. Please try another example later."
                )
            db.execute(
                f"UPDATE runs SET {stage}_attempts = {stage}_attempts + 1, "
                "busy_until = ?, lease = ? WHERE token = ?",
                (now + 60, lease, token),
            )
            scenario = row["scenario"]
            evidence = json.loads(row["evidence"])["evidence"] if row["evidence"] else []
        model = None
        try:
            model = self.factory()
            if scenario == "custom":
                result = model.call(
                    scenario,
                    stage,
                    evidence,
                    context={"student": row["student"], "email_body": row["email_body"]},
                )
            else:
                result = model.call(scenario, stage, evidence)
            with self.db() as db:
                saved = db.execute(
                    f"UPDATE runs SET {stage} = ?, busy_until = 0, lease = NULL "
                    "WHERE token = ? AND lease = ?",
                    (json.dumps(result), token, lease),
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
