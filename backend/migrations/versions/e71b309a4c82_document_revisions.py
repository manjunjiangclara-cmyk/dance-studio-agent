"""Retain immutable document ingestion revisions.

Revision ID: e71b309a4c82
Revises: d30e61b4a8c2
"""

import hashlib
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e71b309a4c82"
down_revision = "d30e61b4a8c2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "documents", sa.Column("current_revision", sa.Integer(), server_default="1", nullable=False)
    )
    table = op.create_table(
        "document_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("hash_origin", sa.String(30), nullable=False),
        sa.Column("ingestion_status", sa.String(30), nullable=False),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.UniqueConstraint("document_id", "revision"),
        sa.CheckConstraint("revision > 0", name="positive_revision"),
        sa.CheckConstraint("byte_size >= 0", name="nonnegative_size"),
        sa.CheckConstraint(
            "effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to",
            name="dates_ordered",
        ),
        sa.CheckConstraint(
            "hash_origin IN ('upload_bytes', 'stored_text_utf8')", name="hash_origin"
        ),
        sa.CheckConstraint(
            "ingestion_status IN ('ready', 'needs_correction')", name="ingestion_status"
        ),
    )
    op.create_index("ix_document_revisions_sha256", "document_revisions", ["sha256"])
    connection = op.get_bind()
    # Preserve stored text exactly; original upload bytes are not available for legacy rows.
    rows = connection.execute(
        sa.text("SELECT id, title, filename, content, created_at, updated_at FROM documents")
    ).mappings()
    for row in rows:
        raw = row["content"].encode("utf-8")
        connection.execute(
            table.insert().values(
                id=uuid.uuid4(),
                document_id=row["id"],
                revision=1,
                title=row["title"],
                filename=row["filename"],
                content=row["content"],
                byte_size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                hash_origin="stored_text_utf8",
                ingestion_status="ready"
                if row["content"].replace("\ufeff", "").strip()
                else "needs_correction",
                created_at=row["updated_at"],
                updated_at=row["updated_at"],
            )
        )
    op.execute("""CREATE FUNCTION reject_document_revision_update() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'Document revisions are immutable'; END $$""")
    op.execute("""CREATE TRIGGER document_revision_immutable BEFORE UPDATE ON document_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_document_revision_update()""")


def downgrade():
    op.execute("DROP TRIGGER document_revision_immutable ON document_revisions")
    op.execute("DROP FUNCTION reject_document_revision_update()")
    op.drop_table("document_revisions")
    op.drop_column("documents", "current_revision")
