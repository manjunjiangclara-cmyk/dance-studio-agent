from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from studio_copilot.persistence.models import (
    ClassSession,
    Enrolment,
    Student,
    StudioClass,
    Term,
)

pytestmark = pytest.mark.integration


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


def test_session_roster_is_stored_independently_of_enrolment_dates(db, catalog):
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
    catalog.class_session.students = [catalog.student.id]
    later.students = [catalog.student.id]
    db.add(later)
    db.commit()
    db.expire_all()
    assert catalog.class_session.students == [catalog.student.id]
    assert later.students == [catalog.student.id]
    catalog.enrolment.status = "cancelled"
    db.commit()
    db.expire_all()
    assert catalog.class_session.students == later.students == [catalog.student.id]
