from datetime import timedelta

import pytest
from pydantic import ValidationError

from studio_copilot.agent.policy import load_policy
from studio_copilot.agent.tools import execute_tool

pytestmark = pytest.mark.integration


def test_notice_is_strictly_before_start_and_policy_is_editable(db, catalog, tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        'version: "test"\nabsence_notice_before_start: true\nexplanation: "Test policy"\n'
    )
    policy = load_policy(path)
    start = catalog.class_session.starts_at
    for notice_at, expected in [
        (start - timedelta(seconds=1), True),
        (start, False),
        (start + timedelta(seconds=1), False),
    ]:
        result = execute_tool(
            db,
            catalog.student.id,
            notice_at,
            policy,
            "check_absence_notice",
            {"session_id": str(catalog.class_session.id)},
        )
        assert result["notice_before_start"] is expected
        assert result["makeup_eligibility"] == "unknown"
    path.write_text(
        'version: "changed"\nabsence_notice_before_start: false\nexplanation: "Changed policy"\n'
    )
    changed = execute_tool(
        db,
        catalog.student.id,
        start,
        load_policy(path),
        "check_absence_notice",
        {"session_id": str(catalog.class_session.id)},
    )
    assert changed["notice_before_start"] is None
    assert changed["explanation"] == "Changed policy"


def test_session_search_returns_local_dates_and_does_not_promise_makeup_capacity(db, catalog):
    result = execute_tool(
        db,
        catalog.student.id,
        catalog.class_session.starts_at,
        load_policy(),
        "search_sessions",
        {
            "from_date": "2027-02-08",
            "to_date": "2027-02-08",
            "weekday": 0,
            "level": "Level 2",
            "location_id": None,
        },
    )
    assert result["items"][0]["id"] == str(catalog.class_session.id)
    assert "unknown" in result["items"][0]["makeup_availability"]
    assert result["items"][0]["placement"] == "requires policy or teacher judgment"


def test_tools_reject_student_override_and_unbounded_date_ranges(db, catalog):
    with pytest.raises(ValidationError):
        execute_tool(
            db,
            catalog.student.id,
            catalog.class_session.starts_at,
            load_policy(),
            "get_enrolments",
            {"on_date": "2027-02-08", "student_id": str(catalog.student.id)},
        )
    with pytest.raises(ValidationError):
        execute_tool(
            db,
            catalog.student.id,
            catalog.class_session.starts_at,
            load_policy(),
            "search_sessions",
            {
                "from_date": "2027-01-01",
                "to_date": "2028-01-01",
                "weekday": None,
                "level": None,
                "location_id": None,
            },
        )
