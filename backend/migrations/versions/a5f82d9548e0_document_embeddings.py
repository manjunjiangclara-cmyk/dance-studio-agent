"""Persist revision-pinned embedding preparation

Revision ID: a5f82d9548e0
Revises: e71b309a4c82
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "a5f82d9548e0"
down_revision: str | Sequence[str] | None = "e71b309a4c82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The shared extension is never owned by an application/test schema.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    op.execute(
        "SELECT set_config('search_path', current_setting('search_path') || ', public', true)"
    )
    op.create_table(
        "embedding_vectors",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "public.vector_norm(embedding) BETWEEN 0.999 AND 1.001",
            name=op.f("ck_embedding_vectors_unit_norm"),
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_embedding_vectors")),
        sa.UniqueConstraint(
            "key", "profile_hash", "input_sha256", name=op.f("uq_embedding_vectors_key")
        ),
        sa.UniqueConstraint(
            "profile_hash", "input_sha256", name=op.f("uq_embedding_vectors_profile_hash")
        ),
    )
    op.create_table(
        "embedding_runs",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("chunker_hash", sa.String(length=64), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("chunker_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("headings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("prepared", sa.Boolean(), nullable=False),
        sa.Column("expected_chunks", sa.Integer(), nullable=True),
        sa.Column("expected_passages", sa.Integer(), nullable=True),
        sa.Column("lease_token", sa.UUID(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('preparing','running','failed','complete')",
            name=op.f("ck_embedding_runs_status"),
        ),
        sa.CheckConstraint(
            "reported_tokens >= 0 AND attempts >= 0",
            name=op.f("ck_embedding_runs_usage_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "revision"],
            ["document_revisions.document_id", "document_revisions.revision"],
            name=op.f("fk_embedding_runs_document_id_document_revisions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embedding_runs")),
        sa.UniqueConstraint(
            "document_id",
            "revision",
            "chunker_hash",
            "profile_hash",
            name=op.f("uq_embedding_runs_document_id"),
        ),
        sa.UniqueConstraint("id", "profile_hash", name=op.f("uq_embedding_runs_id")),
    )
    op.create_table(
        "document_chunks",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.String(length=72), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("parent_id", sa.String(length=72), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vector_key", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "kind = 'passage' OR vector_key IS NULL",
            name=op.f("ck_document_chunks_parents_not_embedded"),
        ),
        sa.CheckConstraint("kind IN ('parent','passage')", name=op.f("ck_document_chunks_kind")),
        sa.CheckConstraint(
            "token_count > 0 AND ((kind='parent' AND token_count<=2400) "
            "OR (kind='passage' AND token_count<=900))",
            name=op.f("ck_document_chunks_token_budget"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "parent_id"],
            ["document_chunks.run_id", "document_chunks.chunk_id"],
            name=op.f("fk_document_chunks_run_id_document_chunks"),
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "profile_hash"],
            ["embedding_runs.id", "embedding_runs.profile_hash"],
            name=op.f("fk_document_chunks_run_id_embedding_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vector_key", "profile_hash", "text_sha256"],
            [
                "embedding_vectors.key",
                "embedding_vectors.profile_hash",
                "embedding_vectors.input_sha256",
            ],
            name=op.f("fk_document_chunks_vector_key_embedding_vectors"),
        ),
        sa.PrimaryKeyConstraint("run_id", "chunk_id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("run_id", "ordinal", name=op.f("uq_document_chunks_run_id")),
    )


def downgrade() -> None:
    # Other schemas/databases may use the public extension; do not DROP EXTENSION.
    op.drop_table("document_chunks")
    op.drop_table("embedding_runs")
    op.drop_table("embedding_vectors")
