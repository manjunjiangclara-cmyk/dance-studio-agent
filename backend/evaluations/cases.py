"""Scenario setup is input; expected values mirror the public agent output contract."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from studio_copilot.agent.contracts import Intent

DATASET = Path(__file__).with_name("scenarios.json")
CATALOG = Path(__file__).with_name("catalog.json")
POLICY = Path(__file__).with_name("policy.yaml")
ClassKey = Literal["monday_level_2", "thursday_level_2", "saturday_level_2"]
SessionKey = Literal["absence", "thursday", "saturday"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudentSetup(Strict):
    registered: bool
    highest_level: str | None


class EnrolmentSetup(Strict):
    class_key: ClassKey
    status: Literal["active", "ended", "cancelled"]
    starts_on: str
    ends_on: str | None = None

    @model_validator(mode="after")
    def ended_has_date(self):
        if self.status == "ended" and self.ends_on is None:
            raise ValueError("An ended enrolment must have ends_on.")
        return self


class ConflictingSession(Strict):
    class_name: str = Field(min_length=1, max_length=200)
    start_offset_minutes: int = Field(ge=-180, le=180)
    duration_minutes: int = Field(gt=0, le=240)


class Setup(Strict):
    student: StudentSetup
    enrolments: list[EnrolmentSetup]
    sessions: list[SessionKey]
    full_sessions: list[SessionKey] = []
    absence_in_past: bool = False
    conflicting_session: ConflictingSession | None = None

    @model_validator(mode="after")
    def validate_references(self):
        if not self.student.registered and self.student.highest_level is not None:
            raise ValueError("An unregistered sender cannot have a pre-existing level.")
        if not self.student.registered and self.enrolments:
            raise ValueError("An unregistered sender cannot have existing enrolments.")
        if len(set(self.sessions)) != len(self.sessions):
            raise ValueError("Session keys must be unique.")
        if self.conflicting_session is not None and (
            not self.student.registered or "thursday" not in self.sessions
        ):
            raise ValueError(
                "A conflicting session requires a registered student and Thursday session."
            )
        if not set(self.full_sessions) <= set(self.sessions):
            raise ValueError("Full sessions must be present in sessions.")
        return self


class ExpectedRouting(Strict):
    intents: list[Intent] = Field(min_length=1)
    needs_clarification: bool | None = None


class ExpectedInterpretation(Strict):
    flow: Literal["makeup", "teacher_handoff"]
    routing: ExpectedRouting | None = None
    absence_date: str | None = None
    preferred_date: str | None = None
    preferred_weekday: str | None = None
    location_preference: str | None = None


class ExpectedDraft(Strict):
    body: str | None = None
    rationale: str | None = None
    questions: list[str] | None = None
    references: list[str] | None = None


class ExpectedOutput(Strict):
    status: Literal["awaiting_review"]
    interpretation: ExpectedInterpretation
    draft_details: ExpectedDraft | None = None


class Checks(Strict):
    required_tools: list[
        Literal["get_enrolments", "search_sessions", "get_locations", "check_absence_notice"]
    ] = []
    clarification_required: bool = False
    forbidden_draft_text: list[str] = []
    contradictory_draft_text: list[str] = []
    required_any_draft_text: list[str] = []
    uncertainty_phrases: list[str] = []
    forbid_numeric_amounts: bool = False
    notice_before_start: bool | None = None


class EmailInput(Strict):
    body: str = Field(min_length=1)


class EmailStep(Strict):
    input: EmailInput
    expected: ExpectedOutput
    checks: Checks = Field(default_factory=Checks)


class Scenario(Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str
    setup: Setup
    steps: list[EmailStep] = Field(min_length=1, max_length=3)
    rubric: list[str] = Field(min_length=1)


def load_scenarios(path: Path = DATASET) -> list[Scenario]:
    scenarios = [Scenario.model_validate(item) for item in json.loads(path.read_text())]
    if not scenarios or len({s.id for s in scenarios}) != len(scenarios):
        raise ValueError("Scenarios must have unique IDs and the dataset must not be empty.")
    return scenarios


def render(value, dates: dict):
    """Expand only known placeholders; JSON and other literal email braces remain intact."""
    if isinstance(value, str):
        for key, replacement in dates.items():
            value = value.replace("{" + key + "}", replacement)
        return value
    if isinstance(value, list):
        return [render(item, dates) for item in value]
    if isinstance(value, dict):
        return {key: render(item, dates) for key, item in value.items()}
    return value
