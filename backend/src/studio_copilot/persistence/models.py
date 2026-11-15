"""Studio data, enrolment history, and conversation memory.

Business rules and policy values do not belong in these models. Enrolment rows
describe attendance periods. Each dated session owns an independent student list.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
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


class Document(Record, Base):
    __tablename__ = "documents"

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, deferred=True)
    current_revision: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))


class DocumentRevision(Record, Base):
    """Immutable source snapshot. Online use requires explicit server selection."""

    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision"),
        CheckConstraint("revision > 0", name="positive_revision"),
        CheckConstraint("byte_size >= 0", name="nonnegative_size"),
        CheckConstraint(
            "effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to",
            name="dates_ordered",
        ),
        CheckConstraint("hash_origin IN ('upload_bytes', 'stored_text_utf8')", name="hash_origin"),
        CheckConstraint(
            "ingestion_status IN ('ready', 'needs_correction')", name="ingestion_status"
        ),
        Index("ix_document_revisions_sha256", "sha256"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, deferred=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    hash_origin: Mapped[str] = mapped_column(String(30))
    ingestion_status: Mapped[str] = mapped_column(String(30))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class EmbeddingRun(Record, Base):
    """Explicit CLI preparation, never a publication or permission to retrieve."""

    __tablename__ = "embedding_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "revision"],
            ["document_revisions.document_id", "document_revisions.revision"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("document_id", "revision", "chunker_hash", "profile_hash"),
        UniqueConstraint("id", "profile_hash"),
        CheckConstraint("status IN ('preparing','running','failed','complete')", name="status"),
        CheckConstraint("reported_tokens >= 0 AND attempts >= 0", name="usage_nonnegative"),
        {"info": {"database_browser": False}},
    )

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(Integer)
    chunker_hash: Mapped[str] = mapped_column(String(64))
    profile_hash: Mapped[str] = mapped_column(String(64))
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[dict[str, Any]] = mapped_column(JSONB)
    chunker_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    headings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    warnings: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="preparing")
    prepared: Mapped[bool] = mapped_column(default=False)
    expected_chunks: Mapped[int | None] = mapped_column(Integer)
    expected_passages: Mapped[int | None] = mapped_column(Integer)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reported_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(40))


class DocumentActivation(Base):
    __tablename__ = "document_activations"
    __table_args__ = (
        CheckConstraint("status IN ('preparing','enabled','failed','disabled')", name="status"),
        {"info": {"database_browser": False}},
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("embedding_runs.id", ondelete="SET NULL")
    )
    token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(200))


class EmbeddingVector(Base):
    """Project-local shared cache. No original text or publication authority."""

    __tablename__ = "embedding_vectors"
    __table_args__ = (
        UniqueConstraint("profile_hash", "input_sha256"),
        UniqueConstraint("key", "profile_hash", "input_sha256"),
        CheckConstraint("public.vector_norm(embedding) BETWEEN 0.999 AND 1.001", name="unit_norm"),
        {"info": {"database_browser": False}},
    )

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_hash: Mapped[str] = mapped_column(String(64))
    input_sha256: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[Any] = mapped_column(Vector(1536), deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index(
            "ix_document_chunks_search",
            func.to_tsvector(text("'english'::regconfig"), text("text")),
            postgresql_using="gin",
            postgresql_where=text("kind = 'passage'"),
        ),
        ForeignKeyConstraint(
            ["run_id", "profile_hash"],
            ["embedding_runs.id", "embedding_runs.profile_hash"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["run_id", "parent_id"],
            ["document_chunks.run_id", "document_chunks.chunk_id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["vector_key", "profile_hash", "text_sha256"],
            [
                "embedding_vectors.key",
                "embedding_vectors.profile_hash",
                "embedding_vectors.input_sha256",
            ],
        ),
        UniqueConstraint("run_id", "ordinal"),
        CheckConstraint("kind IN ('parent','passage')", name="kind"),
        CheckConstraint("kind = 'passage' OR vector_key IS NULL", name="parents_not_embedded"),
        CheckConstraint(
            "token_count > 0 AND ((kind='parent' AND token_count<=2400) "
            "OR (kind='passage' AND token_count<=900))",
            name="token_budget",
        ),
        {"info": {"database_browser": False}},
    )

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(72), primary_key=True)
    profile_hash: Mapped[str] = mapped_column(String(64))
    ordinal: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(10))
    parent_id: Mapped[str | None] = mapped_column(String(72))
    text: Mapped[str] = mapped_column(Text, deferred=True)
    text_sha256: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB)
    vector_key: Mapped[str | None] = mapped_column(String(64))


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
    ai_summary: Mapped[str | None] = mapped_column(Text)
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

    students: Mapped[list[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(ARRAY(UUID(as_uuid=True))),
        default=list,
        server_default=text("'{}'::uuid[]"),
    )


class SessionAttendance(Record, Base):
    """Staff-recorded participation; no row means attendance is unknown."""

    __tablename__ = "session_attendance"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id"),
        CheckConstraint("status IN ('attended', 'absent')", name="valid_status"),
        Index("ix_session_attendance_student_id", "student_id"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("class_sessions.id", ondelete="RESTRICT")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20))
    level_at_attendance: Mapped[str] = mapped_column(String(100))


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
            "kind IN ('student_email', 'assistant_draft', 'staff_note', 'teacher_response')",
            name="valid_kind",
        ),
        Index("ix_messages_conversation_id_occurred_at", "conversation_id", "occurred_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(30))
    review_managed: Mapped[bool] = mapped_column(server_default="false", default=False)
    body: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentRun(Record, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'awaiting_review', 'finalizing', 'approved', "
            "'closed', 'superseded', 'failed')",
            name="valid_status",
        ),
        CheckConstraint("revision >= 0", name="positive_revision"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT"), index=True
    )
    source_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="RESTRICT"), unique=True
    )
    draft_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="RESTRICT")
    )
    approved_response_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="running")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    interpretation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    draft_details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(200))
