"""Frozen multi-document stress evaluation; no retrieval tuning or agent integration."""

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from studio_copilot.documents.chunking import Chunker, Source, Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.pipeline import run
from studio_copilot.documents.embedding.provider import Embedder, EmbeddingError, EmbeddingProfile
from studio_copilot.documents.operations import OperationsError, current, instrument
from studio_copilot.documents.operations.runtime import add_arguments, estimate, preflight, run_cli
from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import Document, DocumentRevision, EmbeddingRun

from .engine import BUDGET, CANDIDATES, RESULTS, VERSION, RetrievalError, _sources, search, snapshot
from .evaluation import covered as range_covered
from .evaluation import failed_case, summarize
from .experiment import PairedProvider, require_api

VERSION_CORPUS = "retrieval-corpus-v2"
CORPUS_SHA256 = "5197ac038a7abbff3b844b0e652cdbad831a1156102c58b04a400c2ecd274b27"


def invalid(message):
    raise RetrievalError("invalid_labels", message)


def applicable(document, as_of):
    value = date.fromisoformat(as_of)
    return (
        not document["effective_from"] or date.fromisoformat(document["effective_from"]) <= value
    ) and (not document["effective_to"] or value <= date.fromisoformat(document["effective_to"]))


def source(document):
    return Source(
        text=document["text"],
        title=document["title"],
        filename=document["file"],
        sha256=document["sha256"],
        byte_size=len(document["text"].encode("utf-8")),
        effective_from=document["effective_from"],
        effective_to=document["effective_to"],
    ).validate()


def load_corpus(path):
    """Verify immutable source bytes and manually authored document-scoped labels."""
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CORPUS_SHA256:
        invalid("Use the frozen reviewed corpus manifest.")
    corpus = json.loads(raw.decode("utf-8"))
    if corpus["version"] != VERSION_CORPUS:
        invalid("Unsupported corpus version.")
    documents = corpus["documents"]
    if len(documents) != 16 or len({d["key"] for d in documents}) != len(documents):
        invalid("Expected sixteen uniquely keyed sources.")
    for document in documents:
        filename = document["file"]
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            invalid("Corpus filenames must be local basenames.")
        content = (path.parent / filename).read_bytes()
        if hashlib.sha256(content).hexdigest() != document["sha256"]:
            invalid("Corpus source hash differs.")
        document["text"] = content.decode("utf-8")
        source(document)
        for field in ("effective_from", "effective_to"):
            if document[field]:
                date.fromisoformat(document[field])
        if (
            document["effective_from"]
            and document["effective_to"]
            and document["effective_from"] > document["effective_to"]
        ):
            invalid("Source dates are reversed.")
    by_key = {d["key"]: d for d in documents}
    cases = corpus["cases"]
    if len(cases) != 100 or len({c["id"] for c in cases}) != len(cases):
        invalid("Expected one hundred unique cases.")
    for split in ("tuning", "held_out"):
        selected = [c for c in cases if c["split"] == split]
        if len(selected) != 50 or sum(c["answerable"] for c in selected) != 40:
            invalid("Each split needs forty answerable and ten diagnostic cases.")
    for case in cases:
        if (
            case["split"] not in {"tuning", "held_out"}
            or bool(case["evidence"]) != case["answerable"]
            or not case["query"].strip()
        ):
            invalid("Invalid case split, query, or answerability.")
        date.fromisoformat(case["as_of"])
        if case["expected_empty"] and (
            case["answerable"] or any(applicable(d, case["as_of"]) for d in documents)
        ):
            invalid("Expected-empty dates must exclude every source.")
        for label in case["evidence"]:
            document = by_key.get(label["document_key"])
            if document is None or not applicable(document, case["as_of"]):
                invalid("Evidence source is missing or ineligible on the question date.")
            start, end = label["start"], label["end"]
            if (
                not 0 <= start < end <= len(document["text"])
                or document["text"][start:end] != label["text"]
            ):
                invalid("Evidence must match original Unicode source offsets.")
    return dict(corpus, source_sha256=digest, evaluation_notes=corpus.get("notes", []))


def covered(label, spans):
    return range_covered(label, [s for s in spans if s["document_key"] == label["document_key"]])


def measures(labels, ranked_spans, k):
    spans = [s for group in ranked_spans[:k] for s in group]
    return dict(
        recall=sum(covered(label, spans) for label in labels) / len(labels),
        all_evidence=all(covered(label, spans) for label in labels),
        reciprocal_rank=next(
            (
                1 / i
                for i, group in enumerate(ranked_spans[:k], 1)
                if any(covered(label, group) for label in labels)
            ),
            0.0,
        ),
    )


