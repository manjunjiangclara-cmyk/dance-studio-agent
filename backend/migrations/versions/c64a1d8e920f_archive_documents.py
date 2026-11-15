"""Retain archived documents and historical RAG sources."""

import sqlalchemy as sa
from alembic import op

revision = "c64a1d8e920f"
down_revision = "b82d1a9f140c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("documents", "archived_at")
