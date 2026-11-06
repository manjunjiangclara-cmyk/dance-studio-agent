"""Measure seven exact-10-MB PostgreSQL embedding runs with a fake provider.

Run from backend with TEST_DATABASE_URL pointing to a disposable *_test database:
python scripts/benchmark_embeddings.py --output-dir /tmp/embedding-benchmark

Each case runs in a fresh process and owns a random schema. Only that schema is
removed. Fixture files and results remain in the explicitly supplied directory.
No model/API calls are made; these measurements say nothing about search quality.
"""

import argparse
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import time
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from benchmark_chunking import CASES, SIZE, TAIL, write_case
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.persistence.models import (
    Document,
    DocumentChunk,
    DocumentRevision,
    EmbeddingRun,
    EmbeddingVector,
)


class FakeEmbedder:
    """A cheap unit-vector fixture, deliberately not a semantic model."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.batches = self.inputs = self.tokens = self.max_batch = 0

    def embed(self, texts, before_attempt=lambda: None):
        assert 1 <= len(texts) <= 64
        before_attempt()
        self.batches += 1
        self.inputs += len(texts)
        self.max_batch = max(self.max_batch, len(texts))
        usage = sum(self.tokenizer.count(value) for value in texts)
        self.tokens += usage
        vectors = []
        for value in texts:
            vector = [0.0] * 1536
            index = int(hashlib.sha256(value.encode()).hexdigest()[:8], 16) % 1536
            vector[index] = 1.0
            vectors.append(vector)
        return vectors, usage


def verify(engine, run_id, original, tokenizer, profile, status):
    run_id = uuid.UUID(run_id)
    counts = {}
    with engine.connect() as connection:
        for kind, limit in (("parent", 2400), ("passage", 900)):
            cursor = count = 0
            rows = connection.execution_options(yield_per=64).execute(
                select(
                    DocumentChunk.text,
                    DocumentChunk.text_sha256,
                    DocumentChunk.token_count,
                    DocumentChunk.provenance,
                    DocumentChunk.vector_key,
                )
                .where(DocumentChunk.run_id == run_id, DocumentChunk.kind == kind)
                .order_by(DocumentChunk.ordinal)
            )
            for row in rows:
                body = next(s for s in row.provenance["source_spans"] if s["role"] == "body")
                assert body["start"] == cursor < body["end"] <= len(original)
                spans = row.provenance["source_spans"]
                parts = [row.provenance["prefix"]]
                parts.extend(
                    original[s["start"] : s["end"]] for s in spans if s["role"] == "table_header"
                )
                overlap = next((s for s in spans if s["role"] == "overlap"), None)
                start = overlap["start"] if overlap else body["start"]
                parts.append(original[start : body["end"]])
                assert row.text == "\n\n".join(parts)
                cursor, count = body["end"], count + 1
                assert row.text_sha256 == hashlib.sha256(row.text.encode()).hexdigest()
                assert row.token_count == tokenizer.count(row.text) <= limit
                if kind == "passage":
                    assert row.vector_key == profile.vector_key(row.text_sha256)
                else:
                    assert row.vector_key is None
            assert cursor == len(original)
            counts[kind] = count
        invalid = connection.scalar(
            text(
                "SELECT count(*) FROM embedding_vectors WHERE "
                "public.vector_dims(embedding) <> 1536 OR "
                "abs(public.vector_norm(embedding) - 1) > 0.001 OR profile_hash <> :profile"
            ),
            {"profile": profile.key},
        )
        assert invalid == 0
        # Check every mapping against actual stored vectors, not just its foreign key.
        linked = connection.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .join(EmbeddingVector, DocumentChunk.vector_key == EmbeddingVector.key)
            .where(
                DocumentChunk.run_id == run_id,
                DocumentChunk.kind == "passage",
                DocumentChunk.text_sha256 == EmbeddingVector.input_sha256,
                DocumentChunk.profile_hash == EmbeddingVector.profile_hash,
            )
        )
        assert linked == counts["passage"] == status["embedded_passages"]
        assert status["status"] == "complete" and not status["lease_active"]
        assert status["chunks"] == sum(counts.values())
        assert connection.scalar(select(func.count()).select_from(EmbeddingRun)) == 1
        counts["vectors"] = connection.scalar(select(func.count()).select_from(EmbeddingVector))
    return counts


def child(args):
    url = make_url(os.environ["TEST_DATABASE_URL"])
    if url.drivername != "postgresql+psycopg" or not url.database.endswith("_test"):
        raise ValueError("Use a postgresql+psycopg TEST_DATABASE_URL ending in _test.")
    schema = "embedding_benchmark_" + (uuid.UUID(args.schema) if args.schema else uuid.uuid4()).hex
    admin = create_engine(url)
    engine = None
    try:
        with admin.begin() as connection:
            # Extension is shared; never drop it during schema cleanup.
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
        with engine.begin() as connection:
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        raw = args.source.read_bytes()
        assert len(raw) == SIZE and raw.endswith(TAIL)
        original = raw.decode("utf-8")
        with Session(engine) as session, session.begin():
            document = Document(title=args.case, filename=args.source.name, content=original)
            session.add(document)
            session.flush()
            document_id = document.id
            session.add(
                DocumentRevision(
                    document_id=document_id,
                    revision=1,
                    title=args.case,
                    filename=args.source.name,
                    content=original,
                    byte_size=SIZE,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    hash_origin="upload_bytes",
                    ingestion_status="ready",
                )
            )
        del raw
        tokenizer = Tokenizer(args.tokenizer_cache)
        # The cache identity cannot ever be confused with a real embedding profile.
        profile = EmbeddingProfile(endpoint="https://benchmark.invalid/v1")
        fake = FakeEmbedder(tokenizer)
        started = time.monotonic()
        status = run(engine, document_id, 1, tokenizer, profile, embedder=fake)
        elapsed = time.monotonic() - started
        verify_started = time.monotonic()
        counts = verify(engine, status["run_id"], original, tokenizer, profile, status)
        verification_seconds = time.monotonic() - verify_started
        before = fake.batches
        resumed = run(engine, document_id, 1, tokenizer, profile, embedder=fake)
        assert resumed == status and fake.batches == before
        assert counts["vectors"] == fake.inputs
        assert fake.batches == status["attempts"]
        assert status["reported_tokens"] == fake.tokens
        assert fake.max_batch <= 64
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes = rss if sys.platform == "darwin" else rss * 1024
        result = {
            "source_bytes": SIZE,
            "elapsed_seconds": round(elapsed, 3),
            "verification_seconds": round(verification_seconds, 3),
            "peak_rss_mib": round(peak_bytes / 1024**2, 2),
            "counts": counts,
            "cache_reused_passages": counts["passage"] - fake.inputs,
            "new_vectors": fake.inputs,
            "fake_batches": fake.batches,
            "max_batch": fake.max_batch,
            "fake_reported_tokens": fake.tokens,
            "warnings": status["warnings"],
            "model_calls": 0,
            "verification": (
                "full source coverage, text/token/vector/mapping checks and no-op replay"
            ),
        }
        assert math.isfinite(elapsed)
        print(json.dumps(result), flush=True)
    finally:
        if engine is not None:
            engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--case", choices=list(CASES), help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--schema", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.case:
        if not args.source:
            parser.error("Child case requires --source.")
        child(args)
        return
    if args.output_dir is None:
        parser.error("--output-dir is required.")
    if not os.environ.get("TEST_DATABASE_URL"):
        parser.error("Set TEST_DATABASE_URL to the disposable PostgreSQL test database.")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    results = {}
    for case in args.cases:
        source = args.output_dir / f"{case}.md"
        write_case(source, *CASES[case])
        schema_id = uuid.uuid4()
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
                    str(schema_id),
                    "--tokenizer-cache",
                    str(args.tokenizer_cache),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
            )
        finally:
            # Also clean up if subprocess.run had to kill a timed-out child, whose
            # Python finally block cannot execute after SIGKILL.
            admin = create_engine(os.environ["TEST_DATABASE_URL"])
            try:
                with admin.begin() as connection:
                    schema = "embedding_benchmark_" + schema_id.hex
                    connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            finally:
                admin.dispose()
        (args.output_dir / f"{case}.log").write_text(completed.stderr)
        if completed.returncode:
            raise RuntimeError(f"{case} failed: {completed.stderr}")
        results[case] = json.loads(completed.stdout)
        print(json.dumps({case: results[case]}), flush=True)
        (args.output_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
