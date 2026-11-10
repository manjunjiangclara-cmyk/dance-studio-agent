"""Online teacher-review integration with real PostgreSQL and fake paid providers."""

import hashlib
import os
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import EnquiryInterpretation, Routing
from studio_copilot.documents import online
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.models import (
    AgentRun,
    Document,
    DocumentRevision,
    EmbeddingRun,
    Message,
)
from tests.integration.test_retrieval import LocalVectors

from .helpers import review, start

pytestmark = pytest.mark.integration
TEXT = "# Trial policy\r\n\r\nA trial costs $20. Café 💃.\r\n"
QUESTION = "What does a trial cost?"


class Ranker:
    def rank(self, question, candidates):
        return candidates


class Writer:
    def __init__(self, engine, *, quote="A trial costs $20.", status="answered", hook=None):
        self.engine, self.quote, self.status, self.hook = engine, quote, status, hook
        self.calls = []
        self.expected_connections = 1

    def generate(self, payload):
        assert self.engine.pool.checkedout() == self.expected_connections
        self.calls.append(payload)
        if self.hook:
            self.hook()
        return dict(
            status=self.status,
            claims=[
                dict(
                    id="c1",
                    text="A trial costs $20.",
                    citations=[
                        dict(
                            evidence_id=payload["evidence"][0]["id"],
                            quote=self.quote,
                        )
                    ],
                )
            ],
            missing_information=[] if self.status == "answered" else ["A teacher must confirm."],
            reason_code="supported" if self.status == "answered" else "insufficient_evidence",
        )

    def verify(self, *args):
        raise AssertionError("Verification must stay off")


@pytest.fixture
def online_rig(rig, scenario, db_engine, monkeypatch):
    tokenizer = Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))
    with Session(db_engine) as db, db.begin():
        document = Document(title="Trial policy", filename="policy.md", content=TEXT)
        db.add(document)
        db.flush()
        document_id = document.id
        db.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title="Trial policy",
                filename="policy.md",
                content=TEXT,
                byte_size=len(TEXT.encode()),
                sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
                hash_origin="upload_bytes",
                ingestion_status="ready",
                effective_to=date(2028, 12, 31),
            )
        )
    prepared = pipeline.run(
        db_engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=LocalVectors(db_engine)
    )
    run_id = prepared["run_id"]
    with Session(db_engine) as db:
        online.source_rows(db, [run_id], date(2027, 2, 7))
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    monkeypatch.setenv("STUDIO_DOCUMENT_RUN_IDS", str(run_id))
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/not-downloaded")
    model = rig[1]
    model.routing = Routing(
        intents=["general_enquiry"],
        action="information_only",
        request_summary=QUESTION,
        needs_clarification=False,
        reason="Informational policy question.",
    )
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary=QUESTION,
        missing_details=[],
        enduring_preferences=[],
        questions=[QUESTION],
        requested_actions=[],
    )
    model.draft = lambda context: pytest.fail("Grounded answers must not be freely rewritten")
    model.choose_tools = lambda *args: pytest.fail("Document path must not run model tools")

    class OnlineVectors(LocalVectors):
        expected_connections = 1

        def embed(self, texts, before_attempt=lambda: None):
            # Existing agent orchestration holds a session advisory lock; document
            # retrieval/source-read transactions themselves must be closed.
            assert self.engine.pool.checkedout() == self.expected_connections
            self.calls.append(list(texts))
            return [[1.0] + [0.0] * 1535 for _ in texts], len(texts)

    writer, vectors = Writer(db_engine), OnlineVectors(db_engine)
    original = online.gather

    def gather(engine, state):
        return original(
            engine, state, tokenizer=tokenizer, reranker=Ranker(), embedder=vectors, provider=writer
        )

    monkeypatch.setattr(online, "gather", gather)
    return document_id, run_id, writer, vectors


def test_question_automatically_gets_exact_citations_and_remains_a_draft(
    online_rig,
    rig,
    scenario,
    db_engine,
):
    document_id, _, writer, vectors = online_rig
    run = start(rig, scenario)
    result = run["evidence"][0]["result"]
    assert len(writer.calls) == len(vectors.calls) == 1
    assert result["status"] == "answered" and result["verification_applied"] is False
    assert "[E" in run["draft_details"]["body"]
    citation = result["claims"][0]["citations"][0]
    assert TEXT[citation["start"] : citation["end"]] == citation["quote"]
    assert citation["document_id"] == str(document_id) and citation["revision"] == 1
    assert result["evidence"][0]["text"].endswith(TEXT)
    assert run["approved_response_id"] is None
    response = review(rig[0], run, "approve")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"


