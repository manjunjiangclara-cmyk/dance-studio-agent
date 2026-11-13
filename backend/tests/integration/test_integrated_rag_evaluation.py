"""Unpaid checks for the new integrated evaluation harness."""

import hashlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from integrated_rag_evaluation import execute
from integrated_rag_evaluation.runner import RunBudget
from studio_copilot.api.app import create_app
from studio_copilot.documents import activation
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.persistence.models import DocumentActivation
from tests.integration.test_retrieval import LocalVectors

pytestmark = pytest.mark.integration


def test_prepare_documents_requires_explicit_api_activation_in_test_schema(db_engine, monkeypatch):
    content = "# Trial policy\nA trial costs $20.\n"
    source = dict(
        key="trial",
        title="Trial policy",
        file="trial.md",
        text=content,
        sha256=hashlib.sha256(content.encode()).hexdigest(),
        effective_from="2026-01-01",
        effective_to="2028-12-31",
    )
    monkeypatch.setattr(execute, "load_sources", lambda: {"documents": [source]})
    monkeypatch.setattr(activation, "check_setup", lambda: None)
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    monkeypatch.setenv(
        "STUDIO_TOKENIZER_CACHE", os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    )

    class FakeVectors:
        def __init__(self, profile):
            self.delegate = LocalVectors(db_engine)

        def embed(self, texts, before_attempt=lambda: None):
            return self.delegate.embed(texts, before_attempt)

    monkeypatch.setattr(execute, "BudgetEmbedder", FakeVectors)
    app = create_app(db_engine, admin_token="evaluation-test")
    with TestClient(app, headers={"Authorization": "Bearer evaluation-test"}) as client:
        prepared = execute.prepare_documents(client, db_engine, RunBudget(10, 10_000, 10_000))
        assert len(prepared) == 1
        with Session(db_engine) as db:
            assert db.scalar(select(func.count()).select_from(DocumentActivation)) == 1
        status = client.get(
            f"/api/v1/documents/{prepared[0]['document_id']}/answer-activation"
        ).json()
        assert status["status"] == "enabled"


def test_run_case_records_source_date_and_no_business_changes(db_engine):
    class Client:
        def post(self, url, json):
            assert url.startswith("/api/v1/conversations/")
            return type(
                "Response",
                (),
                {
                    "status_code": 200,
                    "json": lambda self: {
                        "id": "run-id",
                        "status": "awaiting_review",
                        "draft_details": {"body": "A trial costs $20.", "answers": []},
                        "evidence": [],
                        "interpretation": {},
                        "error": None,
                    },
                },
            )()

    case = dict(
        id="rag-test-date",
        as_of="2027-06-01",
        question="What does a trial cost?",
        expected_status="answered",
        required_facts=[],
        forbidden_patterns=[],
        tags=["single_source"],
    )
    row = execute.run_case(Client(), db_engine, case, RunBudget(10, 10_000, 10_000))
    assert row["status"] == "completed" and row["no_business_change"]
    assert row["as_of"] == "2027-06-01" and row["draft"]["body"] == "A trial costs $20."
