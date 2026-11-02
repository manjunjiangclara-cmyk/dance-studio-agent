"""Exercise ASGI receive boundaries: no implicit multipart buffering before auth."""

import asyncio
import tempfile

import httpx
import pytest

from studio_copilot.documents import ingestion
from tests.unit.test_documents import client as client
from tests.unit.test_website_auth import session_cookie

ROOT = "/api/v1/documents/upload"
AUTH = {"Authorization": "Bearer test"}


def encoded_upload(raw=b"Valid studio text", **fields):
    request = httpx.Request(
        "POST",
        "http://test" + ROOT,
        data={"title": "Handbook", **fields},
        files={"file": ("handbook.md", raw, "text/plain")},
    )
    return request.read(), request.headers["content-type"]


def stream_request(client, body, content_type, *, headers=None, chunks=7, disconnect=False):
    calls, messages = [], []
    request_headers = {"content-type": content_type, **(headers or {})}
    fragments = [body[offset : offset + chunks] for offset in range(0, len(body), chunks)]

    async def receive():
        calls.append(True)
        if not fragments:
            return {"type": "http.disconnect"}
        part = fragments.pop(0)
        return {"type": "http.request", "body": part, "more_body": bool(fragments) or disconnect}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": ROOT,
        "raw_path": ROOT.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("studio.example.test", 443),
        "client": ("127.0.0.1", 1234),
        "headers": [
            (key.lower().encode(), value.encode()) for key, value in request_headers.items()
        ],
    }
    asyncio.run(client.app(scope, receive, send))
    return next(item["status"] for item in messages if item["type"] == "http.response.start"), calls


def test_auth_and_declared_request_cap_are_checked_before_receiving_or_spooling(
    client, monkeypatch
):
    def no_file(*args, **kwargs):
        pytest.fail(
            "Must not allocate a temporary file before authorization and request-size checks"
        )

    monkeypatch.setattr(ingestion.tempfile, "TemporaryFile", no_file)
    body, content_type = encoded_upload()
    status, calls = stream_request(client, body, content_type)
    assert status == 401 and calls == []
    status, calls = stream_request(
        client,
        body,
        content_type,
        headers={**AUTH, "Content-Length": str(ingestion.MAX_REQUEST_BYTES + 1)},
    )
    assert status == 413 and calls == []


def test_chunked_upload_needs_no_content_length_and_preserves_multibyte_characters(client):
    text = "\ufeff# Café\r\nA dancer brings water. 🩰\r\n"
    body, content_type = encoded_upload(text.encode())
    status, calls = stream_request(client, body, content_type, headers=AUTH, chunks=1)
    assert status == 201 and len(calls) > 10
    items = client.get("/api/v1/documents", headers=AUTH).json()
    assert client.get(f"/api/v1/documents/{items[0]['id']}", headers=AUTH).json()["content"] == text


@pytest.mark.parametrize("case", ["cap", "false_length", "disconnect", "malformed", "utf8"])
def test_stream_failures_close_temporary_file_and_never_persist(client, monkeypatch, case):
    files = []
    original = tempfile.TemporaryFile

    def tracking(*args, **kwargs):
        result = original(*args, **kwargs)
        files.append(result)
        return result

    monkeypatch.setattr(ingestion.tempfile, "TemporaryFile", tracking)
    body, content_type = encoded_upload(b"\xff" if case == "utf8" else b"Good content" * 30)
    headers = dict(AUTH)
    if case == "cap":
        monkeypatch.setattr(ingestion, "MAX_REQUEST_BYTES", 200)
    if case == "false_length":
        headers["Content-Length"] = "1"
    if case in {"disconnect", "malformed"}:
        body = body[:-20]
    status, _ = stream_request(
        client, body, content_type, headers=headers, disconnect=case == "disconnect"
    )
    assert status in {400, 413, 422}
    assert files and all(stream.closed for stream in files)
    assert client.get("/api/v1/documents", headers=AUTH).json() == []


def test_duplicate_parts_and_large_metadata_are_rejected(client):
    for files, data in [
        ([("file", ("one.md", b"First")), ("file", ("two.md", b"Second"))], {"title": "Test"}),
        ({"file": ("one.md", b"Text")}, {"title": "x" * 1025}),
    ]:
        result = client.post(ROOT, headers=AUTH, files=files, data=data)
        assert result.status_code in {413, 422}
    assert client.get("/api/v1/documents", headers=AUTH).json() == []


def test_new_write_endpoints_enforce_owner_origin_and_csrf(client):
    client.cookies.set("studio_owner", session_cookie(), domain="studio.example.test", path="/")
    result = client.post(ROOT, files={"file": ("test.md", b"Good text")}, data={"title": "Test"})
    assert result.status_code == 403
    valid = {"origin": "https://studio.example.test", "x-csrf-token": "csrf-for-test"}
    result = client.post(
        ROOT, headers=valid, files={"file": ("test.md", b"Good text")}, data={"title": "Test"}
    )
    assert result.status_code == 201
    path = "/api/v1/documents/" + result.json()["id"]
    for method, suffix, body in [
        ("PATCH", "/metadata", {"title": "Changed", "expected_revision": 1}),
        (
            "PUT",
            "/text",
            {
                "title": "Changed",
                "filename": "test.md",
                "content": "Changed",
                "expected_revision": 1,
            },
        ),
    ]:
        assert client.request(method, path + suffix, json=body).status_code == 403
    assert (
        client.put(
            path + "/upload",
            files={"file": ("test.md", b"Changed")},
            data={"title": "Changed", "expected_revision": "1"},
        ).status_code
        == 403
    )
    assert client.get(path).json()["content"] == "Good text"
