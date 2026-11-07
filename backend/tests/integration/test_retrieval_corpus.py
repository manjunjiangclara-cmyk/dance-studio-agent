"""Independent multi-document evaluation checks, always using fake embeddings."""

import os
from pathlib import Path

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingError, EmbeddingProfile
from studio_copilot.documents.retrieval.engine import RetrievalError
from studio_copilot.persistence.models import Document, DocumentRevision
from tests.integration.test_embeddings import create_source, unit_vector

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_corpus_v2" / "corpus.json"


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


class CountingFake:
    def __init__(self):
        self.calls = []

    def embed(self, texts, before_attempt=lambda: None):
        before_attempt()
        self.calls.append(list(texts))
        return [unit_vector() for _ in texts], 7 * len(texts)


def test_prepare_gate_precedes_any_database_or_provider_access(tokenizer):
    from studio_copilot.documents.retrieval import corpus

    class ForbiddenEngine:
        def connect(self, *args, **kwargs):
            pytest.fail("Permission gate touched database")

    with pytest.raises(RetrievalError) as caught:
        corpus.prepare(ForbiddenEngine(), CORPUS, tokenizer, EmbeddingProfile())
    assert caught.value.code == "api_permission"


def test_compare_gate_precedes_any_database_or_provider_access(tokenizer):
    from studio_copilot.documents.retrieval import corpus

    with pytest.raises(RetrievalError) as caught:
        corpus.compare(None, [], CORPUS, tokenizer)
    assert caught.value.code == "api_permission"


def test_prepare_reuses_only_immutable_fixture_documents(db_engine, tokenizer):
    from studio_copilot.documents.retrieval import corpus

    unrelated = create_source(db_engine, content="# Private\n\nNever overwrite this source.")
    fake = CountingFake()
    first = corpus.prepare(
        db_engine, CORPUS, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
    )
    paid_batches = len(fake.calls)
    second = corpus.prepare(
        db_engine, CORPUS, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
    )
    assert first == second
    assert paid_batches > 0 and len(fake.calls) == paid_batches
    with Session(db_engine) as session:
        source = session.get(Document, unrelated)
        assert source.content == "# Private\n\nNever overwrite this source."
        assert source.current_revision == 1
        assert len(session.scalars(select(Document)).all()) == 17
        assert len(session.scalars(select(DocumentRevision)).all()) == 17


@pytest.fixture
def prepared(db_engine, tokenizer):
    from studio_copilot.documents.retrieval import corpus

    return corpus.prepare(
        db_engine,
        CORPUS,
        tokenizer,
        EmbeddingProfile(),
        allow_api=True,
        embedder=CountingFake(),
    )


@pytest.mark.parametrize("selection", ["missing", "extra", "empty", "duplicate"])
def test_run_selection_must_match_complete_corpus_before_api(
    db_engine, tokenizer, prepared, selection
):
    from uuid import uuid4

    from studio_copilot.documents.retrieval import corpus

    selected = {
        "missing": prepared[:-1],
        "extra": [*prepared, uuid4()],
        "empty": [],
        "duplicate": [*prepared[:-1], prepared[0]],
    }[selection]
    fake = CountingFake()
    with pytest.raises(RetrievalError):
        corpus.compare(db_engine, selected, CORPUS, tokenizer, allow_api=True, embedder=fake)
    assert fake.calls == []


def test_profile_mismatch_fails_before_question_embedding(
    db_engine, tokenizer, prepared, monkeypatch
):
    from studio_copilot.documents.retrieval import corpus

    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://different.invalid/v1")
    fake = CountingFake()
    with pytest.raises(RetrievalError) as caught:
        corpus.compare(db_engine, prepared, CORPUS, tokenizer, allow_api=True, embedder=fake)
    assert caught.value.code == "profile_mismatch"
    assert fake.calls == []


