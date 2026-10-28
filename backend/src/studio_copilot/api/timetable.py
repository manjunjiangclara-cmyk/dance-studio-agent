from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import Date, cast, func, select

from studio_copilot.administration import service
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db, Paging, page, save
from studio_copilot.persistence.models import (
    ClassSession,
    Location,
    SessionAttendance,
    Student,
    StudioClass,
    Term,
)

router = APIRouter(tags=["Timetable"])


@router.post("/terms", response_model=s.TermRead, status_code=201)
def create_term(body: s.TermCreate, db: Db):
    if body.starts_on > body.ends_on:
        service.invalid("Term end must be on or after its start.")
    return save(db, Term(**body.model_dump()))


@router.get("/terms", response_model=s.Page[s.TermRead])
def list_terms(db: Db, paging: Paging):
    return page(db, select(Term).order_by(Term.starts_on, Term.id), paging)


@router.get("/terms/{term_id}", response_model=s.TermRead)
def get_term(term_id: UUID, db: Db):
    return service.require(db, Term, term_id)


@router.patch("/terms/{term_id}", response_model=s.TermRead)
def update_term(term_id: UUID, body: s.TermPatch, db: Db):
    return save(db, service.update_term(db, term_id, body.model_dump(exclude_unset=True)))


@router.post("/locations", response_model=s.LocationRead, status_code=201)
def create_location(body: s.LocationCreate, db: Db):
    return save(db, Location(**body.model_dump()))


@router.get("/locations", response_model=s.Page[s.LocationRead])
def list_locations(db: Db, paging: Paging):
    return page(db, select(Location).order_by(Location.created_at, Location.id), paging)


@router.get("/locations/{location_id}", response_model=s.LocationRead)
def get_location(location_id: UUID, db: Db):
    return service.require(db, Location, location_id)


@router.patch("/locations/{location_id}", response_model=s.LocationRead)
def update_location(location_id: UUID, body: s.LocationPatch, db: Db):
    return save(db, service.update_location(db, location_id, body.model_dump(exclude_unset=True)))


@router.post("/classes", response_model=s.ClassRead, status_code=201)
def create_class(body: s.ClassCreate, db: Db):
    return save(db, service.create_class(db, body.model_dump()))


@router.get("/classes", response_model=s.Page[s.ClassRead])
def list_classes(
    db: Db,
    paging: Paging,
    term_id: UUID | None = None,
    location_id: UUID | None = None,
    level: str | None = None,
):
    statement = select(StudioClass).order_by(StudioClass.created_at, StudioClass.id)
    for column, value in [
        (StudioClass.term_id, term_id),
        (StudioClass.location_id, location_id),
        (StudioClass.level, level),
    ]:
        if value is not None:
            statement = statement.where(column == value)
    return page(db, statement, paging)


@router.get("/classes/{class_id}", response_model=s.ClassRead)
def get_class(class_id: UUID, db: Db):
    return service.require(db, StudioClass, class_id)


@router.patch("/classes/{class_id}", response_model=s.ClassRead)
def update_class(class_id: UUID, body: s.ClassPatch, db: Db):
    record = service.require(db, StudioClass, class_id, lock=True)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(record, name, value)
    return save(db, record)


@router.post("/sessions", response_model=s.SessionRead, status_code=201)
def create_session(body: s.SessionCreate, db: Db):
    return save(db, service.create_session(db, body.model_dump()))


@router.get("/sessions", response_model=s.Page[s.SessionRead])
def list_sessions(
    db: Db,
    paging: Paging,
    class_id: UUID | None = None,
    term_id: UUID | None = None,
    location_id: UUID | None = None,
    level: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    if from_date and to_date and from_date > to_date:
        service.invalid("from_date must be on or before to_date.")
    statement = (
        select(ClassSession)
        .join(StudioClass)
        .join(Location)
        .order_by(ClassSession.starts_at, ClassSession.id)
    )
    for column, value in [
        (ClassSession.class_id, class_id),
        (StudioClass.term_id, term_id),
        (StudioClass.location_id, location_id),
        (StudioClass.level, level),
    ]:
        if value is not None:
            statement = statement.where(column == value)
    local_date = cast(func.timezone(Location.timezone, ClassSession.starts_at), Date)
    if from_date:
        statement = statement.where(local_date >= from_date)
    if to_date:
        statement = statement.where(local_date <= to_date)
    return page(db, statement, paging)


@router.get("/sessions/{session_id}", response_model=s.SessionRead)
def get_session(session_id: UUID, db: Db):
    return service.require(db, ClassSession, session_id)


@router.patch("/sessions/{session_id}", response_model=s.SessionRead)
def update_session(session_id: UUID, body: s.SessionPatch, db: Db):
    return save(db, service.update_session(db, session_id, body.model_dump(exclude_unset=True)))


@router.get("/sessions/{session_id}/students", response_model=s.Page[s.StudentRead])
def session_roster(session_id: UUID, db: Db, paging: Paging):
    record = service.require(db, ClassSession, session_id)
    students = list(
        db.scalars(
            select(Student)
            .where(Student.id.in_(record.students))
            .order_by(Student.display_name, Student.id)
        )
    )
    limit, offset = paging
    return {
        "items": students[offset : offset + limit],
        "total": len(students),
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}/attendance")
def list_attendance(session_id: UUID, db: Db):
    session = service.require(db, ClassSession, session_id)
    rows = db.scalars(select(SessionAttendance).where(SessionAttendance.session_id == session.id))
    return {str(row.student_id): row.status for row in rows}


@router.put("/sessions/{session_id}/attendance/{student_id}")
def update_attendance(session_id: UUID, student_id: UUID, body: s.AttendanceUpdate, db: Db):
    # Serialize attendance changes with approval's student lock.
    service.require(db, Student, student_id, lock=True)
    session = service.require(db, ClassSession, session_id, lock=True)
    if student_id not in session.students:
        service.invalid("The student must be on the session roster.")
    if body.status != "unknown" and session.ends_at > datetime.now(UTC):
        service.invalid("Attendance can only be recorded after the session ends.")
    row = db.scalar(
        select(SessionAttendance).where(
            SessionAttendance.session_id == session_id, SessionAttendance.student_id == student_id
        )
    )
    if body.status == "unknown":
        if row is not None:
            db.delete(row)
    elif row is None:
        db.add(
            SessionAttendance(
                session_id=session_id,
                student_id=student_id,
                status=body.status,
                level_at_attendance=session.regular_class.level,
            )
        )
    else:
        row.status = body.status
    db.commit()
    return {"student_id": str(student_id), "status": body.status}
