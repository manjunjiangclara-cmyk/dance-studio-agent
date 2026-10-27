"""Booking proposals must point to an actual session retrieved as evidence."""

from uuid import UUID


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
