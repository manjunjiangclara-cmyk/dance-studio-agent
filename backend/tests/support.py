"""Shared database setup helpers, independent of pytest fixture discovery."""

from pathlib import Path

from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]


def migration_config() -> Config:
    return Config(str(BACKEND / "alembic.ini"))
