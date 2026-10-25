"""Studio data, enrolment history, and conversation memory.

Business rules and policy values do not belong in these models. Enrolment rows
describe attendance periods; current enrolments and session rosters are views of
that history, not additional stored copies.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Record:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Student(Record, Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("uq_students_email_normalized", func.lower(text("email")), unique=True),
        CheckConstraint("jsonb_typeof(context) = 'object'", name="context_object"),
    )

    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    # A staff-maintained label, not an inferred rank or a blanket eligibility grant.
    highest_level: Mapped[str | None] = mapped_column(String(100))
    context: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), default=dict, server_default=text("'{}'::jsonb")
    )

    enrolment_history: Mapped[list[Enrolment]] = relationship(
        back_populates="student",
        order_by="(Enrolment.starts_on, Enrolment.created_at, Enrolment.id)",
        passive_deletes="all",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="student", passive_deletes="all"
    )

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

    def active_enrolments_on(self, on_date: date) -> list[Enrolment]:
        """Explicit date makes the current view reproducible in queries/tests."""
        return [record for record in self.enrolment_history if record.is_active_on(on_date)]

    @property
    def current_enrolments(self) -> list[Enrolment]:
        """The initial studio operates in Melbourne; this field is read-only."""
        return self.active_enrolments_on(datetime.now(ZoneInfo("Australia/Melbourne")).date())


class Term(Record, Base):
    __tablename__ = "terms"
    __table_args__ = (CheckConstraint("starts_on <= ends_on", name="dates_ordered"),)

    name: Mapped[str] = mapped_column(String(100), unique=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)


class Location(Record, Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    address: Mapped[str] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(
        String(100), default="Australia/Melbourne", server_default="Australia/Melbourne"
    )


class StudioClass(Record, Base):
    __tablename__ = "classes"
    __table_args__ = (Index("ix_classes_term_id_location_id", "term_id", "location_id"),)

    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id", ondelete="RESTRICT"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(100))
    prerequisites: Mapped[str | None] = mapped_column(Text)

    term: Mapped[Term] = relationship()
    location: Mapped[Location] = relationship()
    sessions: Mapped[list[ClassSession]] = relationship(
        back_populates="regular_class", order_by="ClassSession.starts_at", passive_deletes="all"
    )
    enrolments: Mapped[list[Enrolment]] = relationship(
        back_populates="regular_class", passive_deletes="all"
    )


class ClassSession(Record, Base):
    __tablename__ = "class_sessions"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="times_ordered"),
        CheckConstraint("capacity > 0", name="positive_capacity"),
        UniqueConstraint("class_id", "starts_at"),
    )

    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(Integer)

    regular_class: Mapped[StudioClass] = relationship(back_populates="sessions")

    @property
    def students(self) -> list[Student]:
        """Regular roster only; absence/makeup participation is a later feature."""
        on_date = self.starts_at.astimezone(ZoneInfo(self.regular_class.location.timezone)).date()
        return [
            record.student
            for record in self.regular_class.enrolments
            if record.is_active_on(on_date)
        ]


class Enrolment(Record, Base):
    __tablename__ = "enrolments"
    __table_args__ = (
        CheckConstraint("ends_on IS NULL OR starts_on <= ends_on", name="dates_ordered"),
        CheckConstraint("status IN ('active', 'ended', 'cancelled')", name="valid_status"),
        CheckConstraint("status != 'ended' OR ends_on IS NOT NULL", name="ended_has_date"),
        UniqueConstraint("student_id", "class_id", "starts_on"),
        Index(
            "uq_enrolments_active_student_class",
            "student_id",
            "class_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_enrolments_class_id", "class_id"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")

    student: Mapped[Student] = relationship(back_populates="enrolment_history")
    regular_class: Mapped[StudioClass] = relationship(back_populates="enrolments")

    def is_active_on(self, on_date: date) -> bool:
        """Ended periods still describe historical attendance; cancellation does not."""
        return (
            self.status in {"active", "ended"}
            and self.starts_on <= on_date
            and (self.ends_on is None or on_date <= self.ends_on)
            and self.regular_class.term.starts_on <= on_date <= self.regular_class.term.ends_on
        )


class Conversation(Record, Base):
    __tablename__ = "conversations"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    subject: Mapped[str | None] = mapped_column(String(500))

    student: Mapped[Student] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        order_by="(Message.occurred_at, Message.created_at, Message.id)",
        passive_deletes="all",
    )


class Message(Record, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('student_email', 'assistant_draft', 'staff_note')", name="valid_kind"
        ),
        Index("ix_messages_conversation_id_occurred_at", "conversation_id", "occurred_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
