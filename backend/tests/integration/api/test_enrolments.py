import pytest

from .helpers import post

pytestmark = pytest.mark.integration


def test_class_change_preserves_history_and_independent_rosters(client, records):
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
        assert roster["items"] == []
    history = client.get(
        "/api/v1/enrolments", params={"student_id": r["student"]["id"], "status": "ended"}
    ).json()
    assert history["total"] == 1


def test_transfer_into_class_with_full_session_keeps_session_membership(client, records):
    r = records
    second = post(client, "/students", {"display_name": "Sam", "email": "sam@example.com"})
    session_url = f"/api/v1/sessions/{r['target_session']['id']}"
    assert client.patch(session_url, json={"students": [second["id"]]}).status_code == 200
    response = client.post(
        f"/api/v1/enrolments/{r['enrolment']['id']}/change",
        json={"new_class_id": r["target"]["id"], "effective_on": "2027-02-10"},
    )
    assert response.status_code == 200, response.text
    assert client.get(session_url).json()["students"] == [second["id"]]


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


def test_cancellation_retains_record_and_session_membership(client, records):
    session_url = f"/api/v1/sessions/{records['source_session']['id']}"
    assert (
        client.patch(session_url, json={"students": [records["student"]["id"]]}).status_code == 200
    )
    url = f"/api/v1/enrolments/{records['enrolment']['id']}/cancel"
    assert client.post(url).json()["status"] == "cancelled"
    assert client.post(url).status_code == 200
    assert (
        client.get(f"/api/v1/sessions/{records['source_session']['id']}/students").json()["total"]
        == 1
    )
    assert client.get("/api/v1/enrolments").json()["total"] == 1


def test_enrolments_and_new_sessions_have_independent_capacity(client, records):
    r = records
    url = f"/api/v1/sessions/{r['source_session']['id']}"
    assert client.patch(url, json={"students": [r["student"]["id"]]}).status_code == 200
    for name in ["Sam", "Pat"]:
        student = post(client, "/students", {"display_name": name, "email": f"{name}@example.com"})
        post(
            client,
            "/enrolments",
            {"student_id": student["id"], "class_id": r["source"]["id"], "starts_on": "2027-02-01"},
        )
    assert client.patch(url, json={"capacity": 1}).status_code == 200
    assert client.get(url).json()["students"] == [r["student"]["id"]]
    new_session = post(
        client,
        "/sessions",
        {
            "class_id": r["source"]["id"],
            "starts_at": "2027-02-15T18:00:00+11:00",
            "ends_at": "2027-02-15T19:00:00+11:00",
            "capacity": 1,
        },
    )
    assert new_session["students"] == []
