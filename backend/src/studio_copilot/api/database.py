"""Read-only inspection of application tables and their stored columns."""

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select

from studio_copilot.api.common import Db, Paging
from studio_copilot.persistence.models import Base

router = APIRouter(prefix="/database", tags=["Database"])


@router.get("")
def list_tables(db: Db):
    return [
        {
            "name": table.name,
            "columns": list(table.columns.keys()),
            "total": db.scalar(select(func.count()).select_from(table)),
        }
        for table in Base.metadata.tables.values()
    ]


@router.get("/{table_name}")
def list_records(table_name: str, db: Db, paging: Paging):
    # Resolve only mapped application tables; never interpolate SQL or inspect
    # server-managed tables, workflow checkpoints, or connection configuration.
    table = Base.metadata.tables.get(table_name)
    if table is None:
        raise HTTPException(404, "This application table was not found.")
    limit, offset = paging
    statement = select(table).order_by(table.c.created_at, table.c.id)
    return jsonable_encoder(
        {
            "items": [
                dict(row) for row in db.execute(statement.limit(limit).offset(offset)).mappings()
            ],
            "total": db.scalar(select(func.count()).select_from(table)),
            "limit": limit,
            "offset": offset,
        }
    )
