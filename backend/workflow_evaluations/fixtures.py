"""Disposable synthetic studio data; never use the application's configured database."""

from contextlib import contextmanager
from datetime import datetime, time, timedelta
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
    SessionAttendance,
    Student,
    StudioClass,
    Term,
)

from .cases import ScenarioSetup

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


def seed_studio(engine, fixture: str, setup: ScenarioSetup | None = None) -> dict:
    setup = setup or ScenarioSetup(
        student={"highest_level": "Level 2"},
        enrolments=[] if fixture == "no_enrolments" else [{"class_key": "monday_level_2"}],
        session_rosters={
            "absence": ["student"],
            "thursday": ["other_student"] if fixture == "full" else [],
            "saturday": ["other_student"] if fixture == "full" else [],
        },
    )
    zone = ZoneInfo("Australia/Melbourne")
    now = datetime.now(zone)
    # Next week's Monday keeps all candidate sessions in the future without clock patches.
    monday = now.date() + timedelta(days=7 - now.weekday())
    absence = (
        now.date() - timedelta(days=now.weekday() or 7)
        if fixture in {"late_notice", "past_absence"}
        else monday
    )
    dates = {
        "absence_date": absence.isoformat(),
        "thursday_date": (monday + timedelta(days=3)).isoformat(),
        "saturday_date": (monday + timedelta(days=5)).isoformat(),
    }
    # Sender locks are database-wide, so schema isolation alone is insufficient.
    identity = uuid4().hex
    known_sender = f"alex-{identity}@example.com"
    new_sender = f"new-{identity}@example.com"
    with Session(engine) as db, db.begin():
        student = Student(
            display_name="Synthetic Alex",
            email=known_sender,
            highest_level=setup.student.highest_level,
            context={"staff_note": "Synthetic evaluation fixture"},
        )
        canary = Student(display_name=CANARY, email="private-canary@example.com")
        term = Term(
            name="Synthetic term",
            starts_on=now.date() - timedelta(days=30),
            ends_on=monday + timedelta(days=30),
        )
        location = Location(
            name="Synthetic Studio A", address="100 Fictional Lane", timezone="Australia/Melbourne"
        )
        db.add_all([student, canary, term, location])
        db.flush()
        private = Conversation(student=canary)
        db.add(Message(conversation=private, kind="student_email", body=CANARY))
        ids = {}
        for key, name, day in [
            ("absence", "Monday Level 2", absence),
            ("thursday", "Thursday Level 2", monday + timedelta(days=3)),
            ("saturday", "Saturday Level 2", monday + timedelta(days=5)),
        ]:
            level = {
                "absence": "Level 2",
                "thursday": setup.thursday_level,
                "saturday": setup.saturday_level,
            }[key]
            cls = StudioClass(
                name=name.replace("Level 2", level), level=level, term=term, location=location
            )
            db.add(cls)
            db.flush()
            class_key = "monday_level_2" if key == "absence" else key + "_level_2"
            for enrolment in setup.enrolments:
                if enrolment.class_key == class_key:
                    db.add(
                        Enrolment(
                            student=student,
                            regular_class=cls,
                            starts_on=term.starts_on,
                            status=enrolment.status,
                        )
                    )
            if fixture == "no_sessions" and key != "absence":
                continue
            start = datetime.combine(day, time(18), zone)
            session = ClassSession(
                regular_class=cls,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                capacity=1,
                students=[
                    student.id if member == "student" else canary.id
                    for member in setup.session_rosters.get(key, [])
                ],
            )
            db.add(session)
            db.flush()
            ids[key] = str(session.id)
            if key == "absence" and setup.absence_attendance != "unknown":
                db.add(
                    SessionAttendance(
                        session_id=session.id,
                        student_id=student.id,
                        status=setup.absence_attendance,
                        level_at_attendance=level,
                    )
                )
        if setup.conflicting_booking is not None:
            conflict_class = StudioClass(
                name=setup.conflicting_booking.class_name,
                level="Level 2",
                term=term,
                location=location,
            )
            db.add(conflict_class)
            db.flush()
            conflict_start = datetime.combine(
                monday + timedelta(days=3), time(18), zone
            ) + timedelta(minutes=setup.conflicting_booking.start_offset_minutes)
            conflict_session = ClassSession(
                regular_class=conflict_class,
                starts_at=conflict_start,
                ends_at=conflict_start
                + timedelta(minutes=setup.conflicting_booking.duration_minutes),
                capacity=2,
                students=[student.id],
            )
            db.add(conflict_session)
            db.flush()
            ids["conflicting_booking"] = str(conflict_session.id)
        if setup.attended_level is not None:
            historical_class = StudioClass(
                name="Historical attended class",
                level=setup.attended_level,
                term=term,
                location=location,
            )
            db.add(historical_class)
            db.flush()
            historical_start = now - timedelta(days=14)
            historical = ClassSession(
                regular_class=historical_class,
                starts_at=historical_start,
                ends_at=historical_start + timedelta(hours=1),
                capacity=2,
                students=[student.id],
            )
            db.add(historical)
            db.flush()
            db.add(
                SessionAttendance(
                    session_id=historical.id,
                    student_id=student.id,
                    status="attended",
                    level_at_attendance=setup.attended_level,
                )
            )
        return {
            "reference_at": now.isoformat(),
            "setup": setup.model_dump(mode="json"),
            "dates": dates,
            "sessions": ids,
            "student_id": str(student.id),
            "canary_id": str(canary.id),
            "known_sender": known_sender,
            "new_sender": new_sender,
        }
