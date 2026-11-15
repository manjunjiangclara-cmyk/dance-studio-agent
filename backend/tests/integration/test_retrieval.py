"""Revision-pinned retrieval against real PostgreSQL and deterministic fake vectors."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding import pipeline
from studio_copilot.documents.embedding.provider import EmbeddingError, EmbeddingProfile
from studio_copilot.documents.retrieval.engine import RetrievalError, search
from studio_copilot.persistence.models import (
    Document,
    DocumentChunk,
    DocumentRevision,
    EmbeddingRun,
    EmbeddingVector,
)
from tests.integration.test_embeddings import create_source, fake_http_provider, unit_vector

pytestmark = pytest.mark.integration
AS_OF = date(2026, 6, 1)


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache()))))


class LocalVectors:
    """Two orthogonal directions make nearest-neighbour expectations explicit."""

    def __init__(self, engine, *, hook=None, error=None, index=0):
        self.engine, self.hook, self.error, self.index = engine, hook, error, index
        self.calls = []

    def embed(self, texts, before_attempt=lambda: None):
        assert self.engine.pool.checkedout() == 0
        before_attempt()
        assert self.engine.pool.checkedout() == 0
        self.calls.append(list(texts))
        if self.hook:
            self.hook()
        if self.error:
            raise self.error
        return [unit_vector(self.index) for _ in texts], len(texts)


def prepared(engine, tokenizer, content, *, title="Handbook", profile=None, index=0):
    document_id = create_source(engine, content, title)
    result = pipeline.run(
        engine,
        document_id,
        1,
        tokenizer,
        profile or EmbeddingProfile(),
        embedder=LocalVectors(engine, index=index),
    )
    return document_id, UUID(result["run_id"])


def retrieve(engine, tokenizer, runs, query="cancellations", **kwargs):
    return search(engine, runs, query, AS_OF, tokenizer, **kwargs)


def table_counts(engine):
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (Document, DocumentRevision, EmbeddingRun, DocumentChunk, EmbeddingVector)
        )


def test_keyword_uses_stemming_and_returns_exact_immutable_source_without_api(
    db_engine, tokenizer, monkeypatch
):
    content = "# Attendance\r\n\r\nCancellations require twenty-four hours notice. Café 💃.\r\n"
    document_id, run_id = prepared(db_engine, tokenizer, content)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    before = table_counts(db_engine)
    forbidden = LocalVectors(db_engine, error=AssertionError("keyword called provider"))
    result = retrieve(
        db_engine, tokenizer, [run_id], "cancellation", mode="keyword", embedder=forbidden
    )
    assert not forbidden.calls
    assert result["mode"] == "keyword" and not result["degraded"]
    assert len(result["results"]) == 1
    hit = result["results"][0]
    assert hit["document_id"] == str(document_id) and hit["revision"] == 1
    assert hit["run_id"] == str(run_id) and hit["title"] == "Handbook"
    assert "Café 💃" in hit["text"] and "\r\n" in hit["text"]
    assert hit["keyword_rank"] == 1 and hit["vector_rank"] is None
    assert hit["heading_path"] == ["Attendance"]
    with Session(db_engine) as session:
        chunk = session.get(DocumentChunk, (run_id, hit["chunk_id"]))
        assert hit["source_spans"] == chunk.provenance["source_spans"]
        assert hit["text"] == chunk.text
        assert hit["text_sha256"] == hashlib.sha256(hit["text"].encode()).hexdigest()
    assert table_counts(db_engine) == before


def test_keyword_query_is_and_based_and_not_spelling_fuzzy(db_engine, tokenizer):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    assert retrieve(db_engine, tokenizer, [run_id], mode="keyword")["results"]
    for query in ("cancellations zebra", "cancellatoin", "the and is"):
        assert retrieve(db_engine, tokenizer, [run_id], query, mode="keyword")["results"] == []


def test_exact_vector_search_returns_closest_eligible_vectors(db_engine, tokenizer):
    _, far = prepared(db_engine, tokenizer, "# Clothing\n\nShoes must be clean.\n", index=1)
    _, near = prepared(db_engine, tokenizer, "# Attendance\n\nAbsences need notice.\n", index=0)
    provider = LocalVectors(db_engine)
    result = retrieve(
        db_engine,
        tokenizer,
        [far, near],
        "missed lesson",
        mode="vector",
        allow_api=True,
        embedder=provider,
    )
    assert provider.calls == [["missed lesson"]]
    assert [hit["run_id"] for hit in result["results"]] == [str(near), str(far)]
    assert result["results"][0]["cosine_distance"] == pytest.approx(0)
    assert result["results"][1]["cosine_distance"] == pytest.approx(1)
    assert all(hit["keyword_rank"] is None for hit in result["results"])


def test_unselected_runs_are_not_retrieved(db_engine, tokenizer):
    _, selected = prepared(db_engine, tokenizer, "# Clothing\n\nShoes are clean.\n", index=1)
    prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    assert retrieve(db_engine, tokenizer, [selected], mode="keyword")["results"] == []
    result = retrieve(
        db_engine,
        tokenizer,
        [selected],
        mode="vector",
        allow_api=True,
        embedder=LocalVectors(db_engine),
    )
    assert {hit["run_id"] for hit in result["results"]} == {str(selected)}


def test_hybrid_fuses_existing_ranks_without_another_model_call(db_engine, tokenizer):
    _, keyword_only = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n", index=1
    )
    _, both = prepared(
        db_engine, tokenizer, "# Attendance\n\nCancellations permit makeup.\n", index=0
    )
    fake = LocalVectors(db_engine)
    result = retrieve(
        db_engine, tokenizer, [keyword_only, both], mode="hybrid", allow_api=True, embedder=fake
    )
    assert len(fake.calls) == 1
    for hit in result["results"]:
        expected = sum(
            1 / (60 + hit[key]) for key in ("keyword_rank", "vector_rank") if hit[key] is not None
        )
        assert hit["rrf_score"] == pytest.approx(expected)
    again = retrieve(
        db_engine,
        tokenizer,
        [both, keyword_only],
        mode="hybrid",
        allow_api=True,
        embedder=LocalVectors(db_engine),
    )
    assert [(x["run_id"], x["chunk_id"]) for x in result["results"]] == [
        (x["run_id"], x["chunk_id"]) for x in again["results"]
    ]


def test_identical_passage_text_merges_sources_without_losing_total(db_engine, tokenizer):
    runs = [
        prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")[1]
        for _ in range(5)
    ]
    result = retrieve(db_engine, tokenizer, runs, mode="keyword")
    assert len(result["results"]) == 1
    hit = result["results"][0]
    assert hit["total_sources"] == 5 and len(hit["other_sources"]) == 3
    refs = [hit, *hit["other_sources"]]
    assert len({(x["run_id"], x["chunk_id"]) for x in refs}) == 4


@pytest.mark.parametrize("day", [date(2026, 1, 1), date(2026, 12, 31)])
def test_effective_date_endpoints_are_inclusive(db_engine, tokenizer, day):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    assert search(db_engine, [run_id], "cancellations", day, tokenizer, mode="keyword")["results"]


def test_no_applicable_sources_avoids_api(db_engine, tokenizer):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    fake = LocalVectors(db_engine, error=AssertionError("empty eligible corpus called API"))
    result = search(
        db_engine,
        [run_id],
        "cancellations",
        date(2027, 1, 1),
        tokenizer,
        mode="hybrid",
        allow_api=True,
        embedder=fake,
    )
    assert result["results"] == [] and not fake.calls


@pytest.mark.parametrize("status", ["running", "preparing", "failed"])
def test_incomplete_selected_run_rejects_whole_request(db_engine, tokenizer, status):
    _, good = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    _, bad = prepared(db_engine, tokenizer, "# Policy\n\nShoes must be clean.\n")
    with db_engine.begin() as connection:
        connection.execute(update(EmbeddingRun).where(EmbeddingRun.id == bad).values(status=status))
    fake = LocalVectors(db_engine)
    with pytest.raises(RetrievalError):
        retrieve(db_engine, tokenizer, [good, bad], mode="hybrid", allow_api=True, embedder=fake)
    assert not fake.calls


def test_missing_run_rejects_whole_request_before_api(db_engine, tokenizer):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    fake = LocalVectors(db_engine)
    with pytest.raises(RetrievalError):
        retrieve(
            db_engine, tokenizer, [run_id, uuid4()], mode="hybrid", allow_api=True, embedder=fake
        )
    assert not fake.calls


def test_incompatible_profiles_rejected_even_for_keyword(db_engine, tokenizer):
    _, first = prepared(db_engine, tokenizer, "# One\n\nCancellations require notice.\n")
    _, second = prepared(
        db_engine,
        tokenizer,
        "# Two\n\nCancellations need approval.\n",
        profile=EmbeddingProfile(endpoint="https://other.example/v1"),
    )
    with pytest.raises(RetrievalError):
        retrieve(db_engine, tokenizer, [first, second], mode="keyword")


def test_query_profile_mismatch_rejected_before_provider(db_engine, tokenizer, monkeypatch):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://other.example/v1")
    fake = LocalVectors(db_engine)
    with pytest.raises(RetrievalError):
        retrieve(db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=fake)
    assert not fake.calls


def test_provider_failure_degrades_hybrid_but_not_vector(db_engine, tokenizer):
    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    fake = LocalVectors(db_engine, error=EmbeddingError("provider_error", "unavailable"))
    result = retrieve(db_engine, tokenizer, [run_id], mode="hybrid", allow_api=True, embedder=fake)
    assert result["degraded"] and result["warnings"] and result["results"]
    assert all(hit["vector_rank"] is None for hit in result["results"])
    with pytest.raises((RetrievalError, EmbeddingError)):
        retrieve(db_engine, tokenizer, [run_id], mode="vector", allow_api=True, embedder=fake)


def test_delete_during_embedding_rejects_final_search_without_mixing_sources(db_engine, tokenizer):
    document_id, run_id = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n"
    )

    def remove():
        with db_engine.begin() as connection:
            connection.execute(delete(Document).where(Document.id == document_id))

    fake = LocalVectors(db_engine, hook=remove)
    with pytest.raises(RetrievalError):
        retrieve(db_engine, tokenizer, [run_id], mode="hybrid", allow_api=True, embedder=fake)
    assert len(fake.calls) == 1


def test_replacement_during_embedding_preserves_selected_revision(db_engine, tokenizer):
    document_id, run_id = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n"
    )
    replacement = "# New\n\nAll classes are refundable.\n"

    def replace():
        with Session(db_engine) as session:
            session.add(
                DocumentRevision(
                    document_id=document_id,
                    revision=2,
                    title="New title",
                    filename="new.md",
                    content=replacement,
                    byte_size=len(replacement.encode()),
                    sha256=hashlib.sha256(replacement.encode()).hexdigest(),
                    hash_origin="upload_bytes",
                    ingestion_status="ready",
                )
            )
            session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(current_revision=2, title="New title", content=replacement)
            )
            session.commit()

    result = retrieve(
        db_engine,
        tokenizer,
        [run_id],
        mode="hybrid",
        allow_api=True,
        embedder=LocalVectors(db_engine, hook=replace),
    )
    assert result["results"] and all(
        hit["revision"] == 1 and hit["title"] == "Handbook" for hit in result["results"]
    )
    assert all("refundable" not in hit["text"] for hit in result["results"])


def test_parent_expansion_is_unique_bounded_and_retains_each_hit(db_engine, tokenizer):
    content = "".join(
        f"# Policy {i}\n\n"
        + (f"Cancellations condition {i} requires teacher approval. " * 270)
        + "\n\n"
        for i in range(8)
    )
    _, run_id = prepared(db_engine, tokenizer, content)
    result = retrieve(db_engine, tokenizer, [run_id], mode="keyword")
    assert len(result["results"]) == 6
    assert result["evidence"] and result["evidence_tokens"] <= 12000
    parents = [
        (item["run_id"], item["parent_id"])
        for item in result["evidence"]
        if item["kind"] == "parent"
    ]
    assert len(parents) == len(set(parents))
    for hit in result["results"]:
        assert any(
            hit["text"] in item["text"]
            or (
                item["kind"] == "parent"
                and item["run_id"] == hit["run_id"]
                and item["parent_id"] == hit["parent_id"]
            )
            for item in result["evidence"]
        )


def test_two_revisions_of_one_document_are_rejected(db_engine, tokenizer):
    document_id, first = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n"
    )
    content = "# Policy\n\nCancellations require approval.\n"
    with Session(db_engine) as session:
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=2,
                title="Revised handbook",
                filename="new.md",
                content=content,
                byte_size=len(content.encode()),
                sha256=hashlib.sha256(content.encode()).hexdigest(),
                hash_origin="upload_bytes",
                ingestion_status="ready",
            )
        )
        session.commit()
    second = pipeline.run(
        db_engine, document_id, 2, tokenizer, EmbeddingProfile(), embedder=LocalVectors(db_engine)
    )
    with pytest.raises(RetrievalError):
        retrieve(db_engine, tokenizer, [first, UUID(second["run_id"])], mode="keyword")


def test_open_effective_dates_have_no_artificial_cutoff(db_engine, tokenizer):
    content = "# Policy\n\nCancellations require notice.\n"
    with Session(db_engine) as session:
        document = Document(title="Undated policy", filename="policy.md", content=content)
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                revision=1,
                title="Undated policy",
                filename="policy.md",
                content=content,
                byte_size=len(content.encode()),
                sha256=hashlib.sha256(content.encode()).hexdigest(),
                hash_origin="upload_bytes",
                ingestion_status="ready",
            )
        )
        session.commit()
    run = pipeline.run(
        db_engine, document_id, 1, tokenizer, EmbeddingProfile(), embedder=LocalVectors(db_engine)
    )
    for day in (date(1900, 1, 1), date(2200, 1, 1)):
        result = search(
            db_engine, [UUID(run["run_id"])], "cancellations", day, tokenizer, mode="keyword"
        )
        assert result["results"]
        assert result["results"][0]["effective_from"] is None
        assert result["results"][0]["effective_to"] is None


def test_evidence_token_count_measures_final_joined_text(db_engine, tokenizer):
    runs = [
        prepared(
            db_engine, tokenizer, f"# Policy {i}\n\nCancellations condition {i} needs approval.\n"
        )[1]
        for i in range(7)
    ]
    result = retrieve(db_engine, tokenizer, runs, mode="keyword")
    assert len(result["results"]) == 6
    assert result["evidence_tokens"] == tokenizer.count(
        "\n\n".join(item["text"] for item in result["evidence"])
    )


def test_duplicates_do_not_exhaust_candidate_limit_before_distinct_texts(db_engine, tokenizer):
    runs = [
        prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")[1]
        for _ in range(22)
    ]
    _, distinct = prepared(
        db_engine, tokenizer, "# Exception\n\nCancellations require medical evidence.\n"
    )
    result = retrieve(db_engine, tokenizer, [*runs, distinct], mode="keyword")
    assert len(result["results"]) == 2
    assert {item["total_sources"] for item in result["results"]} == {1, 22}
    assert any(item["run_id"] == str(distinct) for item in result["results"])


def test_search_executes_no_database_writes(db_engine, tokenizer):
    from sqlalchemy import event

    _, run_id = prepared(db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n")
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().upper())

    event.listen(db_engine, "before_cursor_execute", capture)
    try:
        retrieve(
            db_engine,
            tokenizer,
            [run_id],
            mode="hybrid",
            allow_api=True,
            embedder=LocalVectors(db_engine),
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", capture)
    assert statements
    assert all(
        not sql.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE"))
        for sql in statements
    )


def test_delete_between_keyword_and_context_reads_uses_one_consistent_snapshot(
    db_engine, tokenizer
):
    from sqlalchemy import event

    document_id, run_id = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n"
    )
    deleted = False

    def delete_after_keyword(connection, cursor, statement, parameters, context, executemany):
        nonlocal deleted
        if "WITH scored AS" in statement and not deleted:
            deleted = True
            with Session(db_engine) as session:
                session.execute(delete(Document).where(Document.id == document_id))
                session.commit()

    event.listen(db_engine, "after_cursor_execute", delete_after_keyword)
    try:
        result = retrieve(db_engine, tokenizer, [run_id], mode="keyword")
    finally:
        event.remove(db_engine, "after_cursor_execute", delete_after_keyword)
    assert deleted and result["results"] and result["evidence"]
    assert result["results"][0]["document_id"] == str(document_id)
    with Session(db_engine) as session:
        assert session.get(Document, document_id) is None


def test_real_retrieval_cli_keyword_and_vector_use_local_database_and_fake_http(
    db_engine, tokenizer
):
    with db_engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    assert schema.startswith("test_")
    url = db_engine.url.update_query_dict({"options": f"-csearch_path={schema},public"})
    with fake_http_provider() as (endpoint, received):
        _, run_id = prepared(
            db_engine,
            tokenizer,
            "# Policy\n\nCancellations require notice.\n",
            profile=EmbeddingProfile(endpoint=endpoint),
        )
        child_env = {
            **os.environ,
            "DATABASE_URL": url.render_as_string(hide_password=False),
            "OPENAI_EMBEDDING_BASE_URL": endpoint,
            "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
            "NO_PROXY": "127.0.0.1,localhost",
        }
        child_env.pop("OPENAI_API_KEY", None)
        common = [
            "search",
            "--run-id",
            str(run_id),
            "--query",
            "cancellations",
            "--as-of",
            "2026-06-01",
            "--tokenizer-cache",
            os.environ.get("STUDIO_TOKENIZER_CACHE", str(default_cache())),
            "--format",
            "json",
        ]

        def invoke(extra):
            result = subprocess.run(
                [sys.executable, "-m", "studio_copilot.documents.retrieval", *common, *extra],
                env=child_env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)

        before = table_counts(db_engine)
        keyword = invoke(["--mode", "keyword"])
        assert keyword["results"] and received == []
        child_env["OPENAI_API_KEY"] = "fake-local-test-key"
        vector = invoke(["--mode", "vector", "--allow-api"])
        assert vector["results"]
        assert len(received) == 1 and received[0]["input"] == ["cancellations"]
        assert received[0]["dimensions"] == 1536
        assert table_counts(db_engine) == before


@pytest.mark.parametrize("mode", ["keyword", "vector", "hybrid"])
def test_archived_source_is_excluded_even_with_explicit_run_id(db_engine, tokenizer, mode):
    document_id, run_id = prepared(
        db_engine, tokenizer, "# Policy\n\nCancellations require notice.\n"
    )
    with db_engine.begin() as connection:
        connection.execute(
            update(Document).where(Document.id == document_id).values(archived_at=func.now())
        )
    result = retrieve(
        db_engine,
        tokenizer,
        [run_id],
        mode=mode,
        allow_api=True,
        embedder=LocalVectors(db_engine),
    )
    assert result["results"] == []
