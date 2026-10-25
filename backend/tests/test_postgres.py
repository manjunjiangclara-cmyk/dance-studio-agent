import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from conftest import migration_config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from studio_copilot.persistence.models import (
    ClassSession,
    Conversation,
    Enrolment,
    Message,
    Student,
    StudioClass,
    Term,
)

pytestmark = pytest.mark.integration


def test_migration_round_trip_and_no_model_drift(db_engine):
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.check(config)
        command.downgrade(config, "base")
        assert set(inspect(connection).get_table_names()) <= {"alembic_version"}
        command.upgrade(config, "head")
        command.check(config)
        assert len(set(inspect(connection).get_table_names()) - {"alembic_version"}) == 8


def test_profile_memory_and_two_consecutive_emails_survive_reload(db, catalog):
    student = catalog.student
    student.context = {"preferred_day": "Thursday"}
    conversation = Conversation(student=student, subject="Makeup request")
    first_at = datetime(2027, 2, 7, 10, tzinfo=ZoneInfo("Australia/Melbourne"))
    # Insert out of order to verify retrieval follows occurrence time.
    conversation.messages = [
        Message(
            kind="student_email",
            body="Actually, Saturday please.",
            occurred_at=first_at + timedelta(minutes=10),
        ),
        Message(kind="student_email", body="Could I attend Thursday?", occurred_at=first_at),
        Message(
            kind="assistant_draft", body="Draft only.", occurred_at=first_at + timedelta(minutes=11)
        ),
    ]
    db.add(conversation)
    student_id, conversation_id = student.id, None
    db.commit()
    conversation_id = conversation.id
    db.expunge_all()

    saved = db.get(Student, student_id)
    assert saved.highest_level == "Level 2"
    assert saved.context == {"preferred_day": "Thursday"}
    saved.context["preferred_day"] = "Saturday"
    db.commit()
    db.expire_all()
    assert db.get(Student, student_id).context["preferred_day"] == "Saturday"
    assert db.get(Student, student_id).highest_level == "Level 2"
    messages = db.get(Conversation, conversation_id).messages
    assert [message.body for message in messages[:2]] == [
        "Could I attend Thursday?",
        "Actually, Saturday please.",
    ]
    assert messages[2].kind == "assistant_draft"
    assert messages[0].occurred_at.utcoffset() is not None


def test_enrolment_changes_preserve_history_and_allow_rejoining(db, catalog):
    old = catalog.enrolment
    old.status, old.ends_on = "ended", date(2027, 2, 14)
    db.flush()
    rejoined = Enrolment(
        student=catalog.student,
        regular_class=catalog.regular_class,
        starts_on=date(2027, 3, 1),
    )
    next_term = Term(name="Term 2", starts_on=date(2027, 4, 1), ends_on=date(2027, 6, 30))
    next_class = StudioClass(
        name="Thursday", level="Level 2", term=next_term, location=catalog.location
    )
    next_enrolment = Enrolment(
        student=catalog.student, regular_class=next_class, starts_on=next_term.starts_on
    )
    second_class = StudioClass(
        name="Saturday", level="Level 2", term=catalog.term, location=catalog.location
    )
    second = Enrolment(
        student=catalog.student, regular_class=second_class, starts_on=date(2027, 3, 1)
    )
    db.add_all([rejoined, next_enrolment, second])
    student_id = catalog.student.id
    db.commit()
    db.expunge_all()
    student = db.get(Student, student_id)
    assert len(student.enrolment_history) == 4
    assert len(student.active_enrolments_on(date(2027, 3, 8))) == 2
    assert len(student.active_enrolments_on(date(2027, 4, 8))) == 1
    assert student.enrolment_history[0].status == "ended"


def test_session_roster_uses_period_dates_in_location_timezone(db, catalog):
    catalog.enrolment.ends_on = date(2027, 2, 8)
    catalog.enrolment.status = "ended"
    # This session is on Feb 8 in Melbourne but Feb 7 in UTC.
    catalog.class_session.starts_at = datetime(
        2027, 2, 8, 0, 30, tzinfo=ZoneInfo("Australia/Melbourne")
    )
    catalog.class_session.ends_at = catalog.class_session.starts_at + timedelta(hours=1)
    later = ClassSession(
        regular_class=catalog.regular_class,
        starts_at=datetime(2027, 2, 15, 18, tzinfo=ZoneInfo("UTC")),
        ends_at=datetime(2027, 2, 15, 19, tzinfo=ZoneInfo("UTC")),
        capacity=12,
    )
    db.add(later)
    db.commit()
    db.expire_all()
    assert catalog.class_session.students == [catalog.student]
    assert later.students == []


def test_duplicate_email_is_case_insensitive_for_direct_sql_writes(db, catalog):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            Student.__table__.insert().values(display_name="Duplicate", email="ALEX@EXAMPLE.TEST")
        )


def test_multiple_active_periods_for_same_class_are_rejected(db, catalog):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            Enrolment(
                student_id=catalog.student.id,
                class_id=catalog.regular_class.id,
                starts_on=date(2027, 2, 8),
            )
        )
        db.flush()


@pytest.mark.parametrize(
    "change",
    [
        "term_dates",
        "session_times",
        "capacity",
        "enrolment_dates",
        "enrolment_status",
        "ended_without_date",
        "foreign_key",
        "message_kind",
        "context_type",
    ],
)
def test_database_rejects_invalid_records(db, catalog, change):
    with pytest.raises(IntegrityError), db.begin_nested():
        if change == "term_dates":
            catalog.term.ends_on = catalog.term.starts_on - timedelta(days=1)
        elif change == "session_times":
            catalog.class_session.ends_at = catalog.class_session.starts_at
        elif change == "capacity":
            catalog.class_session.capacity = 0
        elif change == "enrolment_dates":
            catalog.enrolment.ends_on = catalog.enrolment.starts_on - timedelta(days=1)
        elif change == "enrolment_status":
            catalog.enrolment.status = "invented"
        elif change == "ended_without_date":
            catalog.enrolment.status = "ended"
        elif change == "foreign_key":
            catalog.enrolment.student_id = uuid.uuid4()
        elif change == "message_kind":
            conversation = Conversation(student=catalog.student)
            db.add(Message(conversation=conversation, kind="sent_email", body="Not sent"))
        elif change == "context_type":
            db.execute(text("UPDATE students SET context = '[]'::jsonb"))
        db.flush()


def test_referenced_student_cannot_be_deleted(db, catalog):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.delete(catalog.student)
        db.flush()
    assert db.scalar(select(Student.id)) == catalog.student.id
