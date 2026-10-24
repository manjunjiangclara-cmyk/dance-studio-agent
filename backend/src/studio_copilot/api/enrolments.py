from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import or_, select

from studio_copilot.administration import service
from studio_copilot.api import schemas as s
from studio_copilot.api.common import Db, Paging, page, save
from studio_copilot.persistence.models import Enrolment, StudioClass, Term

router = APIRouter(prefix="/enrolments", tags=["Enrolments"])


@router.post("", response_model=s.EnrolmentRead, status_code=201)
def create_enrolment(body: s.EnrolmentCreate, db: Db):
    return save(db, service.create_enrolment(db, **body.model_dump()))


@router.get("", response_model=s.Page[s.EnrolmentRead])
def list_enrolments(
    db: Db,
    paging: Paging,
    student_id: UUID | None = None,
    class_id: UUID | None = None,
    term_id: UUID | None = None,
    status: Literal["active", "ended", "cancelled"] | None = None,
    on_date: date | None = None,
):
    statement = (
        select(Enrolment)
        .join(StudioClass)
        .join(Term)
        .order_by(Enrolment.starts_on, Enrolment.created_at, Enrolment.id)
    )
    for column, value in [
        (Enrolment.student_id, student_id),
        (Enrolment.class_id, class_id),
        (StudioClass.term_id, term_id),
        (Enrolment.status, status),
    ]:
        if value is not None:
            statement = statement.where(column == value)
    if on_date:
        statement = statement.where(
            Enrolment.status.in_(["active", "ended"]),
            Enrolment.starts_on <= on_date,
            or_(Enrolment.ends_on.is_(None), Enrolment.ends_on >= on_date),
            Term.starts_on <= on_date,
            Term.ends_on >= on_date,
        )
    return page(db, statement, paging)


@router.get("/{enrolment_id}", response_model=s.EnrolmentRead)
def get_enrolment(enrolment_id: UUID, db: Db):
    return service.require(db, Enrolment, enrolment_id)


@router.post("/{enrolment_id}/end", response_model=s.EnrolmentRead)
def end_enrolment(enrolment_id: UUID, body: s.EnrolmentEnd, db: Db):
    return save(db, service.end_enrolment(db, enrolment_id, body.ends_on))


@router.post("/{enrolment_id}/cancel", response_model=s.EnrolmentRead)
def cancel_enrolment(enrolment_id: UUID, db: Db):
    return save(db, service.cancel_enrolment(db, enrolment_id))


@router.post("/{enrolment_id}/change", response_model=s.EnrolmentChangeRead)
def change_enrolment(enrolment_id: UUID, body: s.EnrolmentChange, db: Db):
    previous, replacement = service.change_enrolment(db, enrolment_id, **body.model_dump())
    db.commit()
    db.refresh(previous)
    db.refresh(replacement)
    return {"previous": previous, "replacement": replacement}
