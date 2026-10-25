import pytest

pytestmark = pytest.mark.integration


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
