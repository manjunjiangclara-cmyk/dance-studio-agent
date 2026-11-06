"""Explicit fictional-corpus preparation and paired, ephemeral retrieval evaluation.

No provider is constructed by plan. Normal tests inject fake providers; a live
comparison never infers genuine embeddings merely from a stored model name.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Chunker, Source, Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import Embedder, EmbeddingError, EmbeddingProfile
from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import Document, DocumentRevision, EmbeddingRun

from .engine import BUDGET, CANDIDATES, RESULTS, VERSION, RetrievalError, _sources, snapshot
from .evaluation import evaluate, load_fixture

# Changing either fixture requires a new reviewed experiment version, not hidden tuning.
CASES_SHA256 = "66c7c705416b7dbad903f9c2eeb71f2abdd4355ba5de056aef1d7888140f159e"
EXPERIMENT_VERSION = "retrieval-comparison-v1"
TITLE = "Fictional retrieval evaluation handbook"


def fixture(cases_path):
    path = Path(cases_path)
    labels, original = load_fixture(path, expected_sha256=CASES_SHA256)
    return labels, Source(
        text=original,
        title=TITLE,
        filename=labels["source_file"],
        sha256=labels["source_sha256"],
        byte_size=len(original.encode("utf-8")),
        effective_from=labels["effective_from"],
        effective_to=labels["effective_to"],
    ).validate()


def applicable(case, labels):
    value = date.fromisoformat(case["as_of"])
    return (
        not labels["effective_from"] or date.fromisoformat(labels["effective_from"]) <= value
    ) and (not labels["effective_to"] or value <= date.fromisoformat(labels["effective_to"]))


def plan(cases_path, tokenizer, profile):
    """Local-only fresh preparation estimate, not a billing quote or cache inspection."""
    labels, source = fixture(cases_path)
    chunker = Chunker(source, tokenizer)
    inputs = {}
    for record in chunker.records():
        if record["kind"] == "passage":
            inputs[record["text_sha256"]] = record["token_count"]
    queries = {c["query"] for c in labels["cases"] if applicable(c, labels)}
    return dict(
        version=EXPERIMENT_VERSION,
        dry_run=True,
        source_sha256=source.sha256,
        cases_sha256=CASES_SHA256,
        cases=len(labels["cases"]),
        splits={
            split: sum(c["split"] == split for c in labels["cases"])
            for split in ("tuning", "held_out")
        },
        profile=asdict(profile),
        profile_hash=profile.key,
        chunker_hash=chunker.config_hash,
        fresh_document_unique_inputs=len(inputs),
        fresh_document_estimated_tokens=sum(inputs.values()),
        fresh_document_minimum_requests=(len(inputs) + 63) // 64,
        eligible_questions=sum(applicable(c, labels) for c in labels["cases"]),
        unique_question_requests=len(queries),
        estimated_question_tokens=sum(tokenizer.count(query) for query in queries),
        estimate_notes=[
            "Fresh document estimate ignores existing vector cache; retries may add requests.",
            "Vector and hybrid reuse each question vector within this invocation only.",
            "No database access, provider calls, or live semantic measurement occurred.",
        ],
    )


def require_api(allow_api):
    if not allow_api:
        raise RetrievalError("api_permission", "This experiment requires explicit --allow-api.")


def prepare(engine, cases_path, tokenizer, profile, *, allow_api=False, embedder=None):
    """Explicitly create only the frozen fictional source; never overwrite documents."""
    require_api(allow_api)
    labels, source = fixture(cases_path)
    # Preflight credentials/client before any library write; injected providers are test-only.
    provider = embedder if embedder is not None else Embedder(profile)
    document_id = uuid5(NAMESPACE_URL, EXPERIMENT_VERSION + ":" + CASES_SHA256)
    with Session(engine) as session, session.begin():
        document = session.get(Document, document_id)
        if document is None:
            session.add(
                Document(
                    id=document_id,
                    title=source.title,
                    filename=source.filename,
                    content=source.text,
                    current_revision=1,
                )
            )
            session.flush()
            session.add(
                DocumentRevision(
                    document_id=document_id,
                    revision=1,
                    title=source.title,
                    filename=source.filename,
                    content=source.text,
                    byte_size=source.byte_size,
                    sha256=source.sha256,
                    hash_origin="upload_bytes",
                    ingestion_status="ready",
                    effective_from=date.fromisoformat(labels["effective_from"]),
                    effective_to=date.fromisoformat(labels["effective_to"]),
                )
            )
        else:
            revision = session.scalar(
                select(DocumentRevision).where(
                    DocumentRevision.document_id == document_id, DocumentRevision.revision == 1
                )
            )
            if (
                document.current_revision != 1
                or revision is None
                or revision.sha256 != source.sha256
                or revision.content != source.text
                or revision.title != source.title
                or revision.filename != source.filename
                or str(revision.effective_from) != labels["effective_from"]
                or str(revision.effective_to) != labels["effective_to"]
                or revision.ingestion_status != "ready"
            ):
                raise RetrievalError(
                    "fixture_conflict",
                    "Existing evaluation document differs; nothing was overwritten.",
                )
    status = run(engine, document_id, 1, tokenizer, profile, embedder=provider)
    return dict(
        status,
        experiment_version=EXPERIMENT_VERSION,
        cases_sha256=CASES_SHA256,
        source_sha256=source.sha256,
        provenance="injected_test_provider"
        if embedder is not None
        else "configured_provider_unverified_history",
        note="Prepare is resumable; model labels do not prove cached vector provenance.",
    )


class PairedProvider:
    """One profile, one comparison, no disk/DB cache and no query logging."""

    def __init__(self, provider, *, real_provider=False):
        self.provider, self.real_provider = provider, real_provider
        self.cache = {}
        self.requests = self.cache_hits = self.reported_tokens = self.attempts = 0
        self.embedding_seconds = 0.0

    def embed(self, texts, before_attempt=lambda: None):
        if len(texts) != 1:
            raise EmbeddingError("invalid_input", "Paired evaluation expects one question.")
        query = texts[0]
        if query in self.cache:
            self.cache_hits += 1
            return [self.cache[query]], 0
        self.requests += 1
        started = time.perf_counter()

        def attempted():
            self.attempts += 1
            before_attempt()

        try:
            vectors, usage = self.provider.embed(texts, before_attempt=attempted)
            from studio_copilot.documents.embedding.provider import validate_vector

            if len(vectors) != 1:
                raise EmbeddingError("invalid_vectors", "Expected one question vector.")
            vector = validate_vector(vectors[0])
            self.cache[query] = vector
            self.reported_tokens += usage
            return [vector], usage
        finally:
            self.embedding_seconds += time.perf_counter() - started


def compare(
    engine,
    run_id,
    cases_path,
    tokenizer,
    *,
    allow_api=False,
    embedder=None,
    document_vectors_verified=False,
):
    """Paired fixed-corpus comparison; explicit attestation avoids fake-cache quality claims."""
    require_api(allow_api)
    labels, frozen_source = fixture(cases_path)
    expected_chunker = Chunker(frozen_source, tokenizer)
    run_id = UUID(str(run_id))
    # Validate pinned source and all metadata before constructing any paid client.
    with snapshot(engine) as connection:
        rows, profile = _sources(connection, [run_id], date.fromisoformat(labels["effective_from"]))
        row = rows[0]
        dates = connection.execute(
            select(
                DocumentRevision.effective_from,
                DocumentRevision.effective_to,
                DocumentRevision.title,
                DocumentRevision.filename,
            ).where(
                DocumentRevision.document_id == row["document_id"],
                DocumentRevision.revision == row["revision"],
            )
        ).one()
        metadata = connection.execute(
            select(EmbeddingRun.chunker_hash, EmbeddingRun.chunker_config).where(
                EmbeddingRun.id == run_id
            )
        ).one()
        if row["sha256"] != labels["source_sha256"] or tuple(
            value.isoformat() if value else None for value in dates[:2]
        ) != (labels["effective_from"], labels["effective_to"]):
            raise RetrievalError(
                "invalid_labels", "Selected run does not match frozen source and dates."
            )
        if (
            metadata.chunker_hash != expected_chunker.config_hash
            or metadata.chunker_config != asdict(expected_chunker.config)
            or dates.title != frozen_source.title
            or dates.filename != frozen_source.filename
        ):
            raise RetrievalError(
                "invalid_labels", "Selected run differs from frozen chunker or source metadata."
            )
        if profile.key != EmbeddingProfile.from_env().key:
            raise RetrievalError(
                "profile_mismatch", "Configure the selected run's embedding profile."
            )
        source_identity = dict(
            run_id=str(run_id),
            document_id=str(row["document_id"]),
            revision=row["revision"],
            source_sha256=row["sha256"],
            chunker_hash=metadata.chunker_hash,
            chunker_config=metadata.chunker_config,
        )
    paired = PairedProvider(
        embedder if embedder is not None else Embedder(profile),
        real_provider=embedder is None and document_vectors_verified,
    )
    reports = {}
    for mode in ("keyword", "vector", "hybrid"):
        reports[mode] = evaluate(
            engine,
            run_id,
            cases_path,
            tokenizer,
            mode=mode,
            allow_api=True,
            embedder=paired,
            continue_on_error=True,
            fixture_data=(labels, frozen_source.text),
        )
    complete = all(report["complete"] for report in reports.values())
    measured = complete and paired.real_provider
    latency = {}
    for mode, report in reports.items():
        successful = [c for c in report["cases"] if not c.get("failed")]
        latency[mode] = {
            field: mean(c["timings"][field] for c in successful) if successful else None
            for field in ("keyword_seconds", "vector_seconds", "context_seconds", "total_seconds")
        }
        report["semantic_quality_measured"] = measured and mode != "keyword"
        report["target_met"] = report["target_met"] if mode == "keyword" or measured else False
    return dict(
        version=EXPERIMENT_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        complete=complete,
        semantic_quality_measured=measured,
        provider_provenance="injected_test_provider"
        if embedder is not None
        else "configured_provider",
        document_vectors_verified=document_vectors_verified,
        source=source_identity,
        cases_sha256=CASES_SHA256,
        profile=asdict(profile),
        profile_hash=profile.key,
        retrieval=dict(
            version=VERSION,
            candidate_limit=CANDIDATES,
            result_limit=RESULTS,
            evidence_budget=BUDGET,
            rrf_k=60,
            reranker=False,
        ),
        question_embedding=dict(
            requests=paired.requests,
            attempts=paired.attempts,
            cache_hits=paired.cache_hits,
            reported_tokens=paired.reported_tokens,
            seconds=paired.embedding_seconds,
        ),
        latency_means=latency,
        modes=reports,
        limitations=[
            *labels.get("evaluation_notes", []),
            "Vector reuse changes hybrid embedding latency; compare DB stage timings.",
            "Provider usage is reported tokens, not an invoice or exactly-once billing guarantee.",
            "Document vector origin needs explicit attestation; model names are not proof.",
        ],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "prepare", "compare"):
        command = commands.add_parser(name)
        command.add_argument("--cases", type=Path, required=True)
        command.add_argument("--tokenizer-cache", type=Path, default=default_cache())
        if name != "plan":
            command.add_argument("--allow-api", action="store_true")
        if name == "compare":
            command.add_argument("--run-id", type=UUID, required=True)
            command.add_argument(
                "--document-vectors-verified",
                action="store_true",
                help="Attest document vectors came from the real provider, without fake cache.",
            )
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.command != "plan":
            require_api(args.allow_api)
        tokenizer = Tokenizer(args.tokenizer_cache)
        profile = EmbeddingProfile.from_env()
        if args.command == "plan":
            result = plan(args.cases, tokenizer, profile)
        else:
            engine = make_engine()
            if args.command == "prepare":
                result = prepare(engine, args.cases, tokenizer, profile, allow_api=args.allow_api)
            else:
                result = compare(
                    engine,
                    args.run_id,
                    args.cases,
                    tokenizer,
                    allow_api=args.allow_api,
                    document_vectors_verified=args.document_vectors_verified,
                )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("complete", True) else 1
    except (RetrievalError, EmbeddingError) as error:
        print(f"retrieval experiment: {error.code}: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("retrieval experiment: database operation failed; check setup.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError):
        print(
            "retrieval experiment: invalid configuration or fixture; check setup.", file=sys.stderr
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
