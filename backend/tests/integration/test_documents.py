from fastapi.testclient import TestClient

from studio_copilot.api.app import create_app
from tests.unit.test_documents import payload


def test_document_persists_in_migrated_postgres(db_engine):
    app = create_app(db_engine, admin_token="test")
    with TestClient(app, headers={"Authorization": "Bearer test"}) as client:
        result = client.post("/api/v1/documents", json=payload("A studio rule"))
        assert result.status_code == 201
        document_id = result.json()["id"]
    with TestClient(app, headers={"Authorization": "Bearer test"}) as client:
        assert client.get(f"/api/v1/documents/{document_id}").json()["content"] == "A studio rule"
