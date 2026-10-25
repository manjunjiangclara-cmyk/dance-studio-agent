from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


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
