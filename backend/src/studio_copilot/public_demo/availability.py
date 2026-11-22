"""Read availability from the public demo Database's fictional session records."""

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from studio_copilot.public_demo.fixtures import CUSTOM_STUDENTS, SATURDAY_TRIAL_CLASSES

CLASS_LEVEL = re.compile(r"\blevel\s*(\d+)\b", re.IGNORECASE)
SESSION_DATE = re.compile(
    r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)(?:\s+(\d{4}))?\b",
    re.IGNORECASE,
)
SESSION_TIME = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(am|pm)\b", re.IGNORECASE)

TRIAL_SESSION_IDS = {
    SATURDAY_TRIAL_CLASSES[1]: "c3ab8737-7f9b-4dc5-be10-42c1ddb8d95d",
    SATURDAY_TRIAL_CLASSES[2]: "df96032d-5ce8-561e-948f-bda79b05887e",
    SATURDAY_TRIAL_CLASSES[3]: "8de15f20-a66d-4e8c-a5d1-6c6834996fed",
}


@lru_cache(maxsize=1)
def _demo_records():
    module = Path(__file__).resolve()
    records = module.with_name("demo_records.json")
    if not records.is_file():
        records = module.parents[4] / "frontend/src/data/examples.v1.json"
    if not records.is_file():
        return {}
    return json.loads(records.read_text(encoding="utf-8"))


def _demo_sessions():
    return {session["id"]: session for session in _demo_records().get("class_sessions", [])}


def _student_record(student_id):
    email = CUSTOM_STUDENTS[student_id].get("email")
    if not email:
        return None
    return next(
        (student for student in _demo_records().get("students", []) if student["email"] == email),
        None,
    )


def recorded_class_level(student_id):
    student = _student_record(student_id)
    level = CLASS_LEVEL.fullmatch(student["highest_level"] or "") if student else None
    return int(level[1]) if level else None


def recorded_makeup_booking(student_id, level):
    student = _student_record(student_id)
    if not student:
        return None
    records = _demo_records()
    classes = {row["id"]: row for row in records.get("classes", [])}
    sessions = _demo_sessions()
    runs = _student_makeup_runs(records, student["id"])
    bookings = {}
    for session_id in {run["draft_details"].get("booking_session_id") for run in runs}:
        session = sessions.get(session_id)
        if session:
            regular_class = classes[session["class_id"]]
            status = _makeup_status(runs, session, student["id"])
            if status and regular_class["level"] == f"Level {level}":
                bookings[session_id] = _booking_details(records, regular_class, session, status)
    return next(iter(bookings.values())) if len(bookings) == 1 else None


def _student_makeup_runs(records, student_id):
    conversations = {
        row["id"] for row in records.get("conversations", []) if row["student_id"] == student_id
    }
    return [
        run
        for run in records.get("agent_runs", [])
        if run["conversation_id"] in conversations and run["interpretation"].get("flow") == "makeup"
    ]


def _makeup_status(runs, session, student_id):
    matching = [
        run for run in runs if run["draft_details"].get("booking_session_id") == session["id"]
    ]
    if student_id in session["students"] and any(
        run["status"] == "approved" and run.get("approved_response_id") for run in matching
    ):
        return "approved"
    if any(run["status"] == "awaiting_review" for run in matching):
        return "awaiting_review"
    return None


def _booking_details(records, regular_class, session, status):
    return {
        "description": _session_description(records, regular_class, session),
        "places": _spaces(session),
        "makeup_status": status,
    }


def followup_booking_facts(student_id, accepted_reply):
    """Resolve a single dated session mentioned in the preceding accepted reply."""
    levels = set(CLASS_LEVEL.findall(accepted_reply))
    dates = set(SESSION_DATE.findall(accepted_reply.lower()))
    times = {
        (int(hour) % 12 + (12 if period == "pm" else 0), int(minute or "0"))
        for hour, minute, period in SESSION_TIME.findall(accepted_reply.lower())
    }
    if len(levels) != 1 or len(dates) != 1 or len(times) > 1:
        return None
    (level,) = levels
    ((day, month, year),) = dates
    records = _demo_records()
    classes = {row["id"]: row for row in records.get("classes", [])}
    matches = []
    for session in _demo_sessions().values():
        regular_class = classes[session["class_id"]]
        starts = datetime.fromisoformat(session["starts_at"])
        if (
            regular_class["level"] == f"Level {level}"
            and starts.day == int(day)
            and starts.strftime("%B").lower() == month
            and (not year or starts.year == int(year))
            and (not times or (starts.hour, starts.minute) in times)
        ):
            matches.append((session, regular_class))
    if len(matches) != 1:
        return None
    session, regular_class = matches[0]
    student = _student_record(student_id)
    status = None
    if student:
        status = _makeup_status(
            _student_makeup_runs(records, student["id"]), session, student["id"]
        )
    return _booking_details(records, regular_class, session, status)


def above_recorded_level(text, recorded_level):
    return recorded_level is not None and any(
        int(level) > recorded_level for level in CLASS_LEVEL.findall(text)
    )


def trial_spaces(recommended_class):
    if not recommended_class:
        return None
    session = _demo_sessions().get(TRIAL_SESSION_IDS.get(recommended_class["description"]))
    if session is None:
        return None
    return _spaces(session)


def _spaces(session):
    return max(0, session["capacity"] - len(set(session["students"])))


def _session_description(records, regular_class, session):
    location = next(
        row["name"] for row in records["locations"] if row["id"] == regular_class["location_id"]
    )
    starts_at = datetime.fromisoformat(session["starts_at"])
    class_name = regular_class["name"].removesuffix(f" · {starts_at:%A}").replace(" · ", " ")
    time = starts_at.strftime("%I:%M %p").lstrip("0").replace(":00", "").lower()
    return f"{class_name}, {starts_at:%A} {starts_at.day} {starts_at:%B %Y} at {time}, {location}"


def class_availability_evidence():
    records = _demo_records()
    classes = {row["id"]: row for row in records.get("classes", [])}
    lines = []
    for session in sorted(records.get("class_sessions", []), key=lambda row: row["starts_at"]):
        regular_class = classes[session["class_id"]]
        description = _session_description(records, regular_class, session)
        spaces = _spaces(session)
        places = "place" if spaces == 1 else "places"
        lines.append(f"- {description}: {spaces} {places} remaining.")
    if not lines:
        return None
    return "Class availability: The fictional Database shows:\n" + "\n".join(lines)
