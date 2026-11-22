"""State transitions for the fictional trial enquiry.

Extracted fields are suggestions, not authority to book a class. The public
catalog provides fictional availability and leaves placement to the teacher.
"""

import re

from studio_copilot.public_demo.availability import above_recorded_level, trial_spaces
from studio_copilot.public_demo.fixtures import SATURDAY_TRIAL_CLASSES

EXPERIENCE_LEVELS = {
    "beginner": 1,
    "level 1": 1,
    "level1": 1,
    "intermediate": 2,
    "level 2": 2,
    "level2": 2,
    "advanced": 3,
    "level 3": 3,
    "level3": 3,
}
TRIAL_LEVEL_REQUEST = re.compile(
    r"\b(?:book|try|reserve|attend|take|request|prefer|would like|['’]d like)"
    r"(?:\s+(?:me|a|an|the|to|trial|in|for|class|adult|ballet|at|of))*"
    r"\s+level\s*(\d+)\b",
    re.IGNORECASE,
)
TRIAL_CONSENT = re.compile(
    r"\s*yes(?:,?\s+(?:please|i(?:'d| would) (?:love|like) to"
    r"(?: (?:book|try it|attend))?))?"
    r"(?:[,!.]?\s+(?:help me (?:to )?)?(?:book|reserve) (?:it|that class|the trial))?[.!\s]*",
    re.IGNORECASE,
)


def _requested_trial_level(email):
    levels = set(TRIAL_LEVEL_REQUEST.findall(email))
    return int(next(iter(levels))) if len(levels) == 1 else None


def strip_quotes(body):
    lines = body.splitlines()
    kept = []
    for i, line in enumerate(lines):
        if re.fullmatch(r"\s*On .+ wrote:\s*", line, re.I) or re.fullmatch(
            r"\s*-{2,}\s*(?:Original Message|Forwarded message)\s*-{2,}\s*", line, re.I
        ):
            break
        if re.match(r"\s*From:\s*\S", line, re.I) and any(
            re.match(r"\s*(?:Sent|Date):\s*\S", following, re.I)
            for following in lines[i + 1 : i + 4]
        ):
            break
        if not re.match(r"\s*>", line):
            kept.append(line)
    return "\n".join(kept).strip()


def initial_state():
    return {
        "intents": [],
        "experience_level": None,
        "preferred_day": None,
        "requested_trial_level": None,
        "recommended_class": None,
        "customer_name": None,
        "booking_status": "not_started",
        "missing_information": [],
        "next_action": "answer",
        "revision": 0,
    }


def update_state(
    previous, extracted, email, offer_confirmed=False, *, recorded_level=None, previous_email=""
):
    state = dict(previous)
    intents = set(state["intents"])
    intents.update(x for x in extracted.get("intents", []) if x in {"trial_enquiry", "faq"})
    state["intents"] = sorted(intents)
    for key in ("experience_level", "preferred_day", "customer_name"):
        value = extracted.get(key)
        if isinstance(value, str) and 0 < len(value.strip()) <= 120:
            state[key] = value.strip()
    requested_level = _requested_trial_level(email)
    if requested_level is not None and "trial_enquiry" in intents:
        state["requested_trial_level"] = requested_level
    elif (
        "trial_enquiry" in intents
        and not state.get("requested_trial_level")
        and TRIAL_CONSENT.fullmatch(email)
    ):
        # Older turns may have described a class without recording the student's choice.
        state["requested_trial_level"] = _requested_trial_level(previous_email)
    state["revision"] += 1
    previous_class = previous.get("recommended_class")
    changed = any(
        state.get(field) != previous.get(field)
        for field in ("experience_level", "preferred_day", "customer_name")
    ) or (
        requested_level is not None
        and requested_level != previous.get("requested_trial_level")
        and (previous_class or {}).get("description") != SATURDAY_TRIAL_CLASSES.get(requested_level)
    )
    negative = bool(
        re.search(r"\b(?:no|not|don.t|do not|cancel|changed my mind|no longer)\b", email, re.I)
    )
    if previous_class and above_recorded_level(previous_class["description"], recorded_level):
        state.update(booking_status="escalated", next_action="staff_review", recommended_class=None)
        return state
    if previous.get("booking_status") in {"awaiting_approval", "approved_mock"}:
        if changed or negative:
            state.update(
                booking_status="escalated", next_action="staff_review", recommended_class=None
            )
        return state
    if "trial_enquiry" in intents:
        requested_level = state.get("requested_trial_level")
        missing = []
        if not state["experience_level"]:
            missing.append("experience_level")
        if not state["preferred_day"] and requested_level is None:
            missing.append("preferred_day")
        state["missing_information"] = missing
        if missing:
            state.update(
                booking_status="collecting", next_action="ask_customer", recommended_class=None
            )
        else:
            experience = state["experience_level"].lower()
            day = (state["preferred_day"] or "Saturday").lower()
            level = requested_level
            if level is None:
                level = EXPERIENCE_LEVELS.get(experience)
            if (
                day != "saturday"
                or level not in SATURDAY_TRIAL_CLASSES
                or (recorded_level is not None and level > recorded_level)
            ):
                state.update(
                    booking_status="escalated", next_action="staff_review", recommended_class=None
                )
            else:
                state["recommended_class"] = {
                    "source_id": "class_information",
                    "description": SATURDAY_TRIAL_CLASSES[level],
                }
                if trial_spaces(state["recommended_class"]) == 0:
                    state.update(booking_status="class_full", next_action="staff_review")
                    return state
                consent = bool(TRIAL_CONSENT.fullmatch(email)) and not (
                    negative
                    or re.search(
                        r"\b(?:instead|elsewhere|different|monday|tuesday|wednesday|thursday|friday|sunday)\b",
                        email,
                        re.I,
                    )
                )
                if previous.get("recommended_class") != state["recommended_class"]:
                    consent = False
                if previous.get("booking_status") == "offered" and not offer_confirmed:
                    consent = False
                if previous.get("booking_status") in {"offered", "collecting_name"} and consent:
                    state["booking_status"] = (
                        "awaiting_approval" if state["customer_name"] else "collecting_name"
                    )
                    state["next_action"] = (
                        "staff_approval" if state["customer_name"] else "ask_customer"
                    )
                    state["missing_information"] = (
                        [] if state["customer_name"] else ["customer_name"]
                    )
                elif (
                    previous.get("booking_status") == "collecting_name"
                    and previous.get("recommended_class") == state["recommended_class"]
                    and state["customer_name"]
                    and not negative
                    and re.fullmatch(
                        r"\s*(?:my name is|i am|i'm)\s+"
                        + re.escape(state["customer_name"])
                        + r"(?:,?\s+thanks?)?[.!\s]*",
                        email,
                        re.I,
                    )
                ):
                    state.update(
                        booking_status="awaiting_approval",
                        next_action="staff_approval",
                        missing_information=[],
                    )
                else:
                    state.update(booking_status="offered", next_action="ask_customer")
    return state