def test_compare_pairs_embeddings_is_read_only_and_disclaims_fake_quality(
    db_engine, tokenizer, prepared
):
    from studio_copilot.documents.retrieval import corpus

    fake = CountingFake()
    statements = []

    def observe(connection, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())

    event.listen(db_engine, "before_cursor_execute", observe)
    try:
        report = corpus.compare(
            db_engine,
            prepared,
            CORPUS,
            tokenizer,
            allow_api=True,
            embedder=fake,
            document_vectors_verified=True,
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", observe)
    estimate = corpus.plan(CORPUS, tokenizer, EmbeddingProfile())
    requests = estimate["unique_question_requests"]
    assert report["complete"] is True
    assert report["semantic_quality_measured"] is False
    assert len(fake.calls) == requests
    assert report["question_embedding"]["requests"] == requests
    assert report["question_embedding"]["cache_hits"] >= requests
    assert report["question_embedding"]["reported_tokens"] == 7 * requests
    for mode in ("keyword", "vector", "hybrid"):
        assert len(report["modes"][mode]["cases"]) == 100
        if mode != "keyword":
            assert report["modes"][mode]["semantic_quality_measured"] is False
            assert report["modes"][mode]["target_met"] is False
        for split in ("tuning", "held_out"):
            summary = report["modes"][mode]["summaries"][split]
            assert summary["cases"] == 50
            assert summary["date_exclusion_checks_pass"] is True
            assert summary["answerable"] < 50
    assert statements
    assert all(s.startswith(("SELECT", "WITH", "SET TRANSACTION READ ONLY")) for s in statements)
    assert "SET TRANSACTION READ ONLY" in statements


def test_provider_failures_keep_all_cases_and_count_answerable_as_misses(
    db_engine, tokenizer, prepared
):
    from studio_copilot.documents.retrieval import corpus

    class Unavailable(CountingFake):
        def embed(self, texts, before_attempt=lambda: None):
            before_attempt()
            raise EmbeddingError("provider_error", "Unavailable test provider")

    report = corpus.compare(
        db_engine,
        prepared,
        CORPUS,
        tokenizer,
        allow_api=True,
        embedder=Unavailable(),
        document_vectors_verified=True,
    )
    assert report["complete"] is False
    assert report["semantic_quality_measured"] is False
    assert report["modes"]["keyword"]["complete"] is True
    for mode in ("vector", "hybrid"):
        result = report["modes"][mode]
        assert len(result["cases"]) == 100
        assert result["target_met"] is False
        for split in ("tuning", "held_out"):
            summary = result["summaries"][split]
            assert summary["answerable"] > 0
            assert summary["final_at_6"]["recall"] == 0
            assert summary["failed"] > 0
        assert all(c.get("failed") for c in result["cases"] if c["answerable"])


def test_scoring_uses_visible_source_identity_and_actual_packed_context(
    db_engine, tokenizer, prepared, monkeypatch
):
    from studio_copilot.documents.retrieval import corpus
    from studio_copilot.persistence.models import DocumentChunk, EmbeddingRun

    loaded = corpus.load_corpus(CORPUS)
    case = next(c for c in loaded["cases"] if c["answerable"] and len(c["evidence"]) == 1)
    label = case["evidence"][0]
    by_key = {d["key"]: d for d in loaded["documents"]}
    with Session(db_engine) as session:
        runs = dict(session.execute(select(EmbeddingRun.document_id, EmbeddingRun.id)).all())
        correct_run = runs[corpus.document_id(loaded, by_key[label["document_key"]])]
        wrong_run = next(run for run in prepared if run != correct_run)
        passage = next(
            c
            for c in session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.run_id == correct_run, DocumentChunk.kind == "passage"
                )
            )
            if corpus.covered(
                label,
                [dict(s, document_key=label["document_key"]) for s in c.provenance["source_spans"]],
            )
        )
        digest = passage.text_sha256
    loaded["cases"] = [case]
    monkeypatch.setattr(corpus, "load_corpus", lambda path: loaded)
    span = dict(start=label["start"], end=label["end"])
    item = dict(run_id=str(wrong_run), source_spans=[span], other_sources=[])

    def fake_search(*args, **kwargs):
        candidates = [dict(text_sha256=digest)]
        return dict(
            degraded=False,
            timings=dict.fromkeys(
                (
                    "embedding_seconds",
                    "keyword_seconds",
                    "vector_seconds",
                    "context_seconds",
                    "total_seconds",
                ),
                0.0,
            ),
            reported_tokens=0,
            results=[item],
            evidence=[],
            candidates=dict(keyword=candidates, vector=candidates, fused=candidates),
        )

    monkeypatch.setattr(corpus, "search", fake_search)

    def run_case():
        return corpus.compare(
            db_engine, prepared, CORPUS, tokenizer, allow_api=True, embedder=CountingFake()
        )["modes"]["hybrid"]["cases"][0]

    wrong = run_case()
    assert wrong["fused_at_20"]["recall"] == 1
    assert wrong["final_at_6"]["recall"] == 0
    assert wrong["expanded_evidence"]["recall"] == 0
    assert wrong["missing_evidence"][0]["failure_stage"] == "final_selection"
    assert wrong["missing_evidence"][0]["recovered_by_parent"] is False
    # Only an explicitly returned alternate reference may credit the correct source.
    item["other_sources"] = [dict(run_id=str(correct_run), source_spans=[span])]
    visible = run_case()
    assert visible["final_at_6"]["recall"] == 1
    assert visible["expanded_evidence"]["recall"] == 0


