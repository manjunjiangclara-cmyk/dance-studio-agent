import pytest
from fastapi.testclient import TestClient

from studio_copilot.api.app import create_app

from .helpers import post


@pytest.fixture
def client(db_engine):
    with TestClient(
        create_app(db_engine, admin_token="test-admin-token"),
        headers={"Authorization": "Bearer test-admin-token"},
    ) as client:
        yield client


@pytest.fixture
def records(client):
    term = post(
        client, "/terms", {"name": "Term 1", "starts_on": "2027-02-01", "ends_on": "2027-03-31"}
    )
    a = post(client, "/locations", {"name": "A", "address": "Fictional A"})
    b = post(client, "/locations", {"name": "B", "address": "Fictional B"})
    source = post(
        client,
        "/classes",
        {"term_id": term["id"], "location_id": a["id"], "name": "Monday", "level": "Level 2"},
    )
    target = post(
        client,
        "/classes",
        {"term_id": term["id"], "location_id": b["id"], "name": "Thursday", "level": "Level 2"},
    )
    source_session = post(
        client,
        "/sessions",
        {
            "class_id": source["id"],
            "starts_at": "2027-02-08T18:00:00+11:00",
            "ends_at": "2027-02-08T19:00:00+11:00",
            "capacity": 2,
        },
    )
    target_session = post(
        client,
        "/sessions",
        {
            "class_id": target["id"],
            "starts_at": "2027-02-11T18:00:00+11:00",
            "ends_at": "2027-02-11T19:00:00+11:00",
            "capacity": 1,
        },
    )
    student = post(
        client,
        "/students",
        {"display_name": "Alex Example", "email": "Alex@Example.com", "highest_level": "Level 2"},
    )
    enrolment = post(
        client,
        "/enrolments",
        {"student_id": student["id"], "class_id": source["id"], "starts_on": "2027-02-01"},
    )
    return {
        "term": term,
        "a": a,
        "b": b,
        "source": source,
        "target": target,
        "source_session": source_session,
        "target_session": target_session,
        "student": student,
        "enrolment": enrolment,
    }
