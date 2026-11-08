"""Source-aware replay metrics and predeclared adoption gates; no provider calls."""

import copy
import math
import time
from statistics import mean

from studio_copilot.documents.retrieval.corpus import covered, measures
from studio_copilot.documents.retrieval.engine import pack_from_records

from .runtime import RerankError


def visible(item):
    return [
        dict(span, document_key=reference["document_key"])
        for reference in (item, *item.get("other_sources", []))
        for span in reference["source_spans"]
    ]


def evaluate_case(case, snapshot, tokenizer, scorer=None):
    started = time.perf_counter()
    entry = dict(
        id=case["id"],
        split=case["split"],
        answerable=case["answerable"],
        expected_empty=case["expected_empty"],
        tags=case.get("tags", []),
        failed=False,
    )
    entry["multi_source"] = len({label["document_key"] for label in case["evidence"]}) > 1
    rerank_seconds = 0.0
    try:
        if snapshot.get("degraded"):
            raise RerankError("degraded_retrieval", "Do not score degraded candidate capture.")
        candidates = snapshot["candidates"]
        if len(candidates) > 40:
            raise RerankError("candidate_limit", "Candidate snapshot exceeds its bound.")
        by_hash = {c["text_sha256"]: c for c in candidates}
        if len(by_hash) != len(candidates):
            raise RerankError("duplicate_candidates", "Snapshot contains duplicate passages.")
        ranked = candidates
        if scorer is not None and candidates:
            before = time.perf_counter()
            scored = scorer.rank(case["query"], copy.deepcopy(candidates))
            rerank_seconds = time.perf_counter() - before
            if len(scored) != len(candidates) or {c["text_sha256"] for c in scored} != set(by_hash):
                raise RerankError("invalid_scores", "Reranking must return the same candidate set.")
            ranked = []
            for result in scored:
                if not math.isfinite(result["rerank_score"]) or result["window_count"] < 1:
                    raise RerankError("invalid_scores", "Invalid score or window count.")
                ranked.append(
                    dict(
                        by_hash[result["text_sha256"]],
                        rerank_score=result["rerank_score"],
                        window_count=result["window_count"],
                    )
                )
        selected = ranked[:6]
        before_context = time.perf_counter()
        evidence, tokens, warnings = pack_from_records(selected, snapshot["parents"], tokenizer)
        context_seconds = time.perf_counter() - before_context
        keys = {
            str(ref["run_id"]): ref["document_key"]
            for c in candidates
            for ref in (c, *c.get("other_sources", []))
        }
        expanded = [
            [dict(span, document_key=keys[str(item["run_id"])]) for span in item["source_spans"]]
            for item in evidence
        ]
        final = [visible(c) for c in selected]
        entry.update(
            returned_results=len(selected),
            evidence_tokens=tokens,
            warnings=warnings,
            rankings=[
                dict(
                    text_sha256=c["text_sha256"],
                    rerank_score=c.get("rerank_score"),
                    window_count=c.get("window_count", 0),
                )
                for c in ranked
            ],
            timings=dict(
                rerank_seconds=rerank_seconds,
                context_seconds=context_seconds,
                total_seconds=time.perf_counter() - started,
            ),
        )
        if case["answerable"]:
            entry["fused_at_20"] = measures(case["evidence"], [visible(c) for c in candidates], 20)
            entry["final_at_6"] = measures(case["evidence"], final, 6)
            entry["expanded_evidence"] = measures(case["evidence"], expanded, len(expanded))
            entry["missing_evidence"] = [
                dict(
                    label,
                    failure_stage="candidate_search"
                    if not covered(label, [s for c in candidates for s in visible(c)])
                    else "final_selection",
                    recovered_by_parent=covered(label, [s for spans in expanded for s in spans]),
                )
                for label in case["evidence"]
                if not covered(label, [s for spans in final for s in spans])
            ]
        else:
            entry["returned_without_answer_label"] = bool(selected)
        return entry
    except Exception as error:
        entry.update(
            failed=True,
            error_code=error.code if isinstance(error, RerankError) else "inference_error",
            returned_results=0,
            timings=dict(
                rerank_seconds=time.perf_counter() - started,
                context_seconds=None,
                total_seconds=time.perf_counter() - started,
            ),
        )
        if case["answerable"]:
            for stage in ("fused_at_20", "final_at_6", "expanded_evidence"):
                entry[stage] = dict(recall=0.0, all_evidence=False, reciprocal_rank=0.0)
        return entry


def summarize_cases(cases):
    summaries = {}
    for split in sorted({c["split"] for c in cases}):
        selected = [c for c in cases if c["split"] == split]
        answers = [c for c in selected if c["answerable"]]
        summary = dict(
            cases=len(selected),
            answerable=len(answers),
            failed=sum(c["failed"] for c in selected),
            date_exclusion_checks_pass=all(
                not c["failed"] and c["returned_results"] == 0
                for c in selected
                if c["expected_empty"]
            ),
            unanswerable_with_results=sum(
                c.get("returned_without_answer_label", False) for c in selected
            ),
        )
        for stage in ("fused_at_20", "final_at_6", "expanded_evidence"):
            summary[stage] = (
                {
                    key: mean(c[stage][key] for c in answers)
                    for key in ("recall", "all_evidence", "reciprocal_rank")
                }
                if answers
                else None
            )
        multi = [c for c in answers if c["multi_source"]]
        summary["multi_source_all_evidence"] = (
            mean(c["final_at_6"]["all_evidence"] for c in multi) if multi else None
        )
        times = sorted(c["timings"]["rerank_seconds"] for c in answers if not c["failed"])
        summary["rerank_latency"] = (
            dict(p50=times[(len(times) - 1) // 2], p95=times[math.ceil(len(times) * 0.95) - 1])
            if times
            else dict(p50=None, p95=None)
        )
        summaries[split] = summary
    return summaries


def adoption(baseline, model, latency_p95):
    reasons = []
    before, after = baseline["final_at_6"], model["final_at_6"]
    if after["all_evidence"] - before["all_evidence"] < 0.025 - 1e-12:
        reasons.append("complete_evidence_gain_below_2_5pp")
    if after["recall"] + 1e-12 < before["recall"]:
        reasons.append("recall_regression")
    if after["reciprocal_rank"] + 0.01 + 1e-12 < before["reciprocal_rank"]:
        reasons.append("mrr_regression")
    if baseline["multi_source_all_evidence"] is not None and (
        model["multi_source_all_evidence"] is None
        or model["multi_source_all_evidence"] + 1e-12 < baseline["multi_source_all_evidence"]
    ):
        reasons.append("multi_source_regression")
    if model["failed"] or baseline["failed"]:
        reasons.append("failed_cases")
    if not model["date_exclusion_checks_pass"] or not baseline["date_exclusion_checks_pass"]:
        reasons.append("date_exclusion_failure")
    if latency_p95 is None or not math.isfinite(latency_p95) or latency_p95 > 2:
        reasons.append("latency_over_2_seconds")
    return dict(recommended=not reasons, reasons=reasons)
