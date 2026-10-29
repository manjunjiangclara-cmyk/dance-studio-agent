"""Fresh installations must match the complete application schema."""

import logging

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from studio_copilot.persistence.models import Base
from tests.support import migration_config

pytestmark = pytest.mark.integration


def test_fresh_schema_matches_models(db_engine, monkeypatch):
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
        # Programmatic migrations must not silence pre-existing application loggers.
        logger = logging.getLogger("studio_copilot.agent.tracing")
        monkeypatch.setattr(logger, "disabled", False)
        command.check(config)
        assert not logger.disabled


def test_migration_preserves_legacy_regular_and_approved_session_students(db_engine):
    """Exercise real legacy rows before upgrading, including local-date boundaries."""
    from uuid import uuid4

    from sqlalchemy import text
    from sqlalchemy.schema import CreateSchema, DropSchema

    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        legacy_schema = "migration_" + uuid4().hex
        connection.execute(CreateSchema(legacy_schema))
        connection.execute(text(f"SET LOCAL search_path TO {legacy_schema}"))
        command.upgrade(config, "af39d8426b10")
        # Seed through legacy columns only; the current mapped models include students.
        connection.execute(
            text("""
            INSERT INTO terms (id, name, starts_on, ends_on)
            VALUES ('00000000-0000-0000-0000-000000000001', 'Legacy', '2027-02-01', '2027-03-31');
            INSERT INTO locations (id, name, address, timezone)
            VALUES ('00000000-0000-0000-0000-000000000002', 'Legacy', 'Test',
                    'Australia/Melbourne');
            INSERT INTO classes (id, term_id, location_id, name, level)
            VALUES ('00000000-0000-0000-0000-000000000003',
                    '00000000-0000-0000-0000-000000000001',
                    '00000000-0000-0000-0000-000000000002', 'Legacy', 'Level 2');
            INSERT INTO students (id, display_name, email, context)
            VALUES ('00000000-0000-0000-0000-000000000004', 'Regular', 'regular@test.test', '{}'),
                   ('00000000-0000-0000-0000-000000000005', 'Added', 'added@test.test', '{}'),
                   ('00000000-0000-0000-0000-000000000006', 'Cancelled', 'cancel@test.test', '{}');
            INSERT INTO class_sessions (id, class_id, starts_at, ends_at, capacity)
            VALUES ('00000000-0000-0000-0000-000000000007',
                    '00000000-0000-0000-0000-000000000003',
                    '2027-02-07 13:30:00+00', '2027-02-07 14:30:00+00', 3);
            INSERT INTO enrolments (id, student_id, class_id, starts_on, ends_on, status)
            VALUES ('00000000-0000-0000-0000-000000000008',
                    '00000000-0000-0000-0000-000000000004',
                    '00000000-0000-0000-0000-000000000003', '2027-02-08', '2027-02-08', 'ended'),
                   ('00000000-0000-0000-0000-000000000009',
                    '00000000-0000-0000-0000-000000000006',
                    '00000000-0000-0000-0000-000000000003', '2027-02-01', NULL, 'cancelled');
            INSERT INTO conversations (id, student_id)
            VALUES ('00000000-0000-0000-0000-000000000010',
                    '00000000-0000-0000-0000-000000000005');
            INSERT INTO messages (id, conversation_id, kind, body, review_managed)
            VALUES ('00000000-0000-0000-0000-000000000011',
                    '00000000-0000-0000-0000-000000000010', 'student_email',
                    'Please add me', false);
            INSERT INTO agent_runs (id, conversation_id, source_message_id, status, revision,
                                    interpretation, evidence, draft_details, policy_snapshot)
            VALUES ('00000000-0000-0000-0000-000000000012',
                    '00000000-0000-0000-0000-000000000010',
                    '00000000-0000-0000-0000-000000000011', 'approved', 1, '{}', '[]', '{}', '{}');
            INSERT INTO session_bookings (id, student_id, session_id, agent_run_id)
            VALUES ('00000000-0000-0000-0000-000000000013',
                    '00000000-0000-0000-0000-000000000005',
                    '00000000-0000-0000-0000-000000000007',
                    '00000000-0000-0000-0000-000000000012');
        """)
        )
        command.upgrade(config, "head")
        students = connection.execute(text("SELECT students FROM class_sessions")).scalar_one()
        assert {str(student) for student in students} == {
            "00000000-0000-0000-0000-000000000004",
            "00000000-0000-0000-0000-000000000005",
        }
        assert "session_bookings" not in inspect(connection).get_table_names()
        connection.execute(DropSchema(legacy_schema, cascade=True))