@pytest.mark.parametrize(
    "mutation", ["delete", "replace", "disable", "revoke", "expire", "incomplete"]
)
def test_stale_sources_block_approval_without_changing_the_review(
    mutation,
    online_rig,
    rig,
    scenario,
    db_engine,
    monkeypatch,
):
    document_id, run_id, _, _ = online_rig
    run = start(rig, scenario)
    with Session(db_engine) as db:
        before = db.scalar(select(func.count()).select_from(Message))
    if mutation == "expire":

        class Future(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2030, 1, 1, tzinfo=tz)

        monkeypatch.setattr(online, "datetime", Future)
    elif mutation == "disable":
        monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "false")
    elif mutation == "revoke":
        monkeypatch.setenv("STUDIO_DOCUMENT_RUN_IDS", "00000000-0000-0000-0000-000000000099")
    else:
        with Session(db_engine) as db, db.begin():
            if mutation == "delete":
                db.execute(delete(Document).where(Document.id == document_id))
            elif mutation == "replace":
                db.execute(
                    update(Document).where(Document.id == document_id).values(current_revision=2)
                )
            else:
                db.execute(
                    update(EmbeddingRun).where(EmbeddingRun.id == run_id).values(status="failed")
                )
    response = review(rig[0], run, "approve")
    assert response.status_code == 409, response.text
    saved = rig[0].get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["status"] == "awaiting_review"
    assert saved["draft_details"] == run["draft_details"]
    with Session(db_engine) as db:
        assert db.scalar(select(func.count()).select_from(Message)) == before


@pytest.mark.parametrize(
    "status,quote", [("partial", "A trial costs $20."), ("answered", "FORGED")]
)
def test_partial_or_bad_quotes_require_teacher_and_support_answer_or_deferral(
    status,
    quote,
    online_rig,
    rig,
    scenario,
):
    _, _, writer, _ = online_rig
    writer.status, writer.quote = status, quote
    run = start(rig, scenario)
    answer = run["draft_details"]["answers"][0]
    assert answer["status"] == "needs_teacher"
    assert "$20" not in run["draft_details"]["body"]
    assert review(rig[0], run, "approve").status_code == 409
    response = review(
        rig[0],
        run,
        "revise",
        question_resolutions=[
            dict(
                question_id=answer["question_id"],
                decision="answer",
                answer="The teacher confirms a $25 trial.",
            )
        ],
    )
    assert response.status_code == 200, response.text
    revised = response.json()
    assert len(writer.calls) == 1  # A resolved question does not pay for generation again.
    assert "$25" in revised["draft_details"]["body"]
    assert review(rig[0], revised, "approve").status_code == 200


def test_delete_during_generation_never_leaves_a_supported_draft(
    online_rig,
    rig,
    scenario,
    db_engine,
):
    document_id, _, writer, _ = online_rig

    def remove():
        with Session(db_engine) as db, db.begin():
            db.execute(delete(Document).where(Document.id == document_id))

    writer.hook = remove
    run = start(rig, scenario)
    assert run["evidence"][0]["result"]["status"] == "failed"
    assert run["draft_details"]["answers"][0]["status"] == "needs_teacher"
    assert "$20" not in run["draft_details"]["body"]


def test_incoming_email_automatically_retrieves_without_a_separate_search_request(online_rig, rig):
    _, _, writer, vectors = online_rig
    writer.expected_connections = vectors.expected_connections = 2
    response = rig[0].post(
        "/api/v1/incoming-emails",
        json={
            "from": "new-policy-enquirer@example.com",
            "body": QUESTION,
        },
    )
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "awaiting_review"
    assert "[E" in run["draft_details"]["body"]
    assert len(writer.calls) == len(vectors.calls) == 1
    assert run["approved_response_id"] is None


def test_date_ineligible_sources_produce_zero_embedding_or_generation_calls(
    online_rig,
    rig,
    scenario,
    db_engine,
):
    _, _, writer, vectors = online_rig
    with Session(db_engine) as db, db.begin():
        db.execute(
            update(Message)
            .where(Message.id == scenario["source"])
            .values(
                occurred_at=datetime.fromisoformat("2030-01-01T12:00:00+11:00"),
            )
        )
    run = start(rig, scenario)
    assert writer.calls == vectors.calls == []
    assert run["evidence"][0]["result"]["status"] == "abstained"
    assert run["draft_details"]["answers"][0]["status"] == "needs_teacher"


def test_approval_source_locks_prevent_concurrent_replacement(online_rig, rig, scenario, db_engine):
    document_id, _, _, _ = online_rig
    run = start(rig, scenario)
    with Session(db_engine) as db, db.begin():
        record = db.get(AgentRun, UUID(run["id"]))
        online.require_current_sources(db, record)
        with pytest.raises(OperationalError):
            with db_engine.begin() as concurrent:
                concurrent.execute(text("SET LOCAL lock_timeout = '100ms'"))
                concurrent.execute(
                    update(Document).where(Document.id == document_id).values(current_revision=2)
                )
    # Source locks have now been released. A new replacement is allowed.
    with db_engine.begin() as concurrent:
        concurrent.execute(
            update(Document).where(Document.id == document_id).values(current_revision=2)
        )
