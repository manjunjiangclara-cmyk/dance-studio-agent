"""Validated, editable email scenarios and their measurable expectations."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_copilot.agent.contracts import Intent

DATASET = Path(__file__).with_name("scenarios.json")


class Expectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: Literal["makeup", "teacher_handoff"]
    intents: list[Intent] = Field(min_length=1)
    fields: dict[
        Literal["absence_date", "preferred_date", "preferred_weekday", "preferred_class_name"],
        str | None,
    ] = {}
    missing_details: bool | None = None
    proposal: Literal["thursday", "saturday", "none"] = "none"
    required_tools: list[
        Literal[
            "get_timetable",
            "get_enrolments",
            "search_sessions",
            "get_locations",
            "check_absence_notice",
        ]
    ] = []
    notice_before_start: bool | None = None
    forbidden_text: list[str] = []
    contradictory_text: list[str] = []
    required_any_text: list[str] = []
    forbid_specific_amounts: bool = False
    absence_verified: bool | None = None
    attendance_status: Literal["attended", "absent", "unknown"] | None = None
    option_contains: list[Literal["thursday", "saturday"]] = []
    option_excludes: list[Literal["thursday", "saturday"]] = []
    verification_before_search: bool = False
    excluded_candidates: dict[
        Literal["thursday", "saturday"],
        Literal[
            "full",
            "already_in_session",
            "past",
            "above_attended_level",
            "unknown_level",
            "overlapping_session",
            "requested_class_mismatch",
            "requested_time_mismatch",
        ],
    ] = {}


class StudentSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    highest_level: str = "Level 2"


class EnrolmentSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_key: Literal["monday_level_2", "thursday_level_2", "saturday_level_2"]
    status: Literal["active"] = "active"


class ConflictingBooking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: str = Field(min_length=1, max_length=200)
    start_offset_minutes: int = Field(ge=-180, le=180)
    duration_minutes: int = Field(gt=0, le=240)


class ScenarioSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student: StudentSetup
    enrolments: list[EnrolmentSetup]
    level_order: list[str] = ["Level 1", "Level 2", "Level 3"]
    attended_level: str | None = "Level 2"
    absence_attendance: Literal["attended", "absent", "unknown"] = "unknown"
    thursday_level: str = "Level 2"
    saturday_level: str = "Level 2"
    conflicting_booking: ConflictingBooking | None = None
    session_rosters: dict[
        Literal["absence", "thursday", "saturday"], list[Literal["student", "other_student"]]
    ]


class EmailStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    expect: Expectation
    received_before_absence: bool = False


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str
    sender: Literal["known", "new"] = "known"
    fixture: Literal[
        "normal", "no_sessions", "no_enrolments", "late_notice", "full", "past_absence"
    ] = "normal"
    setup: ScenarioSetup
    emails: list[EmailStep] = Field(min_length=1, max_length=3)
    review: Literal[
        "none",
        "approve",
        "approve_twice",
        "reject",
        "revise",
        "restart_approve",
        "capacity_conflict",
    ] = "none"
    review_body: str | None = Field(default=None, min_length=1)
    feedback: str = "Please ask which location I prefer before proposing a booking."
    rubric: list[str] = Field(min_length=1)


def load_scenarios(path: Path = DATASET) -> list[Scenario]:
    scenarios = [Scenario.model_validate(item) for item in json.loads(path.read_text())]
    if not scenarios or len({item.id for item in scenarios}) != len(scenarios):
        raise ValueError("The dataset must contain scenarios with unique IDs.")
    return scenarios
