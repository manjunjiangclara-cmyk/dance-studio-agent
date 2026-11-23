"""Validate and format automatic trial bookings against fictional records only."""

import re
from zoneinfo import ZoneInfo

from studio_copilot.agent.contracts import Draft
from studio_copilot.agent.proposals import confirmation_body

TRIAL = re.compile(r"\btrial\b", re.IGNORECASE)
BOOK_REQUEST = re.compile(
    r"(?:^|[.!?\n]\s+)(?:(?:yes|hi|hello)[, ]+)?"
    r"(?:please\s+(?:book|reserve)|(?:can|could|would) you\s+(?:book|reserve)|"
    r"(?:book|reserve)\s+(?:me|my place|my trial)|"
    r"i(?:['’]d like| would like| want) to (?:book|reserve))\b",
    re.IGNORECASE,
)
CONDITIONAL = re.compile(
    r"\b(?:no|not|don['’]t|do not|cannot|can['’]t|if|unless|but|instead|or|might|"
    r"before|maybe|how much|price|cost|fees?|whenever|ongoing|full term)\b",
    re.IGNORECASE,
)
ACCEPT = re.compile(
    r"(?:yes[,\s]+)?(?:please\s+)?(?:book (?:it|me in)|go ahead|please)"
    r"(?:[.! ]+thank(?:s| you))?[.! ]*",
    re.IGNORECASE,
)
OFFER = re.compile(
    r"\b(?:would you like|if you(?:['’]d| would) like|shall i)\b"
    r"[^.!?\n]{0,85}\b(?:book|reserve|join|try)\b",
    re.IGNORECASE,
)
LEVEL = re.compile(r"\blevel\s*([123])\b", re.IGNORECASE)
CLOCK = re.compile(r"\b(1[0-2]|[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b", re.IGNORECASE)
TIME_RANGE = re.compile(
    r"\b(1[0-2]|[1-9])(:[0-5]\d)?\s*([ap]m)?\s*[-–—]\s*"
    r"(?:1[0-2]|[1-9])(?::[0-5]\d)?\s*([ap]m)\b",
    re.IGNORECASE,
)
CALENDAR = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|"
    r"september|october|november|december)(?:\s+(\d{4}))?\b",
    re.IGNORECASE,
)
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def latest_text(body):
    lines = []
    for line in body.splitlines():
        if re.fullmatch(r"\s*On .+ wrote:\s*", line, re.I) or re.match(
            r"\s*(?:From:|--+\s*(?:Original Message|Forwarded message))", line, re.I
        ):
            break
        if not line.lstrip().startswith(">"):
            lines.append(line)
    return "\n".join(lines).strip()


def _local_start(session):
    return session.starts_at.astimezone(ZoneInfo(session.regular_class.location.timezone))


def exact_session(records, text):
    levels = set(LEVEL.findall(text))
    clock_text = TIME_RANGE.sub(
        lambda match: f"{match[1]}{match[2] or ''} {match[3] or match[4]}", text
    )
    times = {
        (int(hour) % 12 + (12 if period.lower() == "p" else 0), int(minute or 0))
        for hour, minute, period in CLOCK.findall(clock_text)
    }
    words = set(re.findall(r"\b\w+\b", text.casefold()))
    weekdays = words.intersection(WEEKDAYS)
    dates = {(int(day), month.lower(), year) for day, month, year in CALENDAR.findall(text)}
    iso_dates = set(ISO_DATE.findall(text))
    if len(levels) != 1 or len(times) != 1 or not (weekdays or dates or iso_dates):
        return None
    venue = re.search(r"\b[ap]m\s+(?:in|at)\s+([^,.!?;\n]+)", text, re.IGNORECASE)
    venue_text = venue[1] if venue else text
    locations = {
        row["id"]
        for row in records.locations.values()
        if re.search(
            r"\b" + re.escape(row["name"].rsplit(" · ", 1)[-1]) + r"\b",
            venue_text,
            re.IGNORECASE,
        )
    }
    if venue and not locations:
        return None
    candidates = []
    for session_id in records.session_rows:
        session = records.session(session_id)
        start = _local_start(session)
        if (
            session.starts_at > records.now
            and session.regular_class.level.casefold() == f"level {next(iter(levels))}"
            and (start.hour, start.minute) in times
            and (not weekdays or weekdays == {start.strftime("%A").lower()})
            and (
                not dates
                or all(
                    day == start.day
                    and month == start.strftime("%B").lower()
                    and (not year or year == str(start.year))
                    for day, month, year in dates
                )
            )
            and (not iso_dates or iso_dates == {start.date().isoformat()})
            and (not locations or locations == {str(session.regular_class.location_id)})
        ):
            candidates.append(session)
    return candidates[0] if len(candidates) == 1 else None


def previous_offer(records, contact, reply, evidence):
    interest = contact.get("trial_interest") or TRIAL.search(latest_text(contact["source"]["body"]))
    if not interest or reply.count("?") > 1 or not OFFER.search(reply):
        return None
    session = exact_session(records, reply)
    if session is not None and any(
        entry["tool"] == "search_sessions"
        and any(item["id"] == str(session.id) for item in entry["result"].get("items", []))
        for entry in evidence
    ):
        return str(session.id)
    return None


def eligible_trial(records, context):
    if not context.get("walkthrough"):
        return None
    text = latest_text(context["source"]["body"])
    if CONDITIONAL.search(text):
        return None
    if ACCEPT.fullmatch(text) and (offered := context.get("previous_trial_offer")):
        session = records.session(offered)
    elif BOOK_REQUEST.search(text) and (TRIAL.search(text) or context.get("trial_interest")):
        session = exact_session(records, text)
    else:
        return None
    if (
        session is None
        or session.starts_at <= records.now
        or len(session.students) >= session.capacity
    ):
        return None
    student = context["student"]
    if str(session.id) in context.get("simulated_trials", []) or any(
        str(student_id) == student["id"] for student_id in session.students
    ):
        return None
    level = session.regular_class.level.casefold()
    # The public fixture supports beginner trials. Higher levels need recorded placement.
    levels = context["policy"]["level_order"]
    rank = {name.casefold(): index for index, name in enumerate(levels)}
    recorded = str(student.get("highest_level") or "").casefold()
    if level != "level 1" and rank.get(recorded, -1) < rank.get(level, len(levels)):
        return None
    return session


def trial_draft(records, state):
    if state.get("flow") == "makeup" or state.get("question_resolutions"):
        return None
    if any(
        item.get("tool") == "document_answer" and item.get("result", {}).get("status") == "answered"
        for item in state.get("evidence", [])
    ):
        return None
    context = state["context"]
    if not (session := eligible_trial(records, context)):
        return None
    return Draft(
        body=confirmation_body(
            session.regular_class.name,
            session.regular_class.location.name,
            _local_start(session),
            context["student"].get("name"),
        ),
        rationale="The fictional student requested one available trial session.",
        questions=[],
        references=["public-trial:" + str(session.id)],
    )
