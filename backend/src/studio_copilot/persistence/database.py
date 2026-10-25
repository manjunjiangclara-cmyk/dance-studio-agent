"""Explicit database configuration; importing this module opens no connections."""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("Set DATABASE_URL to a PostgreSQL connection URL.")
    if make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("DATABASE_URL must use the postgresql+psycopg driver.")
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
