"""Explicitly paid frozen-corpus evaluation in a disposable PostgreSQL test schema.

Never targets the main library. Requires TEST_DATABASE_URL ending in _test,
--allow-api, the official OpenAI endpoint, and a previously prepared tokenizer.
"""

import argparse
import json
import os
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.retrieval import corpus

BACKEND = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """Safe, fixed local setup message."""


def initialize(engine, schema):
    from studio_copilot.documents.retrieval.isolation import initialize as initialize_schema

    initialize_schema(engine, schema, BACKEND / "alembic.ini")


def execute(args):
    # These checks precede output creation, DB access, and provider construction.
    if not args.allow_api:
        raise ConfigurationError("Explicit --allow-api is required for real OpenAI embeddings.")
    url = make_url(os.environ.get("TEST_DATABASE_URL", ""))
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise ConfigurationError(
            "TEST_DATABASE_URL must select a dedicated PostgreSQL _test database."
        )
    profile = EmbeddingProfile.from_env()
    if profile.endpoint != "https://api.openai.com/v1" or not os.environ.get("OPENAI_API_KEY"):
        raise ConfigurationError("Official OpenAI endpoint and API key are required.")
    tokenizer = Tokenizer(args.tokenizer_cache)
    cases = BACKEND / "tests/fixtures/retrieval_corpus_v2/corpus.json"
    planned = corpus.plan(cases, tokenizer, profile)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    def save(name, value):
        (output / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
        )

    save("plan.json", planned)
    schema = "retrieval_corpus_" + uuid.uuid4().hex
    admin = create_engine(url)
    engine = None
    created = False
    started = time.perf_counter()
    manifest = dict(
        schema=schema,
        official_openai=True,
        fake_providers=False,
        schema_cleaned=False,
        complete=False,
        cases_sha256=corpus.CORPUS_SHA256,
        retrieval_parameters_changed=False,
    )
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
        initialize(engine, schema)
        print(json.dumps(dict(stage="preparing_real_vectors")), flush=True)
        before = time.perf_counter()
        runs = corpus.prepare(engine, cases, tokenizer, profile, allow_api=True)
        with engine.connect() as connection:
            prepared = [
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT id, document_id, revision, status, attempts, reported_tokens "
                        "FROM embedding_runs ORDER BY id"
                    )
                ).mappings()
            ]
            vector_count = connection.scalar(text("SELECT count(*) FROM embedding_vectors"))
        save("preparation.json", prepared)
        manifest.update(
            preparation_seconds=time.perf_counter() - before,
            preparation_requests=sum(r["attempts"] for r in prepared),
            preparation_reported_tokens=sum(r["reported_tokens"] for r in prepared),
            vector_count=vector_count,
        )
        print(json.dumps(dict(stage="vectors_complete", vectors=vector_count)), flush=True)
        before = time.perf_counter()
        compared = corpus.compare(
            engine, runs, cases, tokenizer, allow_api=True, document_vectors_verified=True
        )
        save("comparison.json", compared)
        manifest.update(
            comparison_seconds=time.perf_counter() - before,
            complete=compared["complete"],
            semantic_quality_measured=compared["semantic_quality_measured"],
        )
        save(
            "summary.json",
            dict(
                modes={mode: report["summaries"] for mode, report in compared["modes"].items()},
                question_embedding=compared["question_embedding"],
            ),
        )
        print(
            json.dumps(dict(stage="comparison_complete", complete=compared["complete"])), flush=True
        )
        return 0 if compared["complete"] else 1
    except Exception as error:
        manifest.update(
            failure_type=type(error).__name__,
            failure_code=getattr(error, "code", "execution_failed"),
        )
        # Never print raw provider/SQL exception strings, which may include secrets.
        print(json.dumps(dict(stage="failed", failure_type=manifest["failure_type"])), flush=True)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
        try:
            if created:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                manifest["schema_cleaned"] = True
        finally:
            admin.dispose()
            manifest["elapsed_seconds"] = time.perf_counter() - started
            save("manifest.json", manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except Exception as error:
        # Gate messages are safe and useful; other failures remain sanitized.
        message = (
            str(error)
            if isinstance(error, ConfigurationError)
            else "Check configuration and output path."
        )
        print(f"corpus evaluation: {message}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
