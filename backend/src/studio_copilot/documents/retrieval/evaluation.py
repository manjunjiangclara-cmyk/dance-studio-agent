"""Source-position evaluation, separate from generation and paid semantic claims."""

import hashlib
import json
import time
from datetime import date
from pathlib import Path
from statistics import mean
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from studio_copilot.documents.embedding.provider import EmbeddingError
from studio_copilot.documents.operations import OperationsError, current, instrument

from .engine import RetrievalError, search, snapshot


def covered(label, spans):
    """Require full coverage, allowing adjoining ranges from different chunks."""
    cursor = label["start"]
    for span in sorted(spans, key=lambda s: (s["start"], s["end"])):
        if span["start"] > cursor:
            break
        cursor = max(cursor, span["end"])
        if cursor >= label["end"]:
            return True
    return False


def measures(labels, ranked_spans, k):
    selected = [span for spans in ranked_spans[:k] for span in spans]
    return dict(
        recall=sum(covered(label, selected) for label in labels) / len(labels),
        all_evidence=all(covered(label, selected) for label in labels),
        reciprocal_rank=next(
            (
                1 / index
                for index, spans in enumerate(ranked_spans[:k], 1)
                if any(covered(label, spans) for label in labels)
            ),
            0.0,
        ),
    )


def load_fixture(cases_path, *, expected_sha256=None):
    """Validate the complete labelled corpus before any writes or provider calls."""
    cases_path = Path(cases_path)
    cases_raw = cases_path.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(cases_raw).hexdigest() != expected_sha256:
        raise RetrievalError(
            "invalid_labels", "Use the frozen, reviewed retrieval_cases.json fixture."
        )
    fixture = json.loads(cases_raw.decode("utf-8"))
    source_path = cases_path.parent / fixture["source_file"]
    raw = source_path.read_bytes()
    original = raw.decode("utf-8")
    if hashlib.sha256(raw).hexdigest() != fixture["source_sha256"]:
        raise RetrievalError("invalid_labels", "Evaluation fixture source hash does not match.")
    cases = fixture["cases"]
    if (
        len(cases) < 40
        or len({c["id"] for c in cases}) != len(cases)
        or sum(c["split"] == "tuning" for c in cases) < 20
        or sum(c["split"] == "held_out" for c in cases) < 20
    ):
        raise RetrievalError("invalid_labels", "Use at least 40 unique cases, split 20/20 or more.")
    for case in cases:
        labels = case["evidence"]
        if case["split"] not in {"tuning", "held_out"} or bool(labels) != case["answerable"]:
            raise RetrievalError("invalid_labels", "Answerability and evidence labels disagree.")
        for label in labels:
            if (
                not 0 <= label["start"] < label["end"] <= len(original)
                or original[label["start"] : label["end"]] != label["text"]
            ):
                raise RetrievalError(
                    "invalid_labels", "Evidence labels must match original source ranges."
                )
    return fixture, original


