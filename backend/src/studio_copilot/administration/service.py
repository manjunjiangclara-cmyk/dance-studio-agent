"""Small application services; callers commit or roll back the entire operation."""

from datetime import date, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import (
    ClassSession,
    Enrolment,
    Location,
    Student,
    StudioClass,
    Term,
)


class AdministrationError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def require(db: Session, model, record_id: UUID, *, lock: bool = False):
    record = db.get(model, record_id, with_for_update=lock, populate_existing=lock)
    if record is None:
        raise AdministrationError(404, "not_found", f"{model.__name__} was not found.")
    return record


def invalid(message: str) -> None:
    raise AdministrationError(422, "invalid_operation", message)


def conflict(message: str) -> None:
    raise AdministrationError(409, "conflict", message)


def validate_period(starts_on: date, ends_on: date | None, term: Term) -> None:
    if ends_on is not None and ends_on < starts_on:
        invalid("End date must be on or after start date.")
    if not term.starts_on <= starts_on <= term.ends_on:
        invalid("Start date must fall within the class term.")
    if ends_on is not None and not starts_on <= ends_on <= term.ends_on:
        invalid("End date must fall within the class term.")


def validate_session(record: ClassSession) -> None:
    if record.ends_at <= record.starts_at:
        invalid("Session end must be after its start.")
    zone = ZoneInfo(record.regular_class.location.timezone)
    term = record.regular_class.term
    for instant in [record.starts_at, record.ends_at]:
        if not term.starts_on <= instant.astimezone(zone).date() <= term.ends_on:
            invalid("Session times must fall within the class term in its location timezone.")


def session_attendee_ids(db: Session, session: ClassSession) -> set[UUID]:
    """The session list is authoritative, independently of enrolments."""
    return set(session.students or [])


def check_regular_capacity(db: Session, regular_class: StudioClass) -> None:
    """Explicit student lists must fit the capacity of their own session."""
    db.flush()
    sessions = db.scalars(select(ClassSession).where(ClassSession.class_id == regular_class.id))
    for session in sessions:
        if len(session_attendee_ids(db, session)) > session.capacity:
            conflict("The change would exceed the capacity of a dated session.")


def create_enrolment(
    db: Session, student_id: UUID, class_id: UUID, starts_on: date, ends_on: date | None
) -> Enrolment:
    require(db, Student, student_id)
    regular_class = require(db, StudioClass, class_id, lock=True)
    validate_period(starts_on, ends_on, regular_class.term)
    overlap = db.scalar(
        select(Enrolment.id)
        .where(
            Enrolment.student_id == student_id,
            Enrolment.class_id == class_id,
            Enrolment.status.in_(["active", "ended"]),
            Enrolment.starts_on <= (ends_on or regular_class.term.ends_on),
            or_(Enrolment.ends_on.is_(None), Enrolment.ends_on >= starts_on),
        )
        .limit(1)
    )
    if overlap:
        conflict("The student already has an attendance period covering those dates in this class.")
    record = Enrolment(
        student_id=student_id,
        regular_class=regular_class,
        starts_on=starts_on,
        ends_on=ends_on,
        status="active",
    )
    db.add(record)
    return record


def end_enrolment(db: Session, record_id: UUID, ends_on: date) -> Enrolment:
    record = require(db, Enrolment, record_id, lock=True)
    regular_class = require(db, StudioClass, record.class_id, lock=True)
    if record.status == "ended" and record.ends_on == ends_on:
        return record
    if record.status != "active":
        conflict("Only an active enrolment can be ended.")
    validate_period(record.starts_on, ends_on, regular_class.term)
    if record.ends_on is not None and ends_on > record.ends_on:
        invalid("Ending an enrolment cannot extend its existing attendance period.")
    record.ends_on, record.status = ends_on, "ended"
    return record


def cancel_enrolment(db: Session, record_id: UUID) -> Enrolment:
    record = require(db, Enrolment, record_id, lock=True)
    require(db, StudioClass, record.class_id, lock=True)
    if record.status == "cancelled":
        return record
    if record.status != "active":
        conflict("Only an active registration can be cancelled.")
    # The staff caller asserts registration never took effect. For actual
    # attendance followed by leaving a class, use end_enrolment instead.
    record.status = "cancelled"
    return record


def change_enrolment(
    db: Session, record_id: UUID, new_class_id: UUID, effective_on: date
) -> tuple[Enrolment, Enrolment]:
    previous = require(db, Enrolment, record_id, lock=True)
    if previous.status != "active":
        conflict("Only an active enrolment can change classes.")
    if previous.class_id == new_class_id:
        invalid("Choose a different class.")
    # Consistent ordering also handles opposite class transfers.
    for class_id in sorted([previous.class_id, new_class_id], key=str):
        require(db, StudioClass, class_id, lock=True)
    target = require(db, StudioClass, new_class_id)
    validate_period(effective_on, None, target.term)
    if effective_on <= previous.starts_on:
        invalid(
            "Change date must follow the old start date; cancel an unused registration instead."
        )
    end = min(
        effective_on - timedelta(days=1),
        previous.ends_on or previous.regular_class.term.ends_on,
        previous.regular_class.term.ends_on,
    )
    previous.ends_on, previous.status = end, "ended"
    db.flush()
    replacement = create_enrolment(db, previous.student_id, new_class_id, effective_on, None)
    return previous, replacement


def create_class(db: Session, values: dict) -> StudioClass:
    require(db, Term, values["term_id"], lock=True)
    require(db, Location, values["location_id"], lock=True)
    record = StudioClass(**values)
    db.add(record)
    return record


def create_session(db: Session, values: dict) -> ClassSession:
    regular_class = require(db, StudioClass, values.pop("class_id"), lock=True)
    validate_students(db, values.get("students", []))
    record = ClassSession(regular_class=regular_class, **values)
    with db.no_autoflush:
        validate_session(record)
    db.add(record)
    check_regular_capacity(db, regular_class)
    return record


def update_session(db: Session, record_id: UUID, values: dict) -> ClassSession:
    record = require(db, ClassSession, record_id)
    regular_class = require(db, StudioClass, record.class_id, lock=True)
    db.refresh(record)
    if "students" in values:
        validate_students(db, values["students"])
    for name, value in values.items():
        setattr(record, name, value)
    with db.no_autoflush:
        validate_session(record)
    check_regular_capacity(db, regular_class)
    return record


def update_term(db: Session, record_id: UUID, values: dict) -> Term:
    record = require(db, Term, record_id, lock=True)
    bounds_changed = any(
        name in values and values[name] != getattr(record, name)
        for name in ["starts_on", "ends_on"]
    )
    if bounds_changed and db.scalar(
        select(StudioClass.id).where(StudioClass.term_id == record.id).limit(1)
    ):
        conflict("Term dates cannot change after classes exist; create a new term instead.")
    for name, value in values.items():
        setattr(record, name, value)
    if record.starts_on > record.ends_on:
        invalid("Term end must be on or after its start.")
    return record


def update_location(db: Session, record_id: UUID, values: dict) -> Location:
    record = require(db, Location, record_id, lock=True)
    if "timezone" in values and values["timezone"] != record.timezone:
        if db.scalar(select(StudioClass.id).where(StudioClass.location_id == record.id).limit(1)):
            conflict("Location timezone cannot change after classes exist.")
    for name, value in values.items():
        setattr(record, name, value)
    return record


def validate_students(db: Session, students: list[UUID]) -> None:
    if len(students) != len(set(students)):
        invalid("A student can appear only once in a session.")
    for student_id in students:
        require(db, Student, student_id)
