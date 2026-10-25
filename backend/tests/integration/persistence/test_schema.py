"""Fresh installations must match the complete application schema."""

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from studio_copilot.persistence.models import Base
from tests.support import migration_config

pytestmark = pytest.mark.integration


def test_fresh_schema_matches_models(db_engine):
    # db_engine has applied the initial migration to a new, empty test schema.
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {
            "alembic_version"
        }
        script = ScriptDirectory.from_config(config)
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == script.get_current_head()
        )
        command.check(config)
