from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.api.app import create_app
from studio_copilot.demo import seed_demo
from studio_copilot.persistence.models import Student

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_engine):
    with TestClient(
        create_app(db_engine, admin_token="test-admin-token"),
        headers={"Authorization": "Bearer test-admin-token"},
    ) as client:
        yield client


def post(client, path, body):
    response = client.post(f"/api/v1{path}", json=body)
    assert response.status_code == 201, response.text
    return response.json()


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


def test_class_change_preserves_history_and_updates_rosters(client, records):
    r = records
    changed = client.post(
        f"/api/v1/enrolments/{r['enrolment']['id']}/change",
        json={"new_class_id": r["target"]["id"], "effective_on": "2027-02-10"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["previous"]["ends_on"] == "2027-02-09"
    assert changed.json()["previous"]["status"] == "ended"
    assert changed.json()["replacement"]["class_id"] == r["target"]["id"]
    for day, expected in [("2027-02-09", r["source"]["id"]), ("2027-02-10", r["target"]["id"])]:
        profile = client.get(
            f"/api/v1/students/{r['student']['id']}", params={"on_date": day}
        ).json()
        assert len(profile["enrolment_history"]) == 2
        assert profile["current_enrolments"][0]["class_id"] == expected
        assert profile["as_of"] == day
    for key in ["source_session", "target_session"]:
        roster = client.get(f"/api/v1/sessions/{r[key]['id']}/students").json()
        assert roster["items"][0]["id"] == r["student"]["id"]
    history = client.get(
        "/api/v1/enrolments", params={"student_id": r["student"]["id"], "status": "ended"}
    ).json()
    assert history["total"] == 1


def test_failed_transfer_rolls_back_old_period_and_new_registration(client, records):
    r = records
    second = post(client, "/students", {"display_name": "Sam", "email": "sam@example.com"})
    post(
        client,
        "/enrolments",
        {"student_id": second["id"], "class_id": r["target"]["id"], "starts_on": "2027-02-01"},
    )
    response = client.post(
        f"/api/v1/enrolments/{r['enrolment']['id']}/change",
        json={"new_class_id": r["target"]["id"], "effective_on": "2027-02-10"},
    )
    assert response.status_code == 409
    old = client.get(f"/api/v1/enrolments/{r['enrolment']['id']}").json()
    assert old["status"] == "active" and old["ends_on"] is None
    assert (
        client.get("/api/v1/enrolments", params={"student_id": r["student"]["id"]}).json()["total"]
        == 1
    )


def test_enrolment_end_is_inclusive_and_repeatable(client, records):
    r = records
    url = f"/api/v1/enrolments/{r['enrolment']['id']}/end"
    for _ in range(2):
        response = client.post(url, json={"ends_on": "2027-02-08"})
        assert response.status_code == 200
    for day, count in [("2027-02-08", 1), ("2027-02-09", 0)]:
        result = client.get(
            "/api/v1/enrolments", params={"student_id": r["student"]["id"], "on_date": day}
        ).json()
        assert result["total"] == count


def test_rejoining_cannot_overlap_a_previous_attendance_period(client, records):
    r = records
    assert (
        client.post(
            f"/api/v1/enrolments/{r['enrolment']['id']}/end", json={"ends_on": "2027-02-08"}
        ).status_code
        == 200
    )
    body = {
        "student_id": r["student"]["id"],
        "class_id": r["source"]["id"],
        "starts_on": "2027-02-08",
    }
    assert client.post("/api/v1/enrolments", json=body).status_code == 409
    body["starts_on"] = "2027-02-09"
    assert client.post("/api/v1/enrolments", json=body).status_code == 201
    assert client.get("/api/v1/enrolments").json()["total"] == 2


def test_cancellation_retains_record_and_removes_regular_membership(client, records):
    url = f"/api/v1/enrolments/{records['enrolment']['id']}/cancel"
    assert client.post(url).json()["status"] == "cancelled"
    assert client.post(url).status_code == 200
    assert (
        client.get(f"/api/v1/sessions/{records['source_session']['id']}/students").json()["total"]
        == 0
    )
    assert client.get("/api/v1/enrolments").json()["total"] == 1


def test_capacity_checks_enrolments_session_creation_and_capacity_reduction(client, records):
    r = records
    second = post(client, "/students", {"display_name": "Sam", "email": "sam@example.com"})
    post(
        client,
        "/enrolments",
        {"student_id": second["id"], "class_id": r["source"]["id"], "starts_on": "2027-02-01"},
    )
    third = post(client, "/students", {"display_name": "Pat", "email": "pat@example.com"})
    response = client.post(
        "/api/v1/enrolments",
        json={"student_id": third["id"], "class_id": r["source"]["id"], "starts_on": "2027-02-01"},
    )
    assert response.status_code == 409
    url = f"/api/v1/sessions/{r['source_session']['id']}"
    assert client.patch(url, json={"capacity": 1}).status_code == 409
    assert client.get(url).json()["capacity"] == 2
    response = client.post(
        "/api/v1/sessions",
        json={
            "class_id": r["source"]["id"],
            "starts_at": "2027-02-15T18:00:00+11:00",
            "ends_at": "2027-02-15T19:00:00+11:00",
            "capacity": 1,
        },
    )
    assert response.status_code == 409
    assert client.get("/api/v1/sessions").json()["total"] == 2


def test_student_updates_search_and_duplicate_email_conflict(client, records):
    r = records
    assert r["student"]["email"] == "alex@example.com"
    response = client.patch(
        f"/api/v1/students/{r['student']['id']}",
        json={"highest_level": "Level 3", "context": {"preferred_day": "Saturday"}},
    )
    assert response.status_code == 200
    assert response.json()["highest_level"] == "Level 3"
    assert response.json()["context"]["preferred_day"] == "Saturday"
    assert client.get("/api/v1/students", params={"q": "ALEX"}).json()["total"] == 1
    duplicate = client.post(
        "/api/v1/students", json={"display_name": "Duplicate", "email": "ALEX@example.com"}
    )
    assert duplicate.status_code == 409
    assert "INSERT" not in duplicate.text and "password" not in duplicate.text
    assert (
        client.patch(f"/api/v1/students/{r['student']['id']}", json={"highest_level": None}).json()[
            "highest_level"
        ]
        is None
    )


def test_conversations_keep_ordered_emails_and_allow_only_draft_edits(client, records):
    student_id = records["student"]["id"]
    conversation = post(client, "/conversations", {"student_id": student_id, "subject": "Enquiry"})
    url = f"/conversations/{conversation['id']}/messages"
    later = post(
        client,
        url,
        {
            "kind": "student_email",
            "body": "Saturday instead.",
            "occurred_at": "2027-02-07T11:00:00+11:00",
        },
    )
    earlier = post(
        client,
        url,
        {
            "kind": "student_email",
            "body": "Thursday please.",
            "occurred_at": "2027-02-07T10:00:00+11:00",
        },
    )
    draft = post(client, url, {"kind": "assistant_draft", "body": "Manually written draft."})
    messages = client.get(f"/api/v1{url}").json()["items"]
    assert [item["id"] for item in messages if item["kind"] == "student_email"] == [
        earlier["id"],
        later["id"],
    ]
    assert (
        client.patch(f"/api/v1/messages/{earlier['id']}", json={"body": "Rewritten"}).status_code
        == 409
    )
    assert (
        client.patch(f"/api/v1/messages/{draft['id']}", json={"body": "Edited draft"}).json()[
            "body"
        ]
        == "Edited draft"
    )
    assert client.get(f"/api/v1/students/{student_id}").json()["context"] == {}
    assert (
        client.get("/api/v1/conversations", params={"student_id": student_id}).json()["total"] == 1
    )
    assert (
        client.patch(
            f"/api/v1/conversations/{conversation['id']}", json={"subject": "Updated subject"}
        ).json()["subject"]
        == "Updated subject"
    )


def test_timetable_updates_filters_and_timezone_date_queries(client, records):
    r = records
    term = post(
        client,
        "/terms",
        {"name": "Unused term", "starts_on": "2027-04-01", "ends_on": "2027-06-30"},
    )
    assert (
        client.patch(f"/api/v1/terms/{term['id']}", json={"starts_on": "2027-04-02"}).status_code
        == 200
    )
    assert (
        client.patch(f"/api/v1/terms/{r['term']['id']}", json={"ends_on": "2027-04-01"}).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/locations/{r['a']['id']}", json={"address": "Updated fictional"}
        ).status_code
        == 200
    )
    assert (
        client.patch(f"/api/v1/locations/{r['a']['id']}", json={"timezone": "UTC"}).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/classes/{r['target']['id']}", json={"prerequisites": "Staff review"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/classes", params={"location_id": r["b"]["id"], "level": "Level 2"}
        ).json()["total"]
        == 1
    )
    post(
        client,
        "/sessions",
        {
            "class_id": r["source"]["id"],
            "starts_at": "2027-02-08T00:30:00+11:00",
            "ends_at": "2027-02-08T01:30:00+11:00",
            "capacity": 2,
        },
    )
    assert (
        client.get(
            "/api/v1/sessions", params={"from_date": "2027-02-08", "to_date": "2027-02-08"}
        ).json()["total"]
        == 2
    )
    assert (
        client.get(
            "/api/v1/sessions", params={"from_date": "2027-02-07", "to_date": "2027-02-07"}
        ).json()["total"]
        == 0
    )
    assert (
        client.get(
            "/api/v1/sessions", params={"from_date": "2027-03-01", "to_date": "2027-02-01"}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "path,body",
    [
        ("/students", {"display_name": " ", "email": "alex@example.com"}),
        ("/students", {"display_name": "Alex", "email": "invalid"}),
        ("/locations", {"name": "A", "address": "Fictional", "timezone": "Invalid/Zone"}),
        ("/terms", {"name": "Invalid", "starts_on": "2027-03-01", "ends_on": "2027-02-01"}),
        ("/conversations", {"student_id": str(uuid4()), "unexpected": True}),
    ],
)
def test_invalid_input_has_structured_errors(client, path, body):
    response = client.post(f"/api/v1{path}", json=body)
    assert response.status_code == 422
    assert "code" in response.json()["error"]


def test_invalid_sessions_enrolments_and_null_patches_roll_back(client, records):
    r = records
    for update in [
        {"starts_at": "2027-02-08T18:00:00"},
        {"capacity": 0},
        {"starts_at": "2027-04-01T18:00:00+11:00"},
        {"capacity": None},
    ]:
        assert (
            client.patch(f"/api/v1/sessions/{r['source_session']['id']}", json=update).status_code
            == 422
        )
    assert (
        client.patch(f"/api/v1/students/{r['student']['id']}", json={"email": None}).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/classes/{r['source']['id']}", json={"term_id": r["term"]["id"]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/enrolments",
            json={
                "student_id": r["student"]["id"],
                "class_id": r["target"]["id"],
                "starts_on": "2027-04-01",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/enrolments",
            json={
                "student_id": r["student"]["id"],
                "class_id": r["source"]["id"],
                "starts_on": "2027-02-02",
            },
        ).status_code
        == 409
    )
    assert client.get("/api/v1/enrolments").json()["total"] == 1


@pytest.mark.parametrize(
    "resource",
    ["students", "terms", "locations", "classes", "sessions", "enrolments", "conversations"],
)
def test_staff_access_and_bounded_pagination(client, resource):
    url = f"/api/v1/{resource}"
    assert client.get(url, headers={"Authorization": ""}).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(url, params={"limit": 101}).status_code == 422
    assert client.get(url, params={"offset": -1}).status_code == 422
    assert client.get(url).json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_not_found_no_hard_delete_health_and_documentation(client, records):
    assert client.get(f"/api/v1/students/{uuid4()}").status_code == 404
    assert client.get("/api/v1/students/not-a-uuid").status_code == 422
    assert client.delete(f"/api/v1/students/{records['student']['id']}").status_code == 405
    assert client.get("/health", headers={"Authorization": ""}).json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert "/api/v1/enrolments/{enrolment_id}/change" in client.get("/openapi.json").json()["paths"]


def test_demo_seed_is_repeatable_and_preserves_edits(db_engine):
    with Session(db_engine) as db, db.begin():
        result = seed_demo(db)
        assert result["created"]
    with Session(db_engine) as db, db.begin():
        alex = db.get(Student, result["ids"]["alex"])
        alex.highest_level = "Staff corrected level"
    with Session(db_engine) as db, db.begin():
        assert not seed_demo(db)["created"]
        assert db.scalar(select(func.count()).select_from(Student)) == 2
        assert db.get(Student, result["ids"]["alex"]).highest_level == "Staff corrected level"
