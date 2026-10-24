from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from studio_copilot.administration.service import require
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db, Paging, page, save
from studio_copilot.persistence.models import Enrolment, Student, StudioClass

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=s.StudentRead, status_code=201)
def create_student(body: s.StudentCreate, db: Db):
    return save(db, Student(**body.model_dump()))


@router.get("", response_model=s.Page[s.StudentRead])
def list_students(db: Db, paging: Paging, q: str | None = None):
    statement = select(Student).order_by(Student.created_at, Student.id)
    if q:
        statement = statement.where(
            or_(
                Student.display_name.icontains(q, autoescape=True),
                Student.email.icontains(q, autoescape=True),
            )
        )
    return page(db, statement, paging)


@router.get("/{student_id}", response_model=s.StudentDetail)
def get_student(student_id: UUID, db: Db, on_date: date | None = None):
    require(db, Student, student_id)
    student = db.scalar(
        select(Student)
        .where(Student.id == student_id)
        .options(
            selectinload(Student.enrolment_history)
            .selectinload(Enrolment.regular_class)
            .selectinload(StudioClass.term)
        )
    )
    as_of = on_date or datetime.now(ZoneInfo("Australia/Melbourne")).date()
    return {
        **s.StudentRead.model_validate(student).model_dump(),
        "as_of": as_of,
        "current_enrolments": student.active_enrolments_on(as_of),
        "enrolment_history": student.enrolment_history,
    }


@router.patch("/{student_id}", response_model=s.StudentRead)
def update_student(student_id: UUID, body: s.StudentPatch, db: Db):
    student = require(db, Student, student_id, lock=True)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(student, name, value)
    return save(db, student)
