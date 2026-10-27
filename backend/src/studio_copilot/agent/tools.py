"""Read-only query tools scoped to the run's student. No arbitrary SQL or write tools."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from sqlalchemy import select, text

from studio_copilot.administration.service import session_attendee_ids
from studio_copilot.agent.contracts import StrictModel
from studio_copilot.persistence.models import (
    ClassSession,
    Location,
    Message,
    Student,
    StudioClass,
    Term,
)


class TimetableQuery(StrictModel):
    pass


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
    absence_message_id: UUID | None


TOOL_TYPES = {
    "get_timetable": (
        TimetableQuery,
        "Read the class catalog for current and future terms, with term dates, locations, "
        "and up to eight upcoming dated sessions per class (local weekday/time). "
        "Use this first to resolve class/day questions or discover term dates before searching "
        "sessions. Truncation flags mean the result is incomplete. Does not grant enrolment.",
    ),
    "get_enrolments": (EnrolmentQuery, "Get this student's enrolments on a specific local date."),
    "search_sessions": (
        SessionQuery,
        "Find up to 30 timetable sessions by local dates, weekday (Monday=0), level or location. "
        "These are candidates, not guaranteed makeup places or placement approval.",
    ),
    "get_locations": (LocationQuery, "Read studio address and timezone information."),
    "check_absence_notice": (
        NoticeQuery,
        "Check enrolled-session notice timing. Supply absence_message_id for the student email "
        "that actually notifies this absence, including an earlier email for a follow-up. "
        "Use null if that email cannot be established; timing will be unknown. "
        "Does not establish makeup entitlement.",
    ),
}


def tool_definitions():
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": {**schema.model_json_schema(), "required": list(schema.model_fields)},
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


def timetable(db, reference_at: datetime) -> dict:
    """Bounded catalog discovery, including future terms outside a 60-day session search."""
    classes = list(
        db.scalars(
            select(StudioClass)
            .join(Term)
            .where(Term.ends_on >= reference_at.date() - timedelta(days=1))
            .order_by(Term.starts_on, StudioClass.id)
            .limit(31)
        )
    )
    items, references = [], []
    for cls in classes[:30]:
        zone = ZoneInfo(cls.location.timezone)
        local_date = reference_at.astimezone(zone).date()
        if cls.term.ends_on < local_date:
            continue
        sessions = list(
            db.scalars(
                select(ClassSession)
                .where(ClassSession.class_id == cls.id, ClassSession.starts_at >= reference_at)
                .order_by(ClassSession.starts_at, ClassSession.id)
                .limit(9)
            )
        )
        items.append(
            {
                "id": str(cls.id),
                "name": cls.name,
                "level": cls.level,
                "prerequisites": cls.prerequisites,
                "term": {
                    "id": str(cls.term_id),
                    "name": cls.term.name,
                    "starts_on": cls.term.starts_on.isoformat(),
                    "ends_on": cls.term.ends_on.isoformat(),
                    "current_at_source": cls.term.starts_on <= local_date <= cls.term.ends_on,
                },
                "location": {
                    "id": str(cls.location_id),
                    "name": cls.location.name,
                    "timezone": cls.location.timezone,
                },
                "upcoming_sessions": [
                    {
                        "id": str(session.id),
                        "starts_at": session.starts_at.astimezone(zone).isoformat(),
                        "ends_at": session.ends_at.astimezone(zone).isoformat(),
                        "weekday": session.starts_at.astimezone(zone).strftime("%A"),
                    }
                    for session in sessions[:8]
                ],
                "sessions_truncated": len(sessions) > 8,
            }
        )
        references.extend(
            ["class:" + str(cls.id), "term:" + str(cls.term_id), "location:" + str(cls.location_id)]
        )
        references.extend("session:" + str(session.id) for session in sessions[:8])
    return {
        "items": items,
        "limit": 30,
        "truncated": len(classes) > 30,
        "reference_at": reference_at.isoformat(),
        "references": list(dict.fromkeys(references)),
    }


def execute_tool(
    db,
    student_id: UUID,
    source_message_id: UUID | None,
    policy: dict,
    name: str,
    args: dict,
) -> dict[str, Any]:
    schema = TOOL_TYPES[name][0]
    query = schema.model_validate(args)
    # Applies to all DB queries in this tool transaction.
    db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
    student = db.get(Student, student_id)
    if name == "get_timetable":
        source = db.get(Message, source_message_id) if source_message_id else None
        reference_at = source.occurred_at if source is not None else datetime.now(UTC)
        return timetable(db, reference_at)
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
        from datetime import time

        start = datetime.combine(query.from_date - timedelta(days=1), time.min, UTC)
        end = datetime.combine(query.to_date + timedelta(days=2), time.min, UTC)
        statement = (
            select(ClassSession)
            .where(ClassSession.starts_at >= start, ClassSession.starts_at < end)
            .order_by(ClassSession.starts_at, ClassSession.id)
        )
        # Restrict class filters in SQL; never fetch student PII or other students' messages.
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
                    "remaining_places": max(
                        0, session.capacity - len(session_attendee_ids(db, session))
                    ),
                    "makeup_availability": (
                        "eligibility unknown until teacher approval; capacity rechecked on booking"
                    ),
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
    source = db.get(Message, source_message_id) if source_message_id else None
    notice = db.get(Message, query.absence_message_id) if query.absence_message_id else None
    # The model selects provenance, never timestamps. Scope it to this conversation and
    # exclude messages received after the run's source, even if they were backdated.
    if not (
        source is not None
        and source.kind == "student_email"
        and source.conversation.student_id == student_id
        and notice is not None
        and notice.kind == "student_email"
        and notice.conversation_id == source.conversation_id
        and notice.occurred_at <= source.occurred_at
        and notice.created_at <= source.created_at
    ):
        notice = None
    references = ["policy:" + policy["version"], "session:" + str(session.id)]
    if notice is not None:
        references.append("message:" + str(notice.id))
    return {
        "rule_enabled": policy["absence_notice_before_start"],
        "notice_before_start": notice.occurred_at < session.starts_at
        if policy["absence_notice_before_start"] and notice is not None
        else None,
        "absence_message_id": str(notice.id) if notice else None,
        "timing_unknown_reason": None
        if notice
        else "Absence notification could not be established.",
        "makeup_eligibility": "unknown",
        "explanation": policy["explanation"],
        "references": references,
    }
