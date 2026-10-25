"""Read-only query tools scoped to the run's student. No arbitrary SQL or write tools."""

from datetime import date, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from sqlalchemy import select, text

from studio_copilot.agent.contracts import StrictModel
from studio_copilot.persistence.models import ClassSession, Location, Student


class EnrolmentQuery(StrictModel):
    on_date: date


class SessionQuery(StrictModel):
    from_date: date
    to_date: date
    weekday: int | None = Field(ge=0, le=6)
    level: str | None = Field(max_length=100)
    location_id: UUID | None

    @model_validator(mode="after")
    def valid_window(self):
        if not self.from_date <= self.to_date <= self.from_date + timedelta(days=60):
            raise ValueError("Search window must be ordered and at most 60 days.")
        return self


class LocationQuery(StrictModel):
    location_id: UUID | None


class NoticeQuery(StrictModel):
    session_id: UUID


TOOL_TYPES = {
    "get_enrolments": (EnrolmentQuery, "Get this student's enrolments on a specific local date."),
    "search_sessions": (
        SessionQuery,
        "Find up to 30 timetable sessions by local dates, weekday (Monday=0), level or location. "
        "These are candidates, not guaranteed makeup places or placement approval.",
    ),
    "get_locations": (LocationQuery, "Read studio address and timezone information."),
    "check_absence_notice": (
        NoticeQuery,
        "Check enrolled-session notice timing. Does not establish makeup entitlement.",
    ),
}


def tool_definitions():
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": schema.model_json_schema(),
            "strict": True,
        }
        for name, (schema, description) in TOOL_TYPES.items()
    ]


def enrolments(student: Student, on_date: date | None = None) -> list[dict]:
    return [
        {
            "id": str(e.id),
            "class_id": str(e.class_id),
            "class_name": e.regular_class.name,
            "level": e.regular_class.level,
            "term": e.regular_class.term.name,
            "location_id": str(e.regular_class.location_id),
            "starts_on": e.starts_on.isoformat(),
            "ends_on": e.ends_on.isoformat() if e.ends_on else None,
            "status": e.status,
        }
        for e in student.enrolment_history
        if on_date is None or e.is_active_on(on_date)
    ]


def execute_tool(
    db, student_id: UUID, source_at, policy: dict, name: str, args: dict
) -> dict[str, Any]:
    schema = TOOL_TYPES[name][0]
    query = schema.model_validate(args)
    # Applies to all DB queries in this tool transaction.
    db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
    student = db.get(Student, student_id)
    if name == "get_enrolments":
        items = enrolments(student, query.on_date)
        return {"items": items, "references": ["enrolment:" + e["id"] for e in items]}
    if name == "get_locations":
        statement = select(Location).order_by(Location.id)
        if query.location_id:
            statement = statement.where(Location.id == query.location_id)
        items = [
            {
                "id": str(location.id),
                "name": location.name,
                "address": location.address,
                "timezone": location.timezone,
            }
            for location in db.scalars(statement.limit(30))
        ]
        return {"items": items, "references": ["location:" + item["id"] for item in items]}
    if name == "search_sessions":
        # Bound in SQL before applying local-day/weekday filters; per-location timezone matters.
        from datetime import UTC, datetime, time

        start = datetime.combine(query.from_date - timedelta(days=1), time.min, UTC)
        end = datetime.combine(query.to_date + timedelta(days=2), time.min, UTC)
        statement = (
            select(ClassSession)
            .where(ClassSession.starts_at >= start, ClassSession.starts_at < end)
            .order_by(ClassSession.starts_at, ClassSession.id)
        )
        # Restrict class filters in SQL; never fetch student PII or other students' messages.
        from studio_copilot.persistence.models import StudioClass

        statement = statement.join(StudioClass)
        if query.level:
            statement = statement.where(StudioClass.level == query.level)
        if query.location_id:
            statement = statement.where(StudioClass.location_id == query.location_id)
        items = []
        for session in db.scalars(statement.limit(501)):
            local = session.starts_at.astimezone(ZoneInfo(session.regular_class.location.timezone))
            if not query.from_date <= local.date() <= query.to_date:
                continue
            if query.weekday is not None and local.weekday() != query.weekday:
                continue
            items.append(
                {
                    "id": str(session.id),
                    "class_id": str(session.class_id),
                    "class_name": session.regular_class.name,
                    "level": session.regular_class.level,
                    "prerequisites": session.regular_class.prerequisites,
                    "location_id": str(session.regular_class.location_id),
                    "starts_at": local.isoformat(),
                    "ends_at": session.ends_at.isoformat(),
                    "capacity": session.capacity,
                    "makeup_availability": "unknown; regular roster is not makeup inventory",
                    "placement": "requires policy or teacher judgment",
                }
            )
            if len(items) == 30:
                break
        return {"items": items, "limit": 30, "references": ["session:" + s["id"] for s in items]}
    session = db.get(ClassSession, query.session_id)
    if session is None:
        return {"error": "Session not found.", "references": []}
    local_date = session.starts_at.astimezone(
        ZoneInfo(session.regular_class.location.timezone)
    ).date()
    if not any(e.class_id == session.class_id for e in student.active_enrolments_on(local_date)):
        return {
            "error": "Student is not enrolled in this session's class on that date.",
            "references": [],
        }
    return {
        "rule_enabled": policy["absence_notice_before_start"],
        "notice_before_start": source_at < session.starts_at
        if policy["absence_notice_before_start"]
        else None,
        "makeup_eligibility": "unknown",
        "explanation": policy["explanation"],
        "references": ["policy:" + policy["version"], "session:" + str(session.id)],
    }
