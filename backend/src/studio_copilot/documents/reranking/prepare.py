"""Explicitly paid real embeddings and candidate capture in an owned test schema."""

import json
import os
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from studio_copilot.documents.chunking import Chunker
from studio_copilot.documents.embedding.provider import Embedder, EmbeddingProfile
from studio_copilot.documents.operations import current, instrument
from studio_copilot.documents.operations.runtime import estimate, preflight
from studio_copilot.documents.retrieval.corpus import _prepare_documents, document_id, source
from studio_copilot.documents.retrieval.experiment import PairedProvider, require_api
from studio_copilot.documents.retrieval.isolation import initialize

from .artifacts import save
from .capture import capture
from .dataset import BACKEND, load_dataset
from .runtime import RerankError, digest


@instrument("reranking")
def plan(tokenizer):
    dataset = load_dataset()
    inputs = {}
    input_bytes = {}
    for document in dataset["documents"]:
        for record in Chunker(source(document), tokenizer).records():
            if record["kind"] == "passage":
                inputs[record["text_sha256"]] = record["token_count"]
                input_bytes[record["text_sha256"]] = estimate(record["text"])
    return dict(
        dataset_sha256=dataset["source_sha256"],
        documents=len(dataset["documents"]),
        cases=len(dataset["cases"]),
        distinct_passages=len(inputs),
        operations=preflight(
            (len(inputs) + 63) // 64 + len(dataset["cases"]),
            sum(input_bytes.values()) + sum(estimate(c["query"]) for c in dataset["cases"]),
            retries=3,
        ),
        document_tokens=sum(inputs.values()),
        question_tokens=sum(
            tokenizer.count(c["query"]) for c in dataset["cases"] if not c["expected_empty"]
        ),
    )


@instrument("reranking")
def capture_directory(output, tokenizer, *, allow_api=False):
    require_api(allow_api)
    url = make_url(os.environ.get("TEST_DATABASE_URL", ""))
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RerankError(
            "configuration", "Use a dedicated PostgreSQL TEST_DATABASE_URL ending _test."
        )
    profile = EmbeddingProfile.from_env()
    if profile.endpoint != "https://api.openai.com/v1" or not os.environ.get("OPENAI_API_KEY"):
        raise RerankError("configuration", "Configure the official OpenAI endpoint and API key.")
    dataset = load_dataset()
    provider = Embedder(profile)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    save(output / "plan.json", plan(tokenizer))
    schema = "reranking_" + uuid4().hex
    admin, engine, created = create_engine(url), None, False
    paired = PairedProvider(provider, real_provider=True)
    manifest = dict(
        version="rerank-capture-v1",
        dataset_sha256=dataset["source_sha256"],
        complete=False,
        schema_cleaned=False,
        operations=current().budget.snapshot(),
        schema=schema,
        cases=0,
        real_openai=True,
        profile=asdict(profile),
        retrieval_version="retrieval-v1",
        retrieval=dict(candidates_per_route=20, final=6, rrf_k=60, budget=12000),
    )
    save(output / "manifest.json", manifest)
    started = time.perf_counter()
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
        initialize(engine, schema, BACKEND / "alembic.ini")
        print(json.dumps(dict(stage="preparing_real_document_vectors")), flush=True)
        runs = _prepare_documents(engine, dataset, tokenizer, profile, embedder=provider)
        by_id = {str(document_id(dataset, d)): d["key"] for d in dataset["documents"]}
        manifest["source_identities"] = [
            dict(document_id=identity, key=key) for identity, key in by_id.items()
        ]
        with (output / "candidates.jsonl").open("w", encoding="utf-8") as stream:
            for case in dataset["cases"]:
                snapshot = capture(
                    engine,
                    runs,
                    case["query"],
                    date.fromisoformat(case["as_of"]),
                    tokenizer,
                    allow_api=True,
                    embedder=paired,
                )
                if snapshot["degraded"]:
                    raise RerankError(
                        "degraded_retrieval", "Stop rather than freeze degraded candidates."
                    )
                for candidate in snapshot["candidates"]:
                    for ref in (candidate, *candidate.get("other_sources", [])):
                        ref["document_key"] = by_id[str(ref["document_id"])]
                stream.write(
                    json.dumps(dict(case_id=case["id"], snapshot=snapshot), ensure_ascii=False)
                    + "\n"
                )
                stream.flush()
                manifest["cases"] += 1
                if manifest["cases"] % 25 == 0:
                    print(json.dumps(dict(stage="capturing", cases=manifest["cases"])), flush=True)
        manifest.update(complete=True, records_sha256=digest(output / "candidates.jsonl"))
    except Exception as error:
        manifest.update(
            error_code=getattr(error, "code", "capture_failed"), failure_type=type(error).__name__
        )
        raise RerankError(
            "capture_failed", "Capture failed; retained manifest records usage and cleanup."
        ) from None
    finally:
        manifest["question_embedding"] = dict(
            requests=paired.requests,
            attempts=paired.attempts,
            reported_tokens=paired.reported_tokens,
            cache_hits=paired.cache_hits,
            seconds=paired.embedding_seconds,
        )
        if engine is not None:
            try:
                with engine.connect() as connection:
                    manifest["preparation"] = dict(
                        connection.execute(
                            text(
                                "SELECT sum(attempts) AS requests, "
                                "sum(reported_tokens) AS reported_tokens, "
                                "count(*) AS runs FROM embedding_runs"
                            )
                        )
                        .mappings()
                        .one()
                    )
            except Exception:
                manifest["preparation"] = None
            engine.dispose()
        try:
            if created:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                manifest["schema_cleaned"] = True
        finally:
            admin.dispose()
            manifest["seconds"] = time.perf_counter() - started
            save(output / "manifest.json", manifest)
    return manifest
