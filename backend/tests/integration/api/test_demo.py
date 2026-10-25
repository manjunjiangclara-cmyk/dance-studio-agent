from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.api.schemas import IncomingEmail
from studio_copilot.demo import seed_demo
from studio_copilot.persistence.models import ClassSession, Location, Student, StudioClass, Term

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
