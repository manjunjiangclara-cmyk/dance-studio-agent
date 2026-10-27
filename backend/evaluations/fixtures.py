"""Disposable synthetic studio data; never use the application's configured database."""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.persistence.models import (
    ClassSession,
    Conversation,
    Enrolment,
    Location,
    Message,
    Student,
    StudioClass,
    Term,
)

from .cases import CATALOG, Setup, render

BACKEND = Path(__file__).resolve().parents[1]
CANARY = "PRIVATE_CANARY_8491"


def validate_database_url(url: str | None) -> str:
    if not url:
        raise ValueError(
            "Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test."
        )
    try:
        parsed = make_url(url)
    except ArgumentError:
        raise ValueError("The evaluation database URL is invalid.") from None
    if parsed.drivername != "postgresql+psycopg" or not (parsed.database or "").endswith("_test"):
        raise ValueError("Evaluations require postgresql+psycopg and a database ending in _test.")
    if parsed.query:
        raise ValueError("Evaluation database URLs must not contain connection-option overrides.")
    return url


@contextmanager
def isolated_database(url: str):
    validate_database_url(url)
    schema = "eval_" + uuid4().hex
    admin = create_engine(url)
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    created = False
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        with engine.begin() as connection:
            config = Config(str(BACKEND / "alembic.ini"))
            config.set_main_option("script_location", str(BACKEND / "migrations"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with postgres_checkpointer(engine) as saver:
            saver.setup()
        yield engine
    finally:
        engine.dispose()
        try:
            if created:
                with admin.begin() as connection:
                    connection.execute(DropSchema(schema, cascade=True))
        finally:
            admin.dispose()


def seed_studio(engine, setup: Setup) -> dict:
    catalog = json.loads(CATALOG.read_text())
    zone = ZoneInfo(catalog["location"]["timezone"])
    now = datetime.now(zone)
    monday = now.date() + timedelta(days=7 - now.weekday())
    absence = now.date() - timedelta(days=now.weekday() or 7) if setup.absence_in_past else monday
    dates = {
        "absence_date": absence.isoformat(),
        "thursday_date": (monday + timedelta(days=3)).isoformat(),
        "saturday_date": (monday + timedelta(days=5)).isoformat(),
        "term_start": (now.date() - timedelta(days=30)).isoformat(),
        "term_end": (monday + timedelta(days=30)).isoformat(),
        "yesterday": (now.date() - timedelta(days=1)).isoformat(),
    }
    identity = uuid4().hex
    sender = f"eval-{identity}@example.com"
    with Session(engine) as db, db.begin():
        student = None
        if setup.student.registered:
            student = Student(
                display_name="Synthetic Alex",
                email=sender,
                highest_level=setup.student.highest_level,
                context={"staff_note": "Synthetic evaluation fixture"},
            )
            db.add(student)
        canary = Student(display_name=CANARY, email="private-canary@example.com")
        term = Term(name="Synthetic term", starts_on=dates["term_start"], ends_on=dates["term_end"])
        location = Location(**catalog["location"])
        db.add_all([canary, term, location])
        db.flush()
        db.add(
            Message(conversation=Conversation(student=canary), kind="student_email", body=CANARY)
        )
        classes = {}
        for key, details in catalog["classes"].items():
            cls = StudioClass(**details, term=term, location=location)
            db.add(cls)
            db.flush()
            classes[key] = cls
        for enrolment in setup.enrolments:
            resolved = render(enrolment.model_dump(), dates)
            db.add(
                Enrolment(
                    student=student, regular_class=classes[resolved.pop("class_key")], **resolved
                )
            )
        sessions = {}
        for key in setup.sessions:
            details = render(catalog["sessions"][key], dates)
            session = ClassSession(
                regular_class=classes[details["class_key"]],
                starts_at=datetime.fromisoformat(
                    details["date"] + "T" + details["starts_at"]
                ).replace(tzinfo=zone),
                ends_at=datetime.fromisoformat(details["date"] + "T" + details["ends_at"]).replace(
                    tzinfo=zone
                ),
                capacity=details["capacity"],
            )
            db.add(session)
            db.flush()
            sessions[key] = str(session.id)
            if key in setup.full_sessions:
                db.add(
                    Enrolment(
                        student=canary,
                        regular_class=classes[details["class_key"]],
                        starts_on=term.starts_on,
                        status="active",
                    )
                )
        return {
            "reference_at": now.isoformat(),
            "dates": dates,
            "sender": sender,
            "student_id": str(student.id) if student else None,
            "canary_id": str(canary.id),
            "sessions": sessions,
            "catalog": render(catalog, dates),
            "setup": render(setup.model_dump(), dates),
        }
