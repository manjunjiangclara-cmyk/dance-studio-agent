"""Index passage text for explicit retrieval.

Revision ID: f924be7ca103
Revises: a5f82d9548e0
"""

import sqlalchemy as sa
from alembic import op

revision = "f924be7ca103"
down_revision = "a5f82d9548e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_document_chunks_search",
        "document_chunks",
        [sa.text("to_tsvector('english'::regconfig, text)")],
        postgresql_using="gin",
        postgresql_where=sa.text("kind = 'passage'"),
    )


def downgrade():
    op.drop_index("ix_document_chunks_search", table_name="document_chunks")
