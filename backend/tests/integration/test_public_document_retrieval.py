"""Both public entry points use the actual isolated document retrieval pipeline."""

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from studio_copilot.agent.contracts import DocumentEmailComposition, EnquiryInterpretation, Routing
from studio_copilot.documents import online
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.public_demo import document_index
from studio_copilot.public_demo.service import DemoStore, PublicDemo
from tests.integration.agent.helpers import FakeModel
from tests.integration.test_embeddings import create_source
from tests.integration.test_retrieval import LocalVectors

pytestmark = pytest.mark.integration
QUESTION = "Can I wear socks for my first class?"
QUOTE = "Socks are suitable for your first class; ballet shoes are optional."
OWNER_SECRET = "PRIVATE TEST OWNER ONLY blue platypus socks"


class Model(FakeModel):
    def route(self, context):
        return Routing(
            intents=["general_enquiry"],
            action="information_only",
            request_summary=QUESTION,
            needs_clarification=False,
            reason="A question about clothing.",
        )

    def interpret_enquiry(self, context):
        return EnquiryInterpretation(
            request_summary=QUESTION,
            missing_details=[],
            enduring_preferences=[],
            questions=[QUESTION],
            requested_actions=[],
        )

    def demo_evidence_route(self, context):
        return "documents"

    def compose_document_email(self, context):
        return DocumentEmailComposition(body="Hello. " + QUOTE, review_concerns=[])


class Ranker:
    def rank(self, question, candidates):
        return sorted(candidates, key=lambda candidate: QUOTE not in candidate["text"])


class Writer:
    def __init__(self):
        self.calls = []

    def generate(self, payload):
        self.calls.append(payload)
        block = next(block for block in payload["evidence"] if QUOTE in block["text"])
        return {
            "status": "answered",
            "claims": [
                {
                    "id": "c1",
                    "text": QUOTE,
                    "citations": [{"evidence_id": block["id"], "quote": QUOTE}],
                }
            ],
            "missing_information": [],
            "reason_code": "supported",
        }


def test_document_approval_excludes_index_publication(db_engine, monkeypatch):
    monkeypatch.setattr(document_index, "engine_from_env", lambda: db_engine)
    state = {"draft": {"references": ["document:example"]}}
    store = DemoStore(None, None)
    with store.document_approval_guard(state):
        with db_engine.begin() as db:
            assert not db.scalar(text("SELECT pg_try_advisory_xact_lock(582910743)"))
    with db_engine.begin() as db:
        assert db.scalar(text("SELECT pg_try_advisory_xact_lock(582910743)"))


@pytest.mark.parametrize("entry", ["review_queue", "walkthrough"])
def test_public_entry_uses_grounded_demo_documents(entry, db_engine, tmp_path, monkeypatch):
    tokenizer = Tokenizer(Path(default_cache()))
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/unused-fake-reranker")
    vectors = LocalVectors(db_engine)
    document_index.prepare(db_engine, tokenizer, EmbeddingProfile(), embedder=vectors)
    run_ids = set(document_index.configuration(db_engine).run_ids)
    owner_id = create_source(
        db_engine, "# Owner private note\n\n" + OWNER_SECRET, title="Private owner note"
    )
    owner_run = pipeline.run(
        db_engine, owner_id, 1, tokenizer, EmbeddingProfile(), embedder=vectors
    )["run_id"]
    assert owner_run not in {str(run_id) for run_id in run_ids}
    writer = Writer()
    original_gather = online.gather
    captured = []

    def gather(engine, state, **kwargs):
        result = original_gather(
            engine,
            state,
            tokenizer=tokenizer,
            reranker=Ranker(),
            embedder=vectors,
            provider=writer,
            **kwargs,
        )
        captured.append(result)
        return result

    monkeypatch.setattr(document_index, "engine_from_env", lambda: db_engine)
    monkeypatch.setattr(online, "gather", gather)
    demo = PublicDemo(tmp_path / "public.sqlite", factory=Model)
    if entry == "review_queue":
        token = demo.create("document", str(uuid4()))["token"]
    else:
        token = demo.create_walkthrough(str(uuid4()), "new", QUESTION)["token"]
    evidence = demo.execute(token, "evidence")
    assert not evidence["missing_information"]
    assert any(QUOTE in item and "revision 1" in item for item in evidence["evidence"])
    assert len(writer.calls) == 1
    assert OWNER_SECRET not in str(writer.calls)
    assert OWNER_SECRET not in str(evidence)
    document_result = captured[0]["evidence"][0]["result"]
    assert document_result["status"] == "answered"
    citation = document_result["claims"][0]["citations"][0]
    assert citation["title"] == "Beginner clothing policy"
    assert citation["revision"] == 1
    assert citation["quote"] == QUOTE
    used_ids = {source["run_id"] for source in document_result["sources"]}
    assert used_ids and used_ids <= {str(id) for id in run_ids}
    draft = demo.execute(token, "draft")
    assert QUOTE in draft["body"]
    published = document_index.PUBLIC_DOCUMENTS
    changed = deepcopy(published)
    changed[0]["content"] += "\nUpdated policy.\n"
    monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", changed)
    with pytest.raises(HTTPException) as stale:
        demo.execute(token, "approve", revision=draft["revision"], body=draft["body"])
    assert stale.value.status_code == 409
    monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", published)
    approval = demo.execute(token, "approve", revision=draft["revision"], body=draft["body"])
    assert approval["status"] == "approved_mock"
    assert OWNER_SECRET not in str(approval)


