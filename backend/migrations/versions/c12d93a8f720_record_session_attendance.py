"""Record actual attendance separately from session rosters.

Revision ID: c12d93a8f720
Revises: b7e2190c4a63
"""

import sqlalchemy as sa
from alembic import op

revision = "c12d93a8f720"
down_revision = "b7e2190c4a63"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "session_attendance",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("class_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.UUID(),
            sa.ForeignKey("students.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("level_at_attendance", sa.String(100), nullable=False),
        sa.UniqueConstraint("session_id", "student_id"),
        sa.CheckConstraint(
            "status IN ('attended', 'absent')", name="ck_session_attendance_valid_status"
        ),
    )
    op.create_index("ix_session_attendance_student_id", "session_attendance", ["student_id"])


def downgrade():
    op.drop_table("session_attendance")
