"""Run all manual labels through the real keyword search, with no model calls."""

import hashlib
import json
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.retrieval.engine import RetrievalError
from studio_copilot.documents.retrieval.evaluation import evaluate
from studio_copilot.persistence.models import Document, DocumentRevision
from tests.integration.test_embeddings import create_source, tokenizer, unit_vector  # noqa: F401

pytestmark = pytest.mark.integration
CASES = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_cases.json"


def test_all_40_manual_labels_with_real_keyword_engine(db_engine, tokenizer, monkeypatch):  # noqa: F811
    labels = json.loads(CASES.read_text())
    source = (CASES.parent / labels["source_file"]).read_bytes()
    assert hashlib.sha256(source).hexdigest() == labels["source_sha256"]
    with Session(db_engine) as session, session.begin():
        document = Document(
            title="Fictional retrieval fixture", filename="handbook.md", content=source.decode()
        )
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title=document.title,
                filename=document.filename,
                content=document.content,
                byte_size=len(source),
                sha256=labels["source_sha256"],
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_from=date(2027, 1, 1),
                effective_to=date(2027, 12, 31),
            )
        )

    class Fake:
        def embed(self, texts, before_attempt=lambda: None):
            before_attempt()
            return [unit_vector() for _ in texts], 0

    status = run(db_engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=Fake())
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = evaluate(db_engine, UUID(status["run_id"]), CASES, tokenizer)
    assert report["semantic_quality_measured"] is False
    assert len(report["cases"]) == 40
    for split in ("tuning", "held_out"):
        assert report["summaries"][split]["cases"] == 20
        assert report["summaries"][split]["date_exclusion_checks_pass"]
        assert 0 <= report["summaries"][split]["final_at_6"]["recall"] <= 1
    assert any(case.get("final_at_6", {}).get("recall", 0) > 0 for case in report["cases"])
    # Wrong source identity must fail before starting any query evaluation.
    other = create_source(db_engine, content="# Unrelated\n\nOther studio rules.")
    other_status = run(db_engine, other, 1, tokenizer, EmbeddingProfile(), embedder=Fake())
    with pytest.raises(RetrievalError, match="labelled source"):
        evaluate(db_engine, UUID(other_status["run_id"]), CASES, tokenizer)
