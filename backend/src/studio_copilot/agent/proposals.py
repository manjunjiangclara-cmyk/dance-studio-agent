"""Booking proposals must point to an actual session retrieved as evidence."""

from datetime import datetime
from uuid import UUID


def confirmation_body(class_name: str, location_name: str, start: datetime) -> str:
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
