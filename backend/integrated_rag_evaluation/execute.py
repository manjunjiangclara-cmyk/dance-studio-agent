"""Real API/graph evaluation in a disposable schema; never sends or approves mail."""

import base64
import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from datetime import time as clock_time
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from evaluations.model import MeasuredModel
from evaluations.runner import database_snapshot
from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from studio_copilot.documents import online
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import Embedder, EmbeddingProfile
from studio_copilot.documents.generation.provider import PROMPT_VERSION, GenerationProvider
from studio_copilot.documents.operations.runtime import estimate
from studio_copilot.documents.reranking.dataset import load_dataset as load_sources
from studio_copilot.persistence.models import Conversation, Message, Student

from .runner import BudgetExceeded, output_hash, summarize

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests/fixtures"
ZONE = ZoneInfo("Australia/Melbourne")


@contextmanager
def isolated_database(url):
    """Own one schema while resolving pgvector operators installed in public."""
    schema = "rag_eval_" + uuid4().hex
    admin = create_engine(url)
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
    created = False
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        created = True
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            config = Config(str(BACKEND / "alembic.ini"))
            config.set_main_option("script_location", str(BACKEND / "migrations"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            for table in ("documents", "document_activations", "embedding_runs", "agent_runs"):
                owner = connection.scalar(
                    text(
                        "SELECT n.nspname FROM pg_class c JOIN pg_namespace n "
                        "ON c.relnamespace=n.oid WHERE c.oid=to_regclass(:name)"
                    ),
                    {"name": table},
                )
                if owner != schema:
                    raise RuntimeError("Evaluation table resolved outside its owned schema")
        with postgres_checkpointer(engine) as saver:
            saver.setup()
        yield engine
    finally:
        engine.dispose()
        try:
            if created:
                with admin.begin() as connection:
                    connection.execute(DropSchema(schema, cascade=True))
        finally:
            admin.dispose()


class BudgetModel(MeasuredModel):
    def __init__(self, budget):
        super().__init__(budget.limits[0])
        self.client.close()
        self.client = OpenAI(timeout=20.0, max_retries=0)
        self.budget = budget

    def _request(self, operation, **kwargs):
        # Route, interpretation, and composition share the document-call cap.
        ticket = self.budget.reserve(estimate(json.dumps(kwargs, default=str)), 6000)
        before = len(self.calls)
        try:
            return super()._request(operation, **kwargs)
        finally:
            call = self.calls[-1] if len(self.calls) > before else {}
            self.budget.record(ticket, call.get("input_tokens"), call.get("output_tokens"))


class BudgetEmbedder(Embedder):
    budget = None

    def embed(self, texts, before_attempt=lambda: None):
        tickets = []

        def counted_attempt():
            ticket = self.budget.reserve(sum(estimate(text) for text in texts), 0)
            tickets.append(ticket)
            before_attempt()

        try:
            vectors, usage = super().embed(texts, before_attempt=counted_attempt)
        except BaseException:
            for ticket in tickets:
                self.budget.record(ticket, None, None)
            raise
        for ticket in tickets[:-1]:
            self.budget.record(ticket, None, None)
        self.budget.record(tickets[-1], usage, 0)
        return vectors, usage


class BudgetWriter(GenerationProvider):
    budget = None

    def generate(self, payload):
        ticket = self.budget.reserve(estimate(json.dumps(payload, default=str)), 4000)
        try:
            return super().generate(payload)
        finally:
            call = self.calls[-1] if self.calls else {}
            self.budget.record(ticket, call.get("input_tokens"), call.get("output_tokens"))


def snapshot(engine):
    """These authoritative tables must remain unchanged by draft evaluation."""
    return database_snapshot(engine)


def check_response(response):
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Evaluation API returned HTTP {response.status_code}")
    return response.json()


def prepare_documents(client, engine, budget, *, include_attack=False):
    dataset = load_sources()
    documents = list(dataset["documents"])
    if include_attack:
        attack = FIXTURES / "generation_attack.txt"
        raw = attack.read_bytes()
        documents.append(
            dict(
                key="generation_attack",
                title="Untrusted adversarial appendix",
                file="generation_attack.txt",
                text=raw.decode(),
                sha256=hashlib.sha256(raw).hexdigest(),
                effective_from="2026-01-01",
                effective_to="2028-12-31",
            )
        )
    tokenizer = Tokenizer(Path(os.environ["STUDIO_TOKENIZER_CACHE"]))
    profile = EmbeddingProfile.from_env()
    prepared = []
    for source in documents:
        payload = dict(
            title=source["title"],
            filename=source["file"],
            content_base64=base64.b64encode(source["text"].encode()).decode(),
            effective_from=source["effective_from"],
            effective_to=source["effective_to"],
        )
        document = check_response(client.post("/api/v1/documents", json=payload))
        document_id = UUID(document["id"])
        run = pipeline.run(
            engine, document_id, 1, tokenizer, profile, embedder=BudgetEmbedder(profile)
        )
        if run["status"] != "complete":
            raise RuntimeError("Document preparation did not complete")
        activation = check_response(
            client.post(f"/api/v1/documents/{document_id}/answer-activation")
        )
        status = check_response(client.get(f"/api/v1/documents/{document_id}/answer-activation"))
        if activation["status"] not in ("preparing", "enabled") or status["status"] != "enabled":
            raise RuntimeError("Explicit source activation did not complete")
        prepared.append(dict(key=source["key"], document_id=str(document_id), run_id=run["run_id"]))
    return prepared


def run_case(client, engine, case, budget, model=None):
    """Create a dated fictional email, then use the authenticated start-run API."""
    before = snapshot(engine)
    at = datetime.combine(date.fromisoformat(case["as_of"]), clock_time(12), ZONE)
    with Session(engine) as db, db.begin():
        student = Student(display_name="New enquirer", email=f"{case['id']}@example.com")
        db.add(student)
        db.flush()
        conversation = Conversation(student_id=student.id)
        db.add(conversation)
        db.flush()
        source = Message(
            conversation_id=conversation.id,
            kind="student_email",
            body=case["question"],
            occurred_at=at,
        )
        db.add(source)
        db.flush()
        conversation_id, source_id = str(conversation.id), str(source.id)
    started = time.monotonic()
    prior_failures = len(model.failures) if model is not None else 0
    prior_calls = len(model.calls) if model is not None else 0
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/agent-runs",
        json={"source_message_id": source_id},
    )
    elapsed = round((time.monotonic() - started) * 1000)
    run = check_response(response)
    document_evidence = [item for item in run["evidence"] if item.get("tool") == "document_answer"]
    draft = run.get("draft_details") or {}
    after = snapshot(engine)
    model_failures = model.failures[prior_failures:] if model is not None else []
    incomplete_model_calls = (
        [call["operation"] for call in model.calls[prior_calls:] if not call["completed"]]
        if model is not None
        else []
    )
    failed_document_answers = [
        item.get("result", {}).get("error_code", "document_answer_failed")
        for item in document_evidence
        if item.get("result", {}).get("status") == "failed"
    ]
    technical_failures = [*model_failures, *incomplete_model_calls, *failed_document_answers]
    result = dict(
        id=case["id"],
        status="completed"
        if run["status"] == "awaiting_review" and before == after and not technical_failures
        else "failed",
        run_status=run["status"],
        run_id=run["id"],
        source_message_id=source_id,
        as_of=case["as_of"],
        question=case["question"],
        expected_status=case["expected_status"],
        required_facts=case["required_facts"],
        forbidden_patterns=case["forbidden_patterns"],
        tags=case["tags"],
        draft=draft,
        document_evidence=document_evidence,
        interpretation=run["interpretation"],
        error=run.get("error"),
        technical_failures=technical_failures,
        no_business_change=before == after,
        no_email_delivery=True,  # There is no delivery integration in this API.
        latency_ms=elapsed,
        budget=budget.snapshot(),
        review=None,
    )
    result["output_sha256"] = output_hash(result)
    return result


def execute(url, cases, budget, output, *, dataset_hash, phase):
    """Save after every case, including failures; schema cleanup is guaranteed."""
    rows = []
    report = dict(
        version="integrated-rag-report-v1",
        dataset_sha256=dataset_hash,
        phase=phase,
        model=os.environ["OPENAI_MODEL"],
        generation_prompt_version=PROMPT_VERSION,
        reranker_model=online.L6,
        embedding_profile=EmbeddingProfile.from_env().__dict__,
        results=rows,
        technical_error_types=[],
    )

    original_safe_error = online.safe_error

    def diagnostic_safe_error(error):
        report["technical_error_types"].append(type(error).__name__)
        return original_safe_error(error)

    def save():
        report["summary"] = summarize(rows)
        report["budget"] = budget.snapshot()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")

    BudgetEmbedder.budget = BudgetWriter.budget = budget
    with isolated_database(url) as engine:
        model = BudgetModel(budget)
        app = create_app(
            engine,
            admin_token="synthetic-rag-evaluation",
            agent_service=AgentService(engine, model),
        )
        try:
            with (
                patch.object(online, "Embedder", BudgetEmbedder),
                patch.object(online, "GenerationProvider", BudgetWriter),
                patch.object(online, "safe_error", diagnostic_safe_error),
                TestClient(
                    app, headers={"Authorization": "Bearer synthetic-rag-evaluation"}
                ) as client,
            ):
                report["sources"] = prepare_documents(
                    client, engine, budget, include_attack=any(case.get("inject") for case in cases)
                )
                save()
                for case in cases:
                    if budget.exhausted:
                        break
                    try:
                        row = run_case(client, engine, case, budget, model)
                    except BudgetExceeded:
                        budget.exhausted = True
                        row = dict(
                            id=case["id"], status="failed", error="budget_exceeded", review=None
                        )
                    except Exception as error:
                        row = dict(
                            id=case["id"],
                            status="failed",
                            error_type=type(error).__name__,
                            review=None,
                        )
                    rows.append(row)
                    save()
        finally:
            model.client.close()
            save()
    return report
