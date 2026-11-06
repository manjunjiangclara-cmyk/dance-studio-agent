"""Migration/constraint tests independent of fake provider behavior."""

from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.models import EmbeddingVector
from tests.support import migration_config

pytestmark = pytest.mark.integration


def test_downgrade_preserves_shared_vector_extension_and_other_schemas(db_engine):
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        connection.execute(text("CREATE TEMP TABLE vector_sentinel (value public.vector(3))"))
        connection.execute(text("INSERT INTO vector_sentinel VALUES ('[1,0,0]')"))
        command.downgrade(config, "e71b309a4c82")
        assert connection.scalar(text("SELECT count(*) FROM vector_sentinel")) == 1
        assert (
            connection.scalar(
                text(
                    "SELECT extnamespace::regnamespace::text FROM pg_extension "
                    "WHERE extname='vector'"
                )
            )
            == "public"
        )
        command.upgrade(config, "head")
        command.check(config)


@pytest.mark.parametrize("values", [[0.0] * 1536, [2.0] + [0.0] * 1535])
def test_database_itself_rejects_invalid_unit_vectors(db_engine, values):
    profile = EmbeddingProfile()
    with Session(db_engine) as session:
        session.add(
            EmbeddingVector(
                key=uuid4().hex,
                profile_hash=profile.key,
                input_sha256=uuid4().hex,
                embedding=values,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_vector_round_trip_is_single_precision_and_deduplicated(db_engine):
    profile = EmbeddingProfile()
    with Session(db_engine) as session:
        session.add(
            EmbeddingVector(
                key="first",
                profile_hash=profile.key,
                input_sha256="same",
                embedding=[1.0] + [0.0] * 1535,
            )
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(EmbeddingVector)) == 1
        values = session.scalar(select(EmbeddingVector.embedding))
        assert len(values) == 1536 and values[0] == 1.0 and values[1] == 0.0
        session.add(
            EmbeddingVector(
                key="second",
                profile_hash=profile.key,
                input_sha256="same",
                embedding=[1.0] + [0.0] * 1535,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
