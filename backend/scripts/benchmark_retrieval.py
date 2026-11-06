"""Measure actual PostgreSQL retrieval with fake vectors, never model quality.

Run from backend with TEST_DATABASE_URL ending in _test:
python scripts/benchmark_retrieval.py --output-dir /tmp/retrieval-benchmark

Seven exact-10-MB inputs and a four-document corpus are prepared using the real
chunker/embedding pipeline. Search runs in fresh processes, separate from source
preparation. Each case owns one random schema, never existing application data.
"""

import argparse
import hashlib
import json
import math
import os
import resource
import statistics
import subprocess
import sys
import time
import uuid
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from benchmark_chunking import CASES, SIZE, write_case
from benchmark_embeddings import FakeEmbedder, test_database_url
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.retrieval.engine import search
from studio_copilot.persistence.models import (
    Document,
    DocumentChunk,
    DocumentRevision,
    EmbeddingVector,
)

ENDPOINT = "https://benchmark.invalid/v1"
TIMINGS = (
    "keyword_seconds",
    "vector_seconds",
    "embedding_seconds",
    "context_seconds",
    "total_seconds",
)


def peak_mib():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round((rss if sys.platform == "darwin" else rss * 1024) / 1024**2, 2)


def summary(values):
    ordered = sorted(values)
    return {
        "median": round(statistics.median(ordered), 6),
        "p95": round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 6),
    }


class QueryFake:
    """Fixed unit vector; deliberately unrelated to semantic similarity."""

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        assert len(texts) == 1
        self.calls += 1
        return [[1.0] + [0.0] * 1535], 1


