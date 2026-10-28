"""Typed boundaries shared by real and deterministic fake model adapters."""

from typing import Any, Literal, Protocol, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class State(TypedDict, total=False):
    """Checkpoint payload shared by graph nodes; values stay JSON-serializable."""

    run_id: str
    context: dict
    interpretation: dict
    attempt: int
    evidence: list[dict]
    warnings: list[str]
    feedback: str
    draft: dict
    decision: dict
    response_id: str
    routing: dict
    flow: str


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Preference(StrictModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)


Intent = Literal[
    "makeup",
    "absence",
    "enrolment",
    "cancellation",
    "new_student_enquiry",
    "general_enquiry",
    "unknown",
]


class Routing(StrictModel):
    intents: list[Intent] = Field(min_length=1, max_length=7)
    request_summary: str = Field(min_length=1, max_length=2000)
    needs_clarification: bool
    reason: str = Field(min_length=1, max_length=1000)


class RequestInterpretation(StrictModel):
    """Common fields consumed by memory and review, independent of the selected flow."""

    request_summary: str = Field(min_length=1, max_length=2000)
    missing_details: list[str] = Field(max_length=10)
    enduring_preferences: list[Preference] = Field(max_length=20)


class MakeupInterpretation(RequestInterpretation):
    absence_date: str | None
    preferred_date: str | None
    preferred_weekday: str | None
    preferred_class_name: str | None = Field(default=None, min_length=1, max_length=200)
    preferred_time: str | None = Field(default=None, min_length=1, max_length=20)
    location_preference: str | None
    absence_message_id: UUID | None = None
    absence_class_id: UUID | None = None


class ReviewedMemory(StrictModel):
    request_summary: str = Field(min_length=1, max_length=2000)
    enduring_preferences: list[Preference] = Field(max_length=20)


class Draft(StrictModel):
    body: str = Field(min_length=1, max_length=20_000)
    rationale: str = Field(max_length=4000)
    questions: list[str] = Field(max_length=20)
    references: list[str] = Field(max_length=40)
    booking_session_id: UUID | None = None


class ToolCall(StrictModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolTurn(StrictModel):
    calls: list[ToolCall]
    output: list[dict[str, Any]]


class Review(StrictModel):
    action: Literal["approve", "revise", "reject"]
    expected_revision: int = Field(ge=1)
    body: str | None = Field(default=None, min_length=1, max_length=20_000)
    feedback: str | None = Field(default=None, min_length=1, max_length=4000)


class ModelError(Exception):
    """Safe model boundary failure; provider details must not reach the API."""


class Model(Protocol):
    def route(self, context: dict) -> Routing: ...
    def interpret_makeup(self, context: dict) -> MakeupInterpretation: ...
    def choose_tools(self, context: dict, transcript: list[dict]) -> ToolTurn: ...
    def draft(self, context: dict) -> Draft: ...
    def reconcile(self, context: dict) -> ReviewedMemory: ...