@instrument("retrieval")
def evaluate(
    engine,
    run_id,
    cases_path,
    tokenizer,
    *,
    mode="keyword",
    allow_api=False,
    embedder=None,
    continue_on_error=False,
    fixture_data=None,
):
    fixture, original = fixture_data if fixture_data is not None else load_fixture(cases_path)
    cases = fixture["cases"]
    with snapshot(engine) as connection:
        row = (
            connection.execute(
                text("""
            SELECT r.document_id, r.revision, d.sha256, d.effective_from, d.effective_to
            FROM embedding_runs r JOIN document_revisions d
            ON r.document_id=d.document_id AND r.revision=d.revision WHERE r.id=:run_id
            """),
                dict(run_id=run_id),
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["sha256"] != fixture["source_sha256"]:
            raise RetrievalError(
                "invalid_labels", "Select an embedding run of the labelled source."
            )
        for field in ("effective_from", "effective_to"):
            actual = row[field].isoformat() if row[field] else None
            if actual != fixture[field]:
                raise RetrievalError(
                    "invalid_labels", "Selected revision dates differ from the labelled source."
                )
        # One bounded source's passage offsets, without loading any chunk text/vector.
        spans_by_hash = {}
        for chunk in connection.execute(
            text("""
            SELECT text_sha256, provenance->'source_spans' AS spans FROM document_chunks
            WHERE run_id=:run_id AND kind='passage' ORDER BY ordinal
            """),
            dict(run_id=run_id),
        ).mappings():
            spans_by_hash.setdefault(chunk["text_sha256"], []).extend(chunk["spans"])
    reports = []
    for case in cases:
        result = None
        started = time.perf_counter()
        before_embedding = getattr(embedder, "embedding_seconds", None)
        before_tokens = getattr(embedder, "reported_tokens", None)
        try:
            result = search(
                engine,
                [UUID(str(run_id))],
                case["query"],
                date.fromisoformat(case["as_of"]),
                tokenizer,
                mode=mode,
                allow_api=allow_api,
                embedder=embedder,
            )
            if result["degraded"]:
                raise RetrievalError(
                    "evaluation_degraded",
                    "Do not report hybrid quality using degraded keyword-only searches.",
                )
        except (RetrievalError, EmbeddingError, SQLAlchemyError, OperationsError) as error:
            if not continue_on_error and not isinstance(error, OperationsError):
                raise
            reports.append(
                failed_case(
                    case,
                    mode,
                    "database_error" if isinstance(error, SQLAlchemyError) else error.code,
                    timings=result["timings"]
                    if result is not None
                    else dict(
                        embedding_seconds=(
                            embedder.embedding_seconds - before_embedding
                            if before_embedding is not None
                            else None
                        ),
                        keyword_seconds=None,
                        vector_seconds=None,
                        context_seconds=None,
                        total_seconds=time.perf_counter() - started,
                    ),
                    reported_tokens=(
                        result["reported_tokens"]
                        if result is not None
                        else embedder.reported_tokens - before_tokens
                        if before_tokens is not None
                        else None
                    ),
                )
            )
            continue
        entry = dict(
            id=case["id"],
            split=case["split"],
            answerable=case["answerable"],
            returned_results=len(result["results"]),
            warnings=result["warnings"],
            expected_empty=case.get("expected_empty", False),
            timings=result["timings"],
            reported_tokens=result["reported_tokens"],
            result_chunk_ids=[r["chunk_id"] for r in result["results"]],
        )
        if case["answerable"]:
            labels = case["evidence"]
            entry["keyword_at_20"] = measures(
                labels,
                [spans_by_hash[c["text_sha256"]] for c in result["candidates"]["keyword"]],
                20,
            )
            entry["vector_at_20"] = measures(
                labels,
                [spans_by_hash[c["text_sha256"]] for c in result["candidates"]["vector"]],
                20,
            )
            entry["fused_at_20"] = measures(
                labels, [spans_by_hash[c["text_sha256"]] for c in result["candidates"]["fused"]], 20
            )
            entry["final_at_6"] = measures(
                labels, [r["source_spans"] for r in result["results"]], 6
            )
            if mode == "keyword":
                entry["vector_at_20"] = None
            elif mode == "vector":
                entry["keyword_at_20"] = None
            entry["expanded_evidence"] = measures(
                labels, [r["source_spans"] for r in result["evidence"]], 6
            )
            entry["missing_evidence"] = [
                dict(
                    label,
                    failure_stage=(
                        "candidate_search"
                        if not covered(
                            label,
                            [
                                span
                                for c in result["candidates"]["fused"]
                                for span in spans_by_hash[c["text_sha256"]]
                            ],
                        )
                        else "final_selection"
                    ),
                    recovered_by_parent=covered(
                        label,
                        [span for item in result["evidence"] for span in item["source_spans"]],
                    ),
                )
                for label in labels
                if not covered(
                    label, [span for item in result["results"] for span in item["source_spans"]]
                )
            ]
        else:
            entry["returned_without_answer_label"] = bool(result["results"])
        reports.append(entry)
    result = summarize(reports, mode, fixture, embedder)
    result["operations"] = current().budget.snapshot()
    if current().budget.exhausted:
        result["complete"] = False
    return result


def failed_case(case, mode, code, *, timings=None, reported_tokens=None):
    """Sanitized failure diagnostics; unknown stage timings/usage stay null."""
    entry = dict(
        id=case["id"],
        split=case["split"],
        failed=True,
        error_code=code,
        answerable=case["answerable"],
        expected_empty=case.get("expected_empty", False),
        timings=timings
        if timings is not None
        else dict.fromkeys(
            (
                "embedding_seconds",
                "keyword_seconds",
                "vector_seconds",
                "context_seconds",
                "total_seconds",
            )
        ),
        reported_tokens=reported_tokens,
    )
    if case["answerable"]:
        for stage in (
            "keyword_at_20",
            "vector_at_20",
            "fused_at_20",
            "final_at_6",
            "expanded_evidence",
        ):
            entry[stage] = dict(recall=0.0, all_evidence=False, reciprocal_rank=0.0)
        if mode == "keyword":
            entry["vector_at_20"] = None
        elif mode == "vector":
            entry["keyword_at_20"] = None
    return entry


def summarize(reports, mode, fixture, embedder=None):
    summaries = {}
    for split in ("tuning", "held_out"):
        selected = [r for r in reports if r["split"] == split]
        failed = [r for r in selected if r.get("failed")]
        answerable = [r for r in selected if r["answerable"]]
        summaries[split] = dict(cases=len(selected), answerable=len(answerable), failed=len(failed))
        for stage in (
            "keyword_at_20",
            "vector_at_20",
            "fused_at_20",
            "final_at_6",
            "expanded_evidence",
        ):
            measured = [r for r in answerable if r[stage] is not None]
            summaries[split][stage] = (
                {
                    metric: mean(r[stage][metric] for r in measured)
                    for metric in ("recall", "all_evidence", "reciprocal_rank")
                }
                if measured
                else None
            )
        empty = [r for r in selected if r["expected_empty"]]
        summaries[split]["date_exclusion_checks_pass"] = all(
            not r.get("failed") and r["returned_results"] == 0 for r in empty
        )
        summaries[split]["unanswerable_with_results"] = sum(
            r.get("returned_without_answer_label", False) for r in selected
        )
    return dict(
        mode=mode,
        complete=not any(r.get("failed") for r in reports),
        source_sha256=fixture["source_sha256"],
        summaries=summaries,
        cases=reports,
        semantic_quality_measured=mode in {"vector", "hybrid"}
        and (embedder is None or getattr(embedder, "real_provider", False))
        and not any(r.get("failed") for r in reports),
        held_out_recall_target=0.9,
        target_met=(
            summaries["held_out"]["final_at_6"] is not None
            and summaries["held_out"]["final_at_6"]["recall"] >= 0.9
            and not any(r.get("failed") for r in reports)
        ),
        limitations=fixture.get("evaluation_notes", []),
    )
