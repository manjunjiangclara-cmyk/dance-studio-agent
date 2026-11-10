"""Persist explicit document answer activation.

Revision ID: b82d1a9f140c
Revises: f924be7ca103
"""

import sqlalchemy as sa
from alembic import op

revision = "b82d1a9f140c"
down_revision = "f924be7ca103"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_activations",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("token", sa.UUID(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(200), nullable=True),
        sa.CheckConstraint(
            "status IN ('preparing','enabled','failed','disabled')",
            name=op.f("ck_document_activations_status"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_activations_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["embedding_runs.id"],
            name=op.f("fk_document_activations_run_id_embedding_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_document_activations")),
    )


def downgrade():
    op.drop_table("document_activations")