@instrument("retrieval")
def plan(path, tokenizer, profile):
    corpus = load_corpus(path)
    inputs = {}
    input_bytes = {}
    passages = parents = byte_size = 0
    for document in corpus["documents"]:
        byte_size += len(document["text"].encode("utf-8"))
        for record in Chunker(source(document), tokenizer).records():
            if record["kind"] == "passage":
                passages += 1
                inputs[record["text_sha256"]] = record["token_count"]
                input_bytes[record["text_sha256"]] = estimate(record["text"])
            else:
                parents += 1
    queries = {
        c["query"]
        for c in corpus["cases"]
        if any(applicable(d, c["as_of"]) for d in corpus["documents"])
    }
    return dict(
        version=VERSION_CORPUS,
        dry_run=True,
        operations=preflight(
            (len(inputs) + 63) // 64 + len(queries),
            sum(input_bytes.values()) + sum(estimate(q) for q in queries),
            retries=3,
        ),
        source_sha256=corpus["source_sha256"],
        documents=len(corpus["documents"]),
        cases=len(corpus["cases"]),
        splits={
            split: sum(c["split"] == split for c in corpus["cases"])
            for split in ("tuning", "held_out")
        },
        source_bytes=byte_size,
        passages=passages,
        parents=parents,
        fresh_document_unique_inputs=len(inputs),
        fresh_document_estimated_tokens=sum(inputs.values()),
        unique_question_requests=len(queries),
        estimated_question_tokens=sum(tokenizer.count(q) for q in queries),
        profile=asdict(profile),
        retrieval=dict(
            version=VERSION,
            candidate_limit=CANDIDATES,
            result_limit=RESULTS,
            evidence_budget=BUDGET,
            rrf_k=60,
            reranker=False,
        ),
        notes=[
            "Local-only estimate; no DB access or provider calls. Retries can add requests.",
            "Vector/hybrid share query embeddings only during one comparison.",
        ],
    )


def document_id(corpus, document):
    return uuid5(
        NAMESPACE_URL, VERSION_CORPUS + ":" + corpus["source_sha256"] + ":" + document["key"]
    )


@instrument("retrieval")
def prepare(engine, path, tokenizer, profile, *, allow_api=False, embedder=None):
    require_api(allow_api)
    corpus = load_corpus(path)
    return _prepare_documents(engine, corpus, tokenizer, profile, embedder=embedder)


def _prepare_documents(engine, corpus, tokenizer, profile, *, embedder=None):
    """Shared immutable preparation after a caller validates its frozen experiment fixture."""
    provider = embedder if embedder is not None else Embedder(profile)
    # Validate the entire set before any writes. Existing source identities are immutable.
    with Session(engine) as session, session.begin():
        for document in corpus["documents"]:
            identity = document_id(corpus, document)
            current = session.get(Document, identity)
            if current is not None:
                revision = session.scalar(
                    select(DocumentRevision).where(
                        DocumentRevision.document_id == identity, DocumentRevision.revision == 1
                    )
                )
                if (
                    revision is None
                    or current.current_revision != 1
                    or any(
                        getattr(revision, field) != expected
                        for field, expected in {
                            "content": document["text"],
                            "title": document["title"],
                            "filename": document["file"],
                            "sha256": document["sha256"],
                            "effective_from": date.fromisoformat(document["effective_from"])
                            if document["effective_from"]
                            else None,
                            "effective_to": date.fromisoformat(document["effective_to"])
                            if document["effective_to"]
                            else None,
                            "ingestion_status": "ready",
                        }.items()
                    )
                ):
                    raise RetrievalError(
                        "fixture_conflict", "Existing corpus source differs; nothing overwritten."
                    )
            else:
                session.add(
                    Document(
                        id=identity,
                        title=document["title"],
                        filename=document["file"],
                        content=document["text"],
                        current_revision=1,
                    )
                )
                session.flush()
                session.add(
                    DocumentRevision(
                        document_id=identity,
                        revision=1,
                        title=document["title"],
                        filename=document["file"],
                        content=document["text"],
                        byte_size=len(document["text"].encode("utf-8")),
                        sha256=document["sha256"],
                        hash_origin="upload_bytes",
                        ingestion_status="ready",
                        effective_from=date.fromisoformat(document["effective_from"])
                        if document["effective_from"]
                        else None,
                        effective_to=date.fromisoformat(document["effective_to"])
                        if document["effective_to"]
                        else None,
                    )
                )
    runs = []
    for document in corpus["documents"]:
        status = run(
            engine, document_id(corpus, document), 1, tokenizer, profile, embedder=provider
        )
        if status["status"] != "complete":
            raise RetrievalError(
                "incomplete_run", "Corpus preparation did not complete; retry explicitly to resume."
            )
        runs.append(UUID(status["run_id"]))
    return runs


