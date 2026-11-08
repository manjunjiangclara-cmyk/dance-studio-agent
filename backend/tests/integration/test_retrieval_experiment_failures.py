"""Database/provider failures retain paid-usage diagnostics without SQL secrets."""

# ruff: noqa: F811

import json
from uuid import UUID

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from studio_copilot.documents.embedding.provider import EmbeddingError, EmbeddingProfile
from studio_copilot.documents.retrieval import evaluation, experiment
from studio_copilot.documents.retrieval.engine import RetrievalError
from tests.integration.test_retrieval_experiment_independent import (
    CASES,
    CountingFake,
    tokenizer,  # noqa: F401
)

pytestmark = pytest.mark.integration


def prepared(db_engine, tokenizer):
    status = experiment.prepare(
        db_engine, CASES, tokenizer, EmbeddingProfile(), allow_api=True, embedder=CountingFake()
    )
    return UUID(status["run_id"])


def database_error():
    return OperationalError(
        "sql-secret", {"query": "private-question"}, Exception("password-secret")
    )


def test_database_error_after_embedding_keeps_usage_and_failed_case(db_engine, tokenizer):  # noqa: F811
    run_id = prepared(db_engine, tokenizer)
    failed = False

    def fail_first_vector_query(connection, cursor, statement, parameters, context, many):
        nonlocal failed
        if not failed and "WITH inputs AS MATERIALIZED" in statement:
            failed = True
            raise database_error()

    event.listen(db_engine, "before_cursor_execute", fail_first_vector_query)
    try:
        report = experiment.compare(
            db_engine, run_id, CASES, tokenizer, allow_api=True, embedder=CountingFake()
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", fail_first_vector_query)
    assert not report["complete"] and not report["semantic_quality_measured"]
    assert report["question_embedding"]["requests"] == 38
    assert report["question_embedding"]["reported_tokens"] == 38 * 7
    assert report["question_embedding"]["cache_hits"] == 38
    failures = [c for c in report["modes"]["vector"]["cases"] if c.get("failed")]
    assert len(failures) == 1 and failures[0]["error_code"] == "database_error"
    assert failures[0]["reported_tokens"] == 7
    assert failures[0]["timings"]["embedding_seconds"] >= 0
    assert failures[0]["timings"]["vector_seconds"] is None
    assert failures[0]["timings"]["total_seconds"] > 0
    assert report["modes"]["vector"]["summaries"]["tuning"]["answerable"] == 18
    assert report["modes"]["hybrid"]["complete"]
    assert "secret" not in json.dumps(report) and "private-question" not in json.dumps(report)


@pytest.mark.parametrize("failure", ["database_error", "source_missing"])
def test_later_mode_preflight_failure_keeps_prior_modes_and_usage(
    db_engine,
    tokenizer,
    monkeypatch,  # noqa: F811
    failure,
):
    run_id = prepared(db_engine, tokenizer)
    original = experiment.evaluate

    def fail_hybrid(*args, **kwargs):
        if kwargs["mode"] == "hybrid":
            if failure == "database_error":
                raise database_error()
            raise RetrievalError("source_missing", "Selected source was deleted.")
        return original(*args, **kwargs)

    monkeypatch.setattr(experiment, "evaluate", fail_hybrid)
    report = experiment.compare(
        db_engine, run_id, CASES, tokenizer, allow_api=True, embedder=CountingFake()
    )
    assert not report["complete"]
    assert report["modes"]["keyword"]["complete"] and report["modes"]["vector"]["complete"]
    assert report["question_embedding"]["requests"] == 38
    assert report["question_embedding"]["reported_tokens"] == 38 * 7
    hybrid = report["modes"]["hybrid"]
    assert len(hybrid["cases"]) == 40 and all(c.get("failed") for c in hybrid["cases"])
    assert hybrid["cases"][0]["error_code"] == failure
    assert hybrid["summaries"]["held_out"]["final_at_6"]["recall"] == 0
    assert all(v is None for v in hybrid["cases"][0]["timings"].values())
    assert not hybrid["target_met"] and not hybrid["semantic_quality_measured"]
    assert "secret" not in json.dumps(report)


def test_degraded_hybrid_retains_available_stage_timings(db_engine, tokenizer):  # noqa: F811
    run_id = prepared(db_engine, tokenizer)

    class Broken:
        def embed(self, texts, before_attempt=lambda: None):
            before_attempt()
            raise EmbeddingError("provider_error", "Unavailable")

    report = evaluation.evaluate(
        db_engine,
        run_id,
        CASES,
        tokenizer,
        mode="hybrid",
        allow_api=True,
        embedder=experiment.PairedProvider(Broken()),
        continue_on_error=True,
    )
    failed = next(c for c in report["cases"] if c.get("failed"))
    assert failed["error_code"] == "evaluation_degraded"
    assert failed["timings"]["keyword_seconds"] >= 0
    assert failed["timings"]["embedding_seconds"] >= 0
    assert failed["timings"]["total_seconds"] > 0
    assert not report["complete"]
