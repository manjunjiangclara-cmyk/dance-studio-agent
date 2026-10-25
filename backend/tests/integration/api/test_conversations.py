import pytest

from .helpers import post

pytestmark = pytest.mark.integration


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