@pytest.mark.parametrize("entry", ["review_queue", "walkthrough"])
@pytest.mark.parametrize(
    "condition", ["missing_index", "stale_index", "provider_error", "abstained"]
)
def test_public_document_failure_is_not_reported_as_no_answer(
    entry, condition, db_engine, tmp_path, monkeypatch
):
    tokenizer = Tokenizer(Path(default_cache()))
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", str(default_cache()))
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/unused-fake-reranker")
    vectors = LocalVectors(db_engine)
    if condition != "missing_index":
        document_index.prepare(db_engine, tokenizer, EmbeddingProfile(), embedder=vectors)
    if condition == "stale_index":
        changed = deepcopy(document_index.PUBLIC_DOCUMENTS)
        changed[0]["content"] += "\nNew document revision.\n"
        monkeypatch.setattr(document_index, "PUBLIC_DOCUMENTS", changed)

    class UnavailableOrAbstainingWriter:
        def __init__(self):
            self.calls = []

        def generate(self, payload):
            self.calls.append(payload)
            if condition == "provider_error":
                raise RuntimeError("private provider diagnostic")
            return {
                "status": "abstained",
                "claims": [],
                "missing_information": ["The documents do not answer this question."],
                "reason_code": "insufficient_evidence",
            }

    writer = UnavailableOrAbstainingWriter()
    original_gather = online.gather
    captured = []

    def gather(engine, state, **kwargs):
        result = original_gather(
            engine,
            state,
            tokenizer=tokenizer,
            reranker=Ranker(),
            embedder=vectors,
            provider=writer,
            **kwargs,
        )
        captured.append(result)
        return result

    monkeypatch.setattr(document_index, "engine_from_env", lambda: db_engine)
    monkeypatch.setattr(online, "gather", gather)
    demo = PublicDemo(tmp_path / "public.sqlite", factory=Model)
    if entry == "review_queue":
        token = demo.create("document", str(uuid4()))["token"]
    else:
        token = demo.create_walkthrough(str(uuid4()), "new", QUESTION)["token"]
    if condition == "abstained":
        evidence = demo.execute(token, "evidence")
        assert captured[0]["evidence"][0]["result"]["status"] == "abstained"
        assert evidence["missing_information"]
        assert len(writer.calls) == 1
    else:
        with pytest.raises(HTTPException) as failure:
            demo.execute(token, "evidence")
        assert failure.value.status_code == 503
        assert "private provider diagnostic" not in failure.value.detail
        if condition == "provider_error":
            assert len(writer.calls) == 1
            assert captured[0]["evidence"][0]["result"]["status"] == "failed"
        else:
            assert not writer.calls
