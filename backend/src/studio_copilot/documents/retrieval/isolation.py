"""Initialize only explicitly owned disposable evaluation schemas."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def initialize(engine, schema, alembic_ini):
    """Never discover a fallback schema's Alembic version or application tables."""
    # Schema names are generated internally. Quote defensively for test callers too.
    quoted = engine.dialect.identifier_preparer.quote_identifier(schema)
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL search_path TO {quoted}"))
        config = Config(str(alembic_ini))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        for relation in (
            "alembic_version",
            "documents",
            "document_revisions",
            "embedding_vectors",
            "embedding_runs",
            "document_chunks",
        ):
            owner = connection.scalar(
                text(
                    "SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE c.oid=to_regclass(:relation)"
                ),
                dict(relation=relation),
            )
            if owner != schema:
                raise ValueError("Evaluation tables did not resolve inside the owned schema.")
        if connection.scalar(text("SELECT count(*) FROM embedding_vectors")) != 0:
            raise ValueError("Fresh schema unexpectedly has cached vectors.")
