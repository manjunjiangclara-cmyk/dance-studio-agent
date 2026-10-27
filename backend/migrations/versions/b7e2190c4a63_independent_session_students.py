"""Move participation into independent session student lists.

Revision ID: b7e2190c4a63
Revises: af39d8426b10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7e2190c4a63"
down_revision = "af39d8426b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "class_sessions",
        sa.Column(
            "students",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    # Snapshot the former roster once, including approved makeup participants.
    # Later enrolment changes intentionally leave these independent lists alone.
    op.execute("""
        UPDATE class_sessions AS session
        SET students = ARRAY(
            SELECT student_id FROM (
                SELECT enrolment.student_id
                FROM enrolments AS enrolment
                JOIN classes AS class ON class.id = enrolment.class_id
                JOIN terms AS term ON term.id = class.term_id
                JOIN locations AS location ON location.id = class.location_id
                WHERE enrolment.class_id = session.class_id
                  AND enrolment.status IN ('active', 'ended')
                  AND (session.starts_at AT TIME ZONE location.timezone)::date
                      BETWEEN term.starts_on AND term.ends_on
                  AND enrolment.starts_on <=
                      (session.starts_at AT TIME ZONE location.timezone)::date
                  AND (enrolment.ends_on IS NULL OR enrolment.ends_on >=
                      (session.starts_at AT TIME ZONE location.timezone)::date)
                UNION
                SELECT booking.student_id FROM session_bookings AS booking
                WHERE booking.session_id = session.id
            ) AS participants ORDER BY student_id
        )
    """)
    # Approved runs already retain their session proposal and reviewed response.
    op.drop_table("session_bookings")


def downgrade() -> None:
    raise RuntimeError(
        "Independent session lists cannot be converted back to approval-only bookings "
        "without losing manually assigned students. Restore a pre-upgrade backup instead."
    )
