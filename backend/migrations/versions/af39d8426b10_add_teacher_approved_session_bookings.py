"""Store teacher-approved dated-session bookings.

Revision ID: af39d8426b10
Revises: 92a4b7c1d803
"""

import sqlalchemy as sa
from alembic import op

revision = "af39d8426b10"
down_revision = "92a4b7c1d803"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_bookings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("agent_run_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["class_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "session_id"),
        sa.UniqueConstraint("agent_run_id"),
    )
    op.create_index("ix_session_bookings_student_id", "session_bookings", ["student_id"])
    op.create_index("ix_session_bookings_session_id", "session_bookings", ["session_id"])


def downgrade() -> None:
    op.drop_table("session_bookings")
