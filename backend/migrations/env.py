"""Alembic supports explicit test connections and DATABASE_URL at runtime."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_with_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("Set DATABASE_URL before running migrations.")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        run_with_connection(supplied_connection)
    else:
        engine = make_engine()
        with engine.connect() as connection:
            run_with_connection(connection)
        engine.dispose()
