from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.api.schemas import IncomingEmail
from studio_copilot.demo import demo_id, repair_demo_message_dates, seed_demo
from studio_copilot.persistence.models import (
    ClassSession,
    Location,
    Message,
    Student,
    StudioClass,
    Term,
)

pytestmark = pytest.mark.integration


def test_demo_seed_is_repeatable_and_preserves_edits(db_engine):
    with Session(db_engine) as db, db.begin():
        result = seed_demo(db)
        assert result["created"]
    with Session(db_engine) as db, db.begin():
        alex = db.get(Student, result["ids"]["alex"])
        alex.highest_level = "Staff corrected level"
    with Session(db_engine) as db, db.begin():
        assert not seed_demo(db)["created"]
        assert db.scalar(select(func.count()).select_from(Student)) == 2
        assert db.get(Student, result["ids"]["alex"]).highest_level == "Staff corrected level"


def test_demo_messages_are_ordered_in_the_past(db_engine):
    before = datetime.now(UTC)
    with Session(db_engine) as db, db.begin():
        seed_demo(db)
        dates = [db.get(Message, demo_id(f"message_{i}")).occurred_at for i in range(3)]
        assert all(value.tzinfo is not None and value < before for value in dates)
        assert dates[0] < dates[1] < dates[2]


def test_legacy_date_repair_preserves_edits_and_is_repeatable(db_engine):
    edited_date = datetime(2020, 1, 1, tzinfo=UTC)
    with Session(db_engine) as db, db.begin():
        seed_demo(db)
        for index in range(3):
            db.get(Message, demo_id(f"message_{index}")).occurred_at = datetime(
                2027, 2, 7, 10, index, tzinfo=ZoneInfo("Australia/Melbourne")
            )
        db.get(Message, demo_id("message_1")).occurred_at = edited_date
        db.get(Message, demo_id("message_0")).body = "Staff edited text"
        unrelated = Message(
            conversation_id=demo_id("conversation"),
            kind="student_email",
            body="Unrelated email",
            occurred_at=edited_date + timedelta(days=1),
        )
        db.add(unrelated)
        db.flush()
        unrelated_id = unrelated.id
    with Session(db_engine) as db, db.begin():
        assert not seed_demo(db)["created"]
        assert repair_demo_message_dates(db) == 2
    with Session(db_engine) as db, db.begin():
        repaired_date = db.get(Message, demo_id("message_0")).occurred_at
        assert repaired_date < datetime.now(UTC)
        assert db.get(Message, demo_id("message_0")).body == "Staff edited text"
        assert db.get(Message, demo_id("message_1")).occurred_at == edited_date
        assert db.get(Message, unrelated_id).occurred_at == edited_date + timedelta(days=1)
        assert repair_demo_message_dates(db) == 0
        assert not seed_demo(db)["created"]
        assert db.get(Message, demo_id("message_0")).occurred_at == repaired_date


def test_demo_catalog_has_coherent_locations_and_term_dates(db_engine):
    with Session(db_engine) as db, db.begin():
        result = seed_demo(db)
        term = db.get(Term, result["ids"]["term"])
        assert term.name == "Term 1 · Summer 2027"
        locations = list(db.scalars(select(Location)))
        assert {location.name for location in locations} == {
            "Merri Ballet · Brunswick",
            "Merri Ballet · Carlton",
        }
        assert all(
            location.address and location.timezone == "Australia/Melbourne"
            for location in locations
        )
        for session in db.scalars(select(ClassSession)):
            regular_class = db.get(StudioClass, session.class_id)
            zone = ZoneInfo(regular_class.location.timezone)
            local_start = session.starts_at.astimezone(zone)
            assert term.starts_on <= local_start.date() <= term.ends_on
            assert local_start < session.ends_at.astimezone(zone)
            assert local_start.strftime("%A") in regular_class.name
        for student in db.scalars(select(Student)):
            assert student.email.endswith("@example.com")
            incoming = IncomingEmail.model_validate(
                {"from": student.email, "body": "Could I join Saturday ballet?"}
            )
            assert str(incoming.sender) == student.email
