"""Booking proposals must point to an actual session retrieved as evidence."""

from datetime import datetime
from uuid import UUID

from studio_copilot.agent.draft_voice import student_greeting


def session_description(class_name: str, location_name: str, start: datetime) -> str:
    if start.utcoffset() is None or not class_name or not location_name:
        raise ValueError("Incomplete session details")
    label, _, suffix = class_name.rpartition(" · ")
    if suffix.casefold() == start.strftime("%A").casefold() and label:
        class_name = label
    class_label = class_name.replace(" · ", " ")
    location_label = location_name.replace(" · ", ", ")
    date_label = f"{start:%A} {start.day} {start:%B %Y}"
    clock = start.strftime("%I:%M").lstrip("0").removesuffix(":00")
    meridiem = start.strftime("%p").lower()
    return f"{class_label} at {location_label} on {date_label} at {clock} {meridiem}"


def confirmation_body(
    class_name: str, location_name: str, start: datetime, student_name: str | None
) -> str:
    description = session_description(class_name, location_name, start)
    return (
        f"{student_greeting(student_name)}\n\n"
        f"Thanks for letting me know. I've booked you into {description}.\n\nSee you then!"
    )


def legacy_confirmation_body(class_name: str, location_name: str, start: datetime) -> str:
    """Match booking drafts that were already in the review queue before the copy change."""
    if start.utcoffset() is None or not class_name or not location_name:
        raise ValueError("Incomplete session details")
    return (
        f"Your makeup is confirmed for {class_name} on "
        f"{start.strftime('%A, %d %B %Y at %I:%M %p')} at {location_name}."
    )


def candidate_session_ids(evidence: list[dict]) -> set[UUID]:
    result = set()
    for item in evidence:
        if item.get("tool") != "search_sessions":
            continue
        for session in item.get("result", {}).get("items", []):
            try:
                result.add(UUID(str(session["id"])))
            except (KeyError, ValueError, TypeError):
                continue
    return result
