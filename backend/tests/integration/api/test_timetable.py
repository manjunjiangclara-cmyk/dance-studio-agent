import pytest

from .helpers import post

pytestmark = pytest.mark.integration


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


def test_session_students_are_editable_independent_and_resolve_current_names(client, records):
    from uuid import uuid4

    r = records
    student_id = r["student"]["id"]
    session_url = f"/api/v1/sessions/{r['target_session']['id']}"
    assert client.get(session_url).json()["students"] == []
    updated = client.patch(session_url, json={"students": [student_id]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["students"] == [student_id]
    client.patch(f"/api/v1/students/{student_id}", json={"display_name": "Renamed student"})
    roster = client.get(session_url + "/students").json()
    assert roster["total"] == 1
    assert roster["items"][0]["display_name"] == "Renamed student"
    assert client.get(f"/api/v1/sessions/{r['source_session']['id']}/students").json()["total"] == 0
    for invalid in [[student_id, student_id], [str(uuid4())]]:
        response = client.patch(session_url, json={"students": invalid})
        assert response.status_code in {404, 409, 422}, response.text
        assert client.get(session_url).json()["students"] == [student_id]
    other = post(client, "/students", {"display_name": "Other", "email": "other@example.com"})
    assert (
        client.patch(session_url, json={"students": [student_id, other["id"]]}).status_code == 409
    )
    assert client.patch(session_url, json={"students": []}).status_code == 200
    assert client.get(session_url + "/students").json()["items"] == []


def test_session_creation_validates_student_membership(client, records):
    from uuid import uuid4

    body = {
        "class_id": records["source"]["id"],
        "starts_at": "2027-02-15T18:00:00+11:00",
        "ends_at": "2027-02-15T19:00:00+11:00",
        "capacity": 1,
        "students": [records["student"]["id"]],
    }
    for invalid in [[str(uuid4())], [records["student"]["id"]] * 2]:
        response = client.post("/api/v1/sessions", json={**body, "students": invalid})
        assert response.status_code in {404, 409, 422}, response.text
    created = post(client, "/sessions", body)
    assert created["students"] == body["students"]


def test_attendance_records_actual_participation(client, db, catalog):
    from datetime import UTC, datetime, timedelta

    session = catalog.class_session
    session.students = [catalog.student.id]
    session.starts_at = datetime.now(UTC) - timedelta(days=2)
    session.ends_at = session.starts_at + timedelta(hours=1)
    db.commit()
    path = f"/api/v1/sessions/{session.id}/attendance/{catalog.student.id}"
    assert client.get(f"/api/v1/sessions/{session.id}/attendance").json() == {}
    assert client.put(path, json={"status": "attended"}).status_code == 200
    assert client.get(f"/api/v1/sessions/{session.id}/attendance").json() == {
        str(catalog.student.id): "attended"
    }
    assert client.put(path, json={"status": "absent"}).status_code == 200
    assert client.put(path, json={"status": "unknown"}).status_code == 200
    assert client.get(f"/api/v1/sessions/{session.id}/attendance").json() == {}