@instrument("retrieval")
def compare(
    engine,
    run_ids,
    path,
    tokenizer,
    *,
    allow_api=False,
    embedder=None,
    document_vectors_verified=False,
):
    require_api(allow_api)
    corpus = load_corpus(path)
    run_ids = [UUID(str(value)) for value in run_ids]
    if len(run_ids) != 16 or len(set(run_ids)) != 16:
        invalid("Select sixteen distinct pinned runs.")
    by_id = {document_id(corpus, d): d for d in corpus["documents"]}
    by_run, spans_by_hash = {}, {}
    with snapshot(engine) as connection:
        rows, profile = _sources(
            connection, run_ids, date.fromisoformat(corpus["cases"][0]["as_of"])
        )
        if len(rows) != len(by_id) or {r["document_id"] for r in rows} != set(by_id):
            invalid("Select exactly one pinned run per corpus source.")
        for row in rows:
            document = by_id[row["document_id"]]
            expected = Chunker(source(document), tokenizer)
            metadata = connection.execute(
                select(
                    EmbeddingRun.chunker_hash,
                    EmbeddingRun.chunker_config,
                    DocumentRevision.filename,
                    DocumentRevision.content,
                )
                .join(
                    DocumentRevision,
                    (EmbeddingRun.document_id == DocumentRevision.document_id)
                    & (EmbeddingRun.revision == DocumentRevision.revision),
                )
                .where(EmbeddingRun.id == row["run_id"])
            ).one()
            if (
                row["revision"] != 1
                or row["sha256"] != document["sha256"]
                or row["title"] != document["title"]
                or metadata.filename != document["file"]
                or metadata.content != document["text"]
                or metadata.chunker_hash != expected.config_hash
                or metadata.chunker_config != asdict(expected.config)
                or any(
                    (row[field].isoformat() if row[field] else None) != document[field]
                    for field in ("effective_from", "effective_to")
                )
            ):
                invalid("Selected run differs from frozen source, metadata, or chunker.")
            by_run[str(row["run_id"])] = document
        if profile.key != EmbeddingProfile.from_env().key:
            raise RetrievalError("profile_mismatch", "Configure the selected embedding profile.")
        for chunk in connection.execute(
            text(
                "SELECT run_id, text_sha256, provenance->'source_spans' AS spans "
                "FROM document_chunks WHERE run_id=ANY(:ids) AND kind='passage'"
            ),
            dict(ids=run_ids),
        ).mappings():
            document = by_run[str(chunk["run_id"])]
            spans_by_hash.setdefault(chunk["text_sha256"], []).append(
                (document, [dict(s, document_key=document["key"]) for s in chunk["spans"]])
            )
    paired = PairedProvider(
        embedder if embedder is not None else Embedder(profile),
        real_provider=embedder is None and document_vectors_verified,
    )

    def visible(item):
        return [
            dict(span, document_key=by_run[str(ref["run_id"])]["key"])
            for ref in (item, *item.get("other_sources", []))
            for span in ref["source_spans"]
        ]

    reports = {}
    for mode in ("keyword", "vector", "hybrid"):
        cases = []
        for case in corpus["cases"]:
            started = time.perf_counter()
            before_tokens, before_embedding = paired.reported_tokens, paired.embedding_seconds
            try:
                result = search(
                    engine,
                    run_ids,
                    case["query"],
                    date.fromisoformat(case["as_of"]),
                    tokenizer,
                    mode=mode,
                    allow_api=True,
                    embedder=paired,
                )
                if result["degraded"]:
                    cases.append(
                        failed_case(
                            case,
                            mode,
                            "degraded_retrieval",
                            timings=result["timings"],
                            reported_tokens=result["reported_tokens"],
                        )
                    )
                    continue
                entry = dict(
                    id=case["id"],
                    split=case["split"],
                    answerable=case["answerable"],
                    expected_empty=case["expected_empty"],
                    tags=case.get("tags", []),
                    timings=result["timings"],
                    reported_tokens=result["reported_tokens"],
                    returned_results=len(result["results"]),
                    returned_document_keys=[
                        by_run[str(r["run_id"])]["key"] for r in result["results"]
                    ],
                )
                if case["answerable"]:
                    ranked = {}
                    for route in ("keyword", "vector", "fused"):
                        ranked[route] = [
                            [
                                s
                                for doc, spans in spans_by_hash[c["text_sha256"]]
                                if applicable(doc, case["as_of"])
                                for s in spans
                            ]
                            for c in result["candidates"][route]
                        ]
                        entry[route + "_at_20"] = measures(case["evidence"], ranked[route], 20)
                    if mode == "keyword":
                        entry["vector_at_20"] = None
                    elif mode == "vector":
                        entry["keyword_at_20"] = None
                    final = [visible(r) for r in result["results"]]
                    evidence = [visible(r) for r in result["evidence"]]
                    entry["final_at_6"] = measures(case["evidence"], final, 6)
                    entry["expanded_evidence"] = measures(case["evidence"], evidence, len(evidence))
                    entry["missing_evidence"] = [
                        dict(
                            label,
                            failure_stage="candidate_search"
                            if not covered(label, [s for group in ranked["fused"] for s in group])
                            else "final_selection",
                            recovered_by_parent=covered(
                                label, [s for group in evidence for s in group]
                            ),
                        )
                        for label in case["evidence"]
                        if not covered(label, [s for group in final for s in group])
                    ]
                else:
                    entry["returned_without_answer_label"] = bool(result["results"])
                cases.append(entry)
            except (SQLAlchemyError, RetrievalError, EmbeddingError, OperationsError) as error:
                cases.append(
                    failed_case(
                        case,
                        mode,
                        "database_error" if isinstance(error, SQLAlchemyError) else error.code,
                        timings=dict(
                            embedding_seconds=paired.embedding_seconds - before_embedding,
                            keyword_seconds=None,
                            vector_seconds=None,
                            context_seconds=None,
                            total_seconds=time.perf_counter() - started,
                        ),
                        reported_tokens=paired.reported_tokens - before_tokens,
                    )
                )
        reports[mode] = summarize(cases, mode, corpus, paired)
        reports[mode]["target_met"] &= mode == "keyword" or paired.real_provider
    return dict(
        version=VERSION_CORPUS,
        operations=current().budget.snapshot(),
        created_at=datetime.now(UTC).isoformat(),
        complete=all(r["complete"] for r in reports.values()),
        semantic_quality_measured=paired.real_provider
        and all(r["complete"] for r in reports.values()),
        source_sha256=corpus["source_sha256"],
        sources=[
            dict(
                key=doc["key"],
                sha256=doc["sha256"],
                run_id=identity,
                document_id=str(document_id(corpus, doc)),
                revision=1,
                effective_from=doc["effective_from"],
                effective_to=doc["effective_to"],
            )
            for identity, doc in by_run.items()
        ],
        profile=asdict(profile),
        chunker=dict(hash=expected.config_hash, config=asdict(expected.config)),
        retrieval=dict(
            version=VERSION,
            candidate_limit=CANDIDATES,
            result_limit=RESULTS,
            evidence_budget=BUDGET,
            rrf_k=60,
            reranker=False,
        ),
        document_vectors_verified=document_vectors_verified,
        question_embedding=dict(
            requests=paired.requests,
            attempts=paired.attempts,
            cache_hits=paired.cache_hits,
            reported_tokens=paired.reported_tokens,
            seconds=paired.embedding_seconds,
        ),
        modes=reports,
        limitations=[
            *corpus.get("notes", []),
            "Query vectors are reused; hybrid API latency is not independent.",
            "No-answer results are diagnostics; no abstention or generation is implemented.",
            "Coverage measures supplied labels, not every potentially valid alternative answer.",
        ],
    )


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "prepare", "compare"))
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--run-id", type=UUID, action="append", default=[])
    parser.add_argument("--document-vectors-verified", action="store_true")
    add_arguments(parser)
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.command != "plan":
            require_api(args.allow_api)
        tokenizer, profile = Tokenizer(args.tokenizer_cache), EmbeddingProfile.from_env()
        if args.command == "plan":
            result = plan(args.cases, tokenizer, profile)
        else:
            engine = make_engine()
            if args.command == "prepare":
                result = dict(
                    run_ids=[
                        str(r)
                        for r in prepare(engine, args.cases, tokenizer, profile, allow_api=True)
                    ]
                )
            else:
                result = compare(
                    engine,
                    args.run_id,
                    args.cases,
                    tokenizer,
                    allow_api=True,
                    document_vectors_verified=args.document_vectors_verified,
                )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("complete", True) else 1
    except (RetrievalError, EmbeddingError) as error:
        print(f"corpus evaluation: {error.code}: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("corpus evaluation: database operation failed.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError):
        print("corpus evaluation: invalid fixture or configuration.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


def main(argv=None):
    return run_cli(_main, argv)


if __name__ == "__main__":
    raise SystemExit(main())
