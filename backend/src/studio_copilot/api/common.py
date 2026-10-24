from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise


Db = Annotated[Session, Depends(get_db)]


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> tuple[int, int]:
    return limit, offset


Paging = Annotated[tuple[int, int], Depends(pagination)]


def page(db: Session, statement, paging: tuple[int, int]) -> dict:
    limit, offset = paging
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    return {
        "items": list(db.scalars(statement.limit(limit).offset(offset)).unique()),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def save(db: Session, record):
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