def test_candidate_coverage_excludes_outdated_source_occurrences(
    db_engine, tokenizer, prepared, monkeypatch
):
    from studio_copilot.documents.retrieval import corpus
    from studio_copilot.persistence.models import DocumentChunk, EmbeddingRun

    loaded = corpus.load_corpus(CORPUS)
    case = next(
        c
        for c in loaded["cases"]
        if c["answerable"]
        and len(c["evidence"]) == 1
        and c["evidence"][0]["document_key"] == "attendance_2026"
    )
    label = case["evidence"][0]
    archived = next(d for d in loaded["documents"] if d["key"] == label["document_key"])
    with Session(db_engine) as session:
        run_id = session.scalar(
            select(EmbeddingRun.id).where(
                EmbeddingRun.document_id == corpus.document_id(loaded, archived)
            )
        )
        passage = next(
            c
            for c in session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.run_id == run_id, DocumentChunk.kind == "passage"
                )
            )
            if corpus.covered(
                label,
                [dict(s, document_key=label["document_key"]) for s in c.provenance["source_spans"]],
            )
        )
        digest = passage.text_sha256
    # Inject an invalid label date after loader validation, specifically to prove
    # candidate scoring independently filters expired occurrences of a text hash.
    case["as_of"] = "2027-07-01"
    loaded["cases"] = [case]
    monkeypatch.setattr(corpus, "load_corpus", lambda path: loaded)

    def fake_search(*args, **kwargs):
        candidates = [dict(text_sha256=digest)]
        return dict(
            degraded=False,
            timings=dict.fromkeys(
                (
                    "embedding_seconds",
                    "keyword_seconds",
                    "vector_seconds",
                    "context_seconds",
                    "total_seconds",
                ),
                0.0,
            ),
            reported_tokens=0,
            results=[],
            evidence=[],
            candidates=dict(keyword=candidates, vector=candidates, fused=candidates),
        )

    monkeypatch.setattr(corpus, "search", fake_search)
    report = corpus.compare(
        db_engine, prepared, CORPUS, tokenizer, allow_api=True, embedder=CountingFake()
    )
    result = report["modes"]["hybrid"]["cases"][0]
    assert result["fused_at_20"]["recall"] == 0
    assert result["missing_evidence"][0]["failure_stage"] == "candidate_search"


def test_prepare_conflict_rolls_back_all_new_fixture_sources(db_engine, tokenizer):
    from studio_copilot.documents.retrieval import corpus

    loaded = corpus.load_corpus(CORPUS)
    last = loaded["documents"][-1]
    identity = corpus.document_id(loaded, last)
    with Session(db_engine) as session, session.begin():
        session.add(
            Document(
                id=identity, title="Existing local edits", filename="local.md", content="Keep this"
            )
        )
    fake = CountingFake()
    with pytest.raises(RetrievalError) as caught:
        corpus.prepare(
            db_engine, CORPUS, tokenizer, EmbeddingProfile(), allow_api=True, embedder=fake
        )
    assert caught.value.code == "fixture_conflict"
    assert fake.calls == []
    with Session(db_engine) as session:
        assert len(session.scalars(select(Document)).all()) == 1
        assert session.get(Document, identity).content == "Keep this"
        assert session.scalars(select(DocumentRevision)).all() == []


def test_all_date_excluded_cases_make_zero_question_requests(
    db_engine, tokenizer, prepared, monkeypatch
):
    from studio_copilot.documents.retrieval import corpus

    loaded = corpus.load_corpus(CORPUS)
    loaded["cases"] = [case for case in loaded["cases"] if case["expected_empty"]]
    monkeypatch.setattr(corpus, "load_corpus", lambda path: loaded)
    fake = CountingFake()
    report = corpus.compare(db_engine, prepared, CORPUS, tokenizer, allow_api=True, embedder=fake)
    assert fake.calls == []
    assert report["question_embedding"]["requests"] == 0
    for mode in report["modes"].values():
        assert len(mode["cases"]) == 4
        assert all(c["returned_results"] == 0 for c in mode["cases"])
        for split in ("tuning", "held_out"):
            assert mode["summaries"][split]["answerable"] == 0
            assert mode["summaries"][split]["final_at_6"] is None
            assert mode["summaries"][split]["date_exclusion_checks_pass"]


