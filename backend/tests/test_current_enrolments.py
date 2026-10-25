from datetime import date, datetime
from zoneinfo import ZoneInfo

from studio_copilot.persistence import models
from studio_copilot.persistence.models import Enrolment, Location, Student, StudioClass, Term


def test_current_enrolments_keep_history_and_use_melbourne_date(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            # Still January in UTC, but already February in Melbourne.
            return datetime(2027, 1, 31, 13, 15, tzinfo=ZoneInfo("UTC")).astimezone(tz)

    monkeypatch.setattr(models, "datetime", Clock)
    student = Student(display_name="Alex", email="alex@example.test")
    location = Location(name="A", address="Fictional", timezone="Australia/Melbourne")
    previous = Term(name="Previous", starts_on=date(2026, 10, 1), ends_on=date(2026, 12, 20))
    current = Term(name="Current", starts_on=date(2027, 2, 1), ends_on=date(2027, 3, 31))
    next_term = Term(name="Next", starts_on=date(2027, 4, 1), ends_on=date(2027, 6, 30))
    periods = []
    for term in [previous, current, current, next_term]:
        regular_class = StudioClass(name=term.name, level="Level 2", term=term, location=location)
        periods.append(
            Enrolment(
                student=student,
                regular_class=regular_class,
                starts_on=term.starts_on,
                status="active",
            )
        )

    assert student.current_enrolments == periods[1:3]
    assert student.enrolment_history == periods


def test_ended_period_is_historical_and_cancellation_is_not_attendance():
    term = Term(name="Term", starts_on=date(2027, 2, 1), ends_on=date(2027, 3, 31))
    regular_class = StudioClass(name="Monday", level="Level 2", term=term)
    period = Enrolment(
        regular_class=regular_class,
        starts_on=date(2027, 2, 1),
        ends_on=date(2027, 2, 15),
        status="ended",
    )
    assert period.is_active_on(date(2027, 2, 15))
    assert not period.is_active_on(date(2027, 2, 16))
    period.status = "cancelled"
    assert not period.is_active_on(date(2027, 2, 8))
