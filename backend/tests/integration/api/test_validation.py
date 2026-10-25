from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


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
