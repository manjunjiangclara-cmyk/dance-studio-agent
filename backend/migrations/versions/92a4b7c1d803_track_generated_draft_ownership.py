"""Retain generated draft ownership across revisions.

Revision ID: 92a4b7c1d803
Revises: c0f19d27e6a4
"""

import sqlalchemy as sa
from alembic import op

revision = "92a4b7c1d803"
down_revision = "c0f19d27e6a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("review_managed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # The old schema discarded earlier draft pointers. Protect legacy drafts in any
    # revised run's conversation conservatively, without inventing a run association.
    # This may also lock old manual drafts; newly created manual drafts stay editable.
    op.execute(
        "UPDATE messages SET review_managed = true WHERE kind = 'assistant_draft' AND EXISTS ("
        "SELECT 1 FROM agent_runs WHERE agent_runs.draft_message_id = messages.id OR "
        "(agent_runs.conversation_id = messages.conversation_id AND agent_runs.revision > 1))"
    )


def downgrade() -> None:
    op.drop_column("messages", "review_managed")
