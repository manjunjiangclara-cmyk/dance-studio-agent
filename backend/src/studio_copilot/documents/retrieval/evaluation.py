"""Source-position evaluation, separate from generation and paid semantic claims."""

import hashlib
import json
from datetime import date
from pathlib import Path
from statistics import mean
from uuid import UUID

from sqlalchemy import text

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


def evaluate(engine, run_id, cases_path, tokenizer, *, mode="keyword", allow_api=False):
    cases_path = Path(cases_path)
    fixture = json.loads(cases_path.read_text(encoding="utf-8"))
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
        result = search(
            engine,
            [UUID(str(run_id))],
            case["query"],
            date.fromisoformat(case["as_of"]),
            tokenizer,
            mode=mode,
            allow_api=allow_api,
        )
        if result["degraded"]:
            raise RetrievalError(
                "evaluation_degraded",
                "Do not report hybrid quality using degraded keyword-only searches.",
            )
        entry = dict(
            id=case["id"],
            split=case["split"],
            answerable=case["answerable"],
            returned_results=len(result["results"]),
            warnings=result["warnings"],
            expected_empty=case.get("expected_empty", False),
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
        else:
            entry["returned_without_answer_label"] = bool(result["results"])
        reports.append(entry)
    summaries = {}
    for split in ("tuning", "held_out"):
        selected = [r for r in reports if r["split"] == split]
        answerable = [r for r in selected if r["answerable"]]
        summaries[split] = dict(cases=len(selected), answerable=len(answerable))
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
            r["returned_results"] == 0 for r in empty
        )
        summaries[split]["unanswerable_with_results"] = sum(
            r.get("returned_without_answer_label", False) for r in selected
        )
    return dict(
        mode=mode,
        source_sha256=fixture["source_sha256"],
        summaries=summaries,
        cases=reports,
        semantic_quality_measured=mode in {"vector", "hybrid"},
        held_out_recall_target=0.9,
        target_met=(
            summaries["held_out"]["final_at_6"] is not None
            and summaries["held_out"]["final_at_6"]["recall"] >= 0.9
        ),
        limitations=fixture.get("evaluation_notes", []),
    )
