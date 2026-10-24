"""HTTP contracts. Business changes to enrolments use explicit operations."""

from datetime import date, datetime
from typing import Annotated, Any, ClassVar, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)]
Subject = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Capacity = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Patch(Input):
    required_values: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for name in self.required_values & self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")
        return self


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class StudentCreate(Input):
    display_name: Name
    email: EmailStr
    highest_level: Label | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class StudentPatch(Patch):
    required_values = frozenset({"display_name", "email", "context"})
    display_name: Name | None = None
    email: EmailStr | None = None
    highest_level: Label | None = None
    context: dict[str, Any] | None = None


class StudentRead(Record):
    display_name: str
    email: str
    highest_level: str | None
    context: dict[str, Any]


class EnrolmentRead(Record):
    student_id: UUID
    class_id: UUID
    starts_on: date
    ends_on: date | None
    status: Literal["active", "ended", "cancelled"]


class StudentDetail(StudentRead):
    as_of: date
    current_enrolments: list[EnrolmentRead]
    enrolment_history: list[EnrolmentRead]


class TermCreate(Input):
    name: Label
    starts_on: date
    ends_on: date


class TermPatch(Patch):
    required_values = frozenset({"name", "starts_on", "ends_on"})
    name: Label | None = None
    starts_on: date | None = None
    ends_on: date | None = None


class TermRead(Record):
    name: str
    starts_on: date
    ends_on: date


class TimezoneInput(Input):
    @field_validator("timezone", check_fields=False)
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ValueError("Use a valid IANA timezone.") from error
        return value


class LocationCreate(TimezoneInput):
    name: Name
    address: Body
    timezone: Label = "Australia/Melbourne"


class LocationPatch(Patch, TimezoneInput):
    required_values = frozenset({"name", "address", "timezone"})
    name: Name | None = None
    address: Body | None = None
    timezone: Label | None = None


class LocationRead(Record):
    name: str
    address: str
    timezone: str


class ClassCreate(Input):
    term_id: UUID
    location_id: UUID
    name: Name
    level: Label
    prerequisites: Body | None = None


class ClassPatch(Patch):
    required_values = frozenset({"name", "level"})
    name: Name | None = None
    level: Label | None = None
    prerequisites: Body | None = None


class ClassRead(Record):
    term_id: UUID
    location_id: UUID
    name: str
    level: str
    prerequisites: str | None


class SessionCreate(Input):
    class_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    capacity: Capacity


class SessionPatch(Patch):
    required_values = frozenset({"starts_at", "ends_at", "capacity"})
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    capacity: Capacity | None = None


class SessionRead(Record):
    class_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int


class EnrolmentCreate(Input):
    student_id: UUID
    class_id: UUID
    starts_on: date
    ends_on: date | None = None


class EnrolmentEnd(Input):
    ends_on: date


class EnrolmentChange(Input):
    new_class_id: UUID
    effective_on: date


class EnrolmentChangeRead(BaseModel):
    previous: EnrolmentRead
    replacement: EnrolmentRead


class ConversationCreate(Input):
    student_id: UUID
    subject: Subject | None = None


class ConversationPatch(Patch):
    subject: Subject | None = None


class ConversationRead(Record):
    student_id: UUID
    subject: str | None


class MessageCreate(Input):
    kind: Literal["student_email", "assistant_draft", "staff_note"]
    body: Body
    occurred_at: AwareDatetime | None = None


class DraftPatch(Input):
    body: Body


class MessageRead(Record):
    conversation_id: UUID
    kind: Literal["student_email", "assistant_draft", "staff_note"]
    body: str
    occurred_at: datetime