def measure(args):
    os.environ["OPENAI_EMBEDDING_BASE_URL"] = ENDPOINT
    os.environ["OPENAI_EMBEDDING_MODEL"] = "text-embedding-3-small"
    engine = create_engine(
        test_database_url(), connect_args={"options": f"-csearch_path={args.schema},public"}
    )
    tokenizer = Tokenizer(args.tokenizer_cache)
    captured = {}

    def capture(connection, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith("WITH"):
            return
        key = "vector" if "<=>" in statement else "keyword" if "ts_rank_cd" in statement else None
        if key and key not in captured:
            captured[key] = (statement, parameters)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        modes = {}
        for mode in ("keyword", "vector", "hybrid"):
            samples = []
            observations = []
            fake = QueryFake()
            for _ in range(args.repeats):
                for query in ("approval required", "END_OF_SOURCE_10MB", "cancelled class"):
                    before = fake.calls
                    result = search(
                        engine,
                        [uuid.UUID(value) for value in args.run_ids],
                        query,
                        date(2027, 2, 1),
                        tokenizer,
                        mode=mode,
                        allow_api=mode != "keyword",
                        embedder=fake,
                    )
                    assert len(result["results"]) <= 6
                    assert (
                        result["evidence_tokens"]
                        == tokenizer.count("\n\n".join(item["text"] for item in result["evidence"]))
                        <= 12_000
                    )
                    assert fake.calls - before == (mode != "keyword")
                    assert not result["degraded"]
                    for candidates in result["candidates"].values():
                        assert len(candidates) <= 20
                        assert len({c["text_sha256"] for c in candidates}) == len(candidates)
                    samples.append(result["timings"])
                    observations.append(
                        {
                            "query": query,
                            "result_count": len(result["results"]),
                            "timings_seconds": result["timings"],
                        }
                    )
            modes[mode] = {
                "samples": len(samples),
                "timings_seconds": {key: summary([s[key] for s in samples]) for key in TIMINGS},
                "fake_query_calls": fake.calls,
                "real_model_calls": 0,
                "observations": observations,
            }
        event.remove(engine, "before_cursor_execute", capture)
        plans = {}
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            for key, (statement, parameters) in captured.items():
                plans[key] = connection.exec_driver_sql(
                    "EXPLAIN (FORMAT JSON) " + statement, parameters
                ).scalar_one()
            indexes = connection.execute(
                text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=:schema"),
                {"schema": args.schema},
            ).all()
        assert set(plans) == {"keyword", "vector"}
        gin = [definition for _, definition in indexes if "USING gin" in definition]
        assert gin, "Migration did not create a keyword GIN index."
        return {
            "modes": modes,
            "search_peak_rss_mib": peak_mib(),
            "keyword_gin_indexes": gin,
            "explain": plans,
            "semantic_quality": "unmeasured: fixture unit vectors are not semantic embeddings",
            "measurement_notes": (
                "Fresh search process; PostgreSQL buffers may be warm from preparation. "
                "Summaries aggregate three query shapes. Embedding time measures a local "
                "fake call, not OpenAI network latency. EXPLAIN is collected after timing."
            ),
        }
    finally:
        engine.dispose()


def prepare(args):
    admin = create_engine(test_database_url())
    engine = None
    try:
        with admin.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{args.schema}"'))
        engine = create_engine(
            test_database_url(), connect_args={"options": f"-csearch_path={args.schema},public"}
        )
        with engine.begin() as connection:
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        if args.case == "multi-document":
            # Unlike the deliberately repetitive stress cases, this corpus gives
            # every paragraph a distinct identifier to expose exact-scan costs.
            remaining = SIZE
            number = 0
            with args.source.open("wb") as stream:
                while remaining:
                    row = (
                        f"Record {number:06d}: Approval is required for replacement class "
                        f"{number % 101}. Cancellation notice is 24 hours.\n\n"
                    ).encode()
                    output = row[:remaining]
                    stream.write(output)
                    remaining -= len(output)
                    number += 1
        original = args.source.read_bytes()
        assert len(original) == SIZE
        # The multi-document source is ASCII, so byte partitions
        # cannot split a UTF-8 character. Total corpus remains exactly 10 MB.
        parts = (
            [original[n : n + SIZE // 4] for n in range(0, SIZE, SIZE // 4)]
            if args.case == "multi-document"
            else [original]
        )
        tokenizer = Tokenizer(args.tokenizer_cache)
        profile = EmbeddingProfile(endpoint=ENDPOINT)
        fake = FakeEmbedder(tokenizer)
        run_ids = []
        started = time.monotonic()
        for number, raw in enumerate(parts):
            content = raw.decode("utf-8")
            title = f"{args.case}-{number}"
            with Session(engine) as session, session.begin():
                document = Document(title=title, filename=f"{title}.md", content=content)
                session.add(document)
                session.flush()
                document_id = document.id
                session.add(
                    DocumentRevision(
                        document_id=document_id,
                        revision=1,
                        title=title,
                        filename=f"{title}.md",
                        content=content,
                        byte_size=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest(),
                        hash_origin="upload_bytes",
                        ingestion_status="ready",
                    )
                )
            status = run(engine, document_id, 1, tokenizer, profile, embedder=fake)
            assert status["status"] == "complete"
            run_ids.append(status["run_id"])
        preparation_seconds = time.monotonic() - started
        with engine.begin() as connection:
            # Refresh planner statistics after bulk fixture preparation, matching
            # a settled corpus rather than measuring stale planner estimates.
            connection.execute(text("ANALYZE document_chunks"))
            connection.execute(text("ANALYZE embedding_vectors"))
            counts = dict(
                connection.execute(
                    select(DocumentChunk.kind, func.count()).group_by(DocumentChunk.kind)
                ).all()
            )
            counts["distinct_passage_texts"] = connection.scalar(
                select(func.count(func.distinct(DocumentChunk.text_sha256))).where(
                    DocumentChunk.kind == "passage"
                )
            )
            counts["vectors"] = connection.scalar(select(func.count()).select_from(EmbeddingVector))
        search_process = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--measure",
                "--schema",
                args.schema,
                "--run-ids",
                *run_ids,
                "--tokenizer-cache",
                str(args.tokenizer_cache),
                "--repeats",
                str(args.repeats),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if search_process.returncode:
            raise RuntimeError(f"Search subprocess failed: {search_process.stderr}")
        return dict(
            json.loads(search_process.stdout),
            source_bytes=SIZE,
            documents=len(parts),
            chunk_counts=counts,
            preparation_seconds=round(preparation_seconds, 3),
            preparation_peak_rss_mib=peak_mib(),
            real_model_calls=0,
        )
    finally:
        if engine is not None:
            engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{args.schema}" CASCADE'))
        admin.dispose()


def evaluate_keyword(args):
    """Run the labelled lexical baseline without any real embedding provider."""
    from studio_copilot.documents.retrieval.evaluation import evaluate

    fixture_dir = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    cases_path = fixture_dir / "retrieval_cases.json"
    fixture = json.loads(cases_path.read_text())
    raw = (fixture_dir / fixture["source_file"]).read_bytes()
    schema = "retrieval_benchmark_" + uuid.uuid4().hex
    admin = create_engine(test_database_url())
    engine = None
    try:
        with admin.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(
            test_database_url(), connect_args={"options": f"-csearch_path={schema},public"}
        )
        with engine.begin() as connection:
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with Session(engine) as session, session.begin():
            document = Document(
                title="Fictional Retrieval Handbook",
                filename=fixture["source_file"],
                content=raw.decode(),
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
                    content=raw.decode(),
                    byte_size=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    hash_origin="upload_bytes",
                    ingestion_status="ready",
                    effective_from=date.fromisoformat(fixture["effective_from"]),
                    effective_to=date.fromisoformat(fixture["effective_to"]),
                )
            )
        tokenizer = Tokenizer(args.tokenizer_cache)
        profile = EmbeddingProfile(endpoint=ENDPOINT)
        status = run(engine, document_id, 1, tokenizer, profile, embedder=FakeEmbedder(tokenizer))
        result = evaluate(engine, uuid.UUID(status["run_id"]), cases_path, tokenizer)
        result["real_model_calls"] = 0
        result["embedding_preparation"] = "fake unit vectors; unused by keyword search"
        return result
    finally:
        if engine is not None:
            engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()


def main():
    cases = [*CASES, "multi-document"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    parser.add_argument("--cases", nargs="+", choices=cases, default=cases)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--evaluate-keyword",
        action="store_true",
        help="Run only the 40-question labelled keyword baseline, with zero model calls.",
    )
    parser.add_argument("--case", choices=cases, help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--schema", help=argparse.SUPPRESS)
    parser.add_argument("--run-ids", nargs="+", help=argparse.SUPPRESS)
    parser.add_argument("--measure", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20:
        parser.error("--repeats must be between 1 and 20.")
    test_database_url()
    if args.schema:
        # The internal subprocess argument is never interpolated unchecked.
        if not args.schema.startswith("retrieval_benchmark_"):
            parser.error("Invalid benchmark schema.")
        uuid.UUID(hex=args.schema.removeprefix("retrieval_benchmark_"))
    if args.measure:
        print(json.dumps(measure(args)), flush=True)
        return
    if args.case:
        print(json.dumps(prepare(args)), flush=True)
        return
    if args.output_dir is None:
        parser.error("--output-dir is required.")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    if args.evaluate_keyword:
        result = evaluate_keyword(args)
        (args.output_dir / "keyword-evaluation.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        print(json.dumps(result["summaries"]), flush=True)
        return
    results = {}
    for case in args.cases:
        source = args.output_dir / f"{case}.md"
        write_case(source, *CASES["short-blocks" if case == "multi-document" else case])
        schema = "retrieval_benchmark_" + uuid.uuid4().hex
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--case",
                    case,
                    "--source",
                    str(source),
                    "--schema",
                    schema,
                    "--tokenizer-cache",
                    str(args.tokenizer_cache),
                    "--repeats",
                    str(args.repeats),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
            )
        finally:
            admin = create_engine(test_database_url())
            try:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            finally:
                admin.dispose()
        (args.output_dir / f"{case}.log").write_text(completed.stderr)
        if completed.returncode:
            raise RuntimeError(f"{case} failed: {completed.stderr}")
        results[case] = json.loads(completed.stdout)
        (args.output_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps({case: results[case]}), flush=True)


if __name__ == "__main__":
    main()
