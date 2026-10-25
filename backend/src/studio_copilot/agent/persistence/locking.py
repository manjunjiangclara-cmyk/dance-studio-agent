"""Serialize student runs and incoming messages without row locks over LLM calls."""

from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import text

from studio_copilot.administration.service import conflict


def lock_key(student_id: UUID) -> int:
    return int.from_bytes(student_id.bytes[:8], byteorder="big", signed=True)


def guard_message(db, student_id: UUID):
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key(student_id)}):
        conflict("An agent is processing this student. Retry after the run completes.")


@contextmanager
def student_lock(engine, student_id: UUID):
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key(student_id)}
        )
        if not acquired:
            conflict("An agent is processing this student. Retry after the run completes.")
        try:
            yield
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key(student_id)}
            )
