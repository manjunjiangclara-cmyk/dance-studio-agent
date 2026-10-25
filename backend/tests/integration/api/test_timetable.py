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
