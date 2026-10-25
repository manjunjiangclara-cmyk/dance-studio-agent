import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from studio_copilot.persistence.models import (
    Conversation,
    Enrolment,
    Message,
    Student,
)

pytestmark = pytest.mark.integration


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
