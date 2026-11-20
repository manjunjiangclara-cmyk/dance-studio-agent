"""State transitions for the fictional trial enquiry.

Extracted fields are suggestions, not authority to book a class. The public
catalog does not establish a beginner placement or live availability.
"""

import re


def strip_quotes(body):
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.fullmatch(r"\s*On .+ wrote:\s*", line, re.I) or re.fullmatch(
            r"\s*-{2,}\s*(?:Original Message|Forwarded message)\s*-{2,}\s*", line, re.I
        ):
            return "\n".join(lines[:i]).strip()
    return body.strip()


def initial_state():
    return {
        "intents": [],
        "experience_level": None,
        "preferred_day": None,
        "recommended_class": None,
        "customer_name": None,
        "booking_status": "not_started",
        "missing_information": [],
        "next_action": "answer",
        "revision": 0,
    }


def update_state(previous, extracted, email, previous_reply=""):
    state = dict(previous)
    intents = set(state["intents"])
    intents.update(x for x in extracted.get("intents", []) if x in {"trial_enquiry", "faq"})
    state["intents"] = sorted(intents)
    for key in ("experience_level", "preferred_day", "customer_name"):
        value = extracted.get(key)
        if isinstance(value, str) and 0 < len(value.strip()) <= 120:
            state[key] = value.strip()
    state["revision"] += 1
    if "trial_enquiry" in intents:
        missing = [key for key in ("experience_level", "preferred_day") if not state[key]]
        state["missing_information"] = missing
        if missing:
            state.update(
                booking_status="collecting", next_action="ask_customer", recommended_class=None
            )
        else:
            experience = state["experience_level"].lower()
            day = state["preferred_day"].lower()
            suitable = experience in {"intermediate", "level 2", "level2"} and day == "saturday"
            if not suitable:
                state.update(
                    booking_status="escalated", next_action="staff_review", recommended_class=None
                )
            else:
                state["recommended_class"] = {
                    "source_id": "class_information",
                    "description": (
                        "Adult Ballet Level 2, Saturday 13 February 2027 at 6 pm, "
                        "Merri Ballet Brunswick"
                    ),
                }
                consent = bool(
                    re.fullmatch(r"\s*yes(?:,?\s+please)?[.!\s]*", email, re.I)
                    or re.search(
                        r"\b(?:i(?: would|'d) like to|please) (?:book|reserve)\b", email, re.I
                    )
                ) and not re.search(r"\b(?:no|not|don.t|do not|cancel)\b", email, re.I)
                if previous.get("recommended_class") != state["recommended_class"]:
                    consent = False
                if previous.get("booking_status") == "offered" and not (
                    re.search(r"level\s*2", previous_reply, re.I)
                    and re.search(r"\btrial\b", previous_reply, re.I)
                    and "?" in previous_reply
                ):
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
                    and not re.search(r"\b(?:no|not|don.t|cancel)\b", email, re.I)
                ):
                    state.update(
                        booking_status="awaiting_approval",
                        next_action="staff_approval",
                        missing_information=[],
                    )
                else:
                    state.update(booking_status="offered", next_action="ask_customer")
    return state
