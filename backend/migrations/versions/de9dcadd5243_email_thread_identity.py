"""Associate conversations with incoming email thread IDs."""

import sqlalchemy as sa
from alembic import op

revision = "de9dcadd5243"
down_revision = "c64a1d8e920f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversations", sa.Column("thread_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_conversations_thread_id", "conversations", ["thread_id"])


def downgrade():
    op.drop_constraint("uq_conversations_thread_id", "conversations", type_="unique")
    op.drop_column("conversations", "thread_id")
