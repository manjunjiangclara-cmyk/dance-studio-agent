"""Paired offline replay, tuning-only model selection, and single fresh validation."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from studio_copilot.documents.chunking import Tokenizer

from .artifacts import load_capture, records, save
from .experiment import adoption, evaluate_case, summarize_cases
from .runtime import MODELS, RerankError, digest, verify_model


def run_phase(capture_dir, cache, tokenizer_cache, output, model_id, phase, selection=None):
    command = [
        sys.executable,
        "-m",
        "studio_copilot.documents.reranking.worker",
        "--capture-dir",
        str(capture_dir),
        "--model-cache",
        str(cache),
        "--tokenizer-cache",
        str(tokenizer_cache),
        "--model-id",
        model_id,
        "--phase",
        phase,
        "--output",
        str(output),
    ]
    if selection is not None:
        command.extend(["--selection-file", str(selection), "--selection-hash", digest(selection)])
    environment = dict(
        os.environ,
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
    )
    # Offline model workers receive no paid-provider or database credentials.
    for name in tuple(environment):
        if name.startswith("OPENAI_") or name in {"DATABASE_URL", "TEST_DATABASE_URL"}:
            environment.pop(name)
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=1800)
    if not output.is_file():
        raise RerankError(
            "worker_failed", "Local model worker failed; comparison remains incomplete."
        )
    report = json.loads(output.read_text())
    if result.returncode and report.get("complete"):
        raise RerankError("worker_failed", "Worker failed after claiming completion.")
    return report


def select_model(development):
    def quality(model_id):
        summary = development[model_id]["summaries"]["tuning"]
        metrics = summary["final_at_6"]
        latency = summary["rerank_latency"]["p95"]
        return (
            not summary["failed"],
            metrics["all_evidence"],
            metrics["recall"],
            metrics["reciprocal_rank"],
            -(latency if latency is not None else float("inf")),
            -MODELS.index(model_id),
        )

    return max(MODELS, key=quality)


def compare_directory(capture_dir, cache, output, tokenizer_cache):
    capture_dir, cache, output = Path(capture_dir), Path(cache), Path(output)
    manifest, dataset = load_capture(capture_dir)
    identities = {model_id: verify_model(cache, model_id) for model_id in MODELS}
    tokenizer = Tokenizer(tokenizer_cache)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = dict(
        version="rerank-comparison-v1",
        created_at=datetime.now(UTC).isoformat(),
        complete=False,
        semantic_quality_measured=False,
        capture=manifest,
        model_identities=identities,
        models={},
        default_search_changed=False,
    )
    save(output / "comparison.json", report)
    try:
        baseline = [
            evaluate_case(case, snapshot, tokenizer)
            for case, snapshot in records(capture_dir, dataset, fresh=False)
        ]
        development = {}
        for model_id in MODELS:
            print(json.dumps(dict(stage="development", model=model_id)), flush=True)
            development[model_id] = run_phase(
                capture_dir,
                cache,
                tokenizer_cache,
                output / (model_id.split("/")[1] + "-development.json"),
                model_id,
                "development",
            )
            report["models"][model_id] = development[model_id]
            save(output / "comparison.json", report)
        selected = select_model(development)
        selection = dict(
            model_id=selected,
            revision=identities[selected]["revision"],
            records_sha256=manifest["records_sha256"],
            dataset_sha256=manifest["dataset_sha256"],
            frozen_at=datetime.now(UTC).isoformat(),
            tuning_report_hashes={
                model_id: digest(output / (model_id.split("/")[1] + "-development.json"))
                for model_id in MODELS
            },
            rule="Tuning only: completeness, recall, MRR, lower warm p95, L6 tie preference.",
            gates=dict(
                complete_evidence_gain=0.025,
                recall_drop=0,
                mrr_drop=0.01,
                multi_source_drop=0,
                warm_p95_seconds=2,
            ),
        )
        selection_path = output / "selection.json"
        save(selection_path, selection)
        report["selection"] = selection
        print(json.dumps(dict(stage="selection_frozen", model=selected)), flush=True)
        # Neither baseline fresh metrics nor fresh model output influences selection.
        baseline.extend(
            evaluate_case(case, snapshot, tokenizer)
            for case, snapshot in records(capture_dir, dataset, fresh=True)
        )
        fresh = run_phase(
            capture_dir,
            cache,
            tokenizer_cache,
            output / "fresh-validation.json",
            selected,
            "fresh",
            selection_path,
        )
        report["fresh_validation"] = fresh
        report["baseline"] = dict(cases=baseline, summaries=summarize_cases(baseline))
        original = report["baseline"]["summaries"]["fresh_validation"]
        reranked = fresh["summaries"]["fresh_validation"]
        report["adoption"] = adoption(original, reranked, reranked["rerank_latency"]["p95"])
        report["complete"] = (
            all(r["complete"] for r in development.values())
            and fresh["complete"]
            and not any(c["failed"] for c in baseline)
        )
        report["semantic_quality_measured"] = (
            report["complete"]
            and manifest.get("real_openai", False)
            and all(r["real_local_model"] for r in (*development.values(), fresh))
        )
        if not report["complete"] or not report["semantic_quality_measured"]:
            report["adoption"] = dict(
                recommended=False, reasons=["incomplete_or_unverified_comparison"]
            )
        report["limitations"] = [
            *dataset["notes"],
            "Previously inspected held-out cases are diagnostic, not fresh validation.",
            "All paths share captured hybrid candidates; no model can recover absent candidates.",
            "Rerank scores are relative relevance, not answerability or calibrated confidence.",
            "No-answer retrieval does not implement sufficiency checks or abstention.",
            "Timing is local CPU measurement, excluding model loading and query embedding.",
        ]
    except Exception as error:
        report.update(
            error_code=getattr(error, "code", "comparison_failed"),
            failure_type=type(error).__name__,
        )
    finally:
        save(output / "comparison.json", report)
    return report