def test_database_failure_after_paid_step_retains_usage_and_sanitized_partial_report(
    db_engine, tokenizer, prepared
):
    import json

    from sqlalchemy.exc import OperationalError

    from studio_copilot.documents.retrieval import corpus

    failed = False

    def fail_first_vector_query(connection, cursor, statement, parameters, context, many):
        nonlocal failed
        if not failed and "WITH inputs AS MATERIALIZED" in statement:
            failed = True
            raise OperationalError(
                "sql-secret", {"query": "private-question"}, Exception("password-secret")
            )

    fake = CountingFake()
    event.listen(db_engine, "before_cursor_execute", fail_first_vector_query)
    try:
        report = corpus.compare(
            db_engine, prepared, CORPUS, tokenizer, allow_api=True, embedder=fake
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", fail_first_vector_query)
    assert failed is True
    assert report["complete"] is False
    assert report["modes"]["keyword"]["complete"] is True
    assert report["modes"]["hybrid"]["complete"] is True
    assert report["question_embedding"]["reported_tokens"] == 7 * len(fake.calls)
    assert report["question_embedding"]["cache_hits"] >= len(fake.calls)
    failures = [c for c in report["modes"]["vector"]["cases"] if c.get("failed")]
    assert len(failures) == 1
    assert failures[0]["error_code"] == "database_error"
    assert failures[0]["final_at_6"]["recall"] == 0
    assert "secret" not in json.dumps(report)
    assert "private-question" not in json.dumps(report)


def test_isolated_runner_migrates_own_schema_despite_visible_fallback_head(db_engine):
    import importlib.util
    from uuid import uuid4

    from sqlalchemy import create_engine, text
    from sqlalchemy.schema import CreateSchema, DropSchema

    from studio_copilot.persistence.models import Base

    script = CORPUS.parents[3] / "scripts" / "evaluate_retrieval_corpus.py"
    spec = importlib.util.spec_from_file_location("independent_corpus_runner", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    preserved = create_source(db_engine, content="# Fallback policy\n\nDo not touch this document.")
    with db_engine.connect() as connection:
        fallback = connection.scalar(text("SELECT current_schema()"))
        assert connection.scalar(text("SELECT version_num FROM alembic_version"))
    fresh = "test_corpus_runner_" + uuid4().hex
    engine = None
    with db_engine.begin() as connection:
        connection.execute(CreateSchema(fresh))
    try:
        engine = create_engine(
            db_engine.url,
            connect_args={"options": f"-csearch_path={fresh},{fallback},public"},
        )
        with engine.connect() as connection:
            # Reproduce the unsafe precondition: an empty own schema can see the
            # fallback's already-current migration marker and populated tables.
            assert connection.scalar(text("SELECT current_schema()")) == fresh
            assert connection.scalar(text("SELECT count(*) FROM documents")) == 1
            assert connection.scalar(text("SELECT version_num FROM alembic_version"))
        runner.initialize(engine, fresh)
        with engine.connect() as connection:
            owned = set(
                connection.scalars(
                    text("SELECT tablename FROM pg_tables WHERE schemaname=:schema"),
                    dict(schema=fresh),
                )
            )
            assert set(Base.metadata.tables) | {"alembic_version"} <= owned
            assert connection.scalar(text("SELECT count(*) FROM documents")) == 0
            assert connection.scalar(text("SELECT count(*) FROM embedding_vectors")) == 0
            assert connection.scalar(text("SELECT count(*) FROM embedding_runs")) == 0
            assert connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        if engine is not None:
            engine.dispose()
        with db_engine.begin() as connection:
            connection.execute(DropSchema(fresh, cascade=True))
    with Session(db_engine) as session:
        assert (
            session.get(Document, preserved).content
            == "# Fallback policy\n\nDo not touch this document."
        )
        assert len(session.scalars(select(Document)).all()) == 1
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert not connection.scalar(
            text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=:schema)"),
            dict(schema=fresh),
        )
