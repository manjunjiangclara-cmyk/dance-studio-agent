"""Integration tests use temporary schemas in a dedicated test database."""

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import (
    ClassSession,
    Enrolment,
    Location,
    Student,
    StudioClass,
    Term,
)
from tests.support import migration_config


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL database name must end with '_test'.")

    schema = f"test_{uuid.uuid4().hex}"
    admin = make_engine(url)
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # Only the randomly named schema created by this test is removed.
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def db(db_engine: Engine) -> Iterator[Session]:
    with Session(db_engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def catalog(db: Session) -> SimpleNamespace:
    student = Student(
        display_name="Alex Example", email="alex@example.test", highest_level="Level 2"
    )
    term = Term(name="Term 1 2027", starts_on=date(2027, 2, 1), ends_on=date(2027, 3, 31))
    location = Location(
        name="Studio A", address="Fictional location", timezone="Australia/Melbourne"
    )
    regular_class = StudioClass(
        name="Monday Level 2", level="Level 2", term=term, location=location
    )
    enrolment = Enrolment(
        student=student, regular_class=regular_class, starts_on=term.starts_on, status="active"
    )
    class_session = ClassSession(
        regular_class=regular_class,
        starts_at=datetime(2027, 2, 8, 18, tzinfo=ZoneInfo("Australia/Melbourne")),
        ends_at=datetime(2027, 2, 8, 19, tzinfo=ZoneInfo("Australia/Melbourne")),
        capacity=12,
    )
    db.add_all([student, term, location, regular_class, enrolment, class_session])
    db.flush()
    return SimpleNamespace(
        student=student,
        term=term,
        location=location,
        regular_class=regular_class,
        enrolment=enrolment,
        class_session=class_session,
    )
