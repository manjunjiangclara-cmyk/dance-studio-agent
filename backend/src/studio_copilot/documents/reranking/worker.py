"""One real CPU model per process; fresh validation requires a frozen selection file."""

import argparse
import json
import resource
import sys
import time
from pathlib import Path

from studio_copilot.documents.chunking import Tokenizer

from .artifacts import load_capture, records, save
from .experiment import evaluate_case, summarize_cases
from .runtime import MODELS, LocalReranker, RerankError, digest, verify_model


def run(args):
    manifest, dataset = load_capture(args.capture_dir)
    identity = verify_model(args.model_cache, args.model_id)
    if args.phase == "fresh":
        if args.selection_file is None or digest(args.selection_file) != args.selection_hash:
            raise RerankError(
                "invalid_selection", "Fresh validation requires the frozen selection."
            )
        selection = json.loads(args.selection_file.read_text())
        if (
            selection["model_id"] != args.model_id
            or selection["revision"] != identity["revision"]
            or selection["records_sha256"] != manifest["records_sha256"]
            or selection["dataset_sha256"] != manifest["dataset_sha256"]
        ):
            raise RerankError("invalid_selection", "Selected model or candidate capture differs.")
    tokenizer = Tokenizer(args.tokenizer_cache)
    started = time.perf_counter()
    load_error = False
    try:
        scorer = LocalReranker(args.model_cache, args.model_id)
        identity = scorer.identity
        # Warm up inference separately from recorded per-question timing.
        scorer.rank(
            "Which requirement applies?",
            [dict(text="An example policy applies.", text_sha256="0" * 64)],
        )
    except Exception:
        load_error = True

        class FailedModel:
            def rank(self, query, candidates):
                raise RerankError("model_load_failed", "Local model initialization failed.")

        scorer = FailedModel()
    load_seconds = time.perf_counter() - started
    cases = [
        evaluate_case(case, snapshot, tokenizer, scorer=scorer)
        for case, snapshot in records(args.capture_dir, dataset, fresh=args.phase == "fresh")
    ]
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report = dict(
        model=identity,
        real_local_model=not load_error,
        complete=not load_error and not any(c["failed"] for c in cases),
        load_and_warmup_seconds=load_seconds,
        cold_load_seconds=None if load_error else scorer.load_seconds,
        warmup_seconds=None if load_error else load_seconds - scorer.load_seconds,
        peak_rss_mib=(rss if sys.platform == "darwin" else rss * 1024) / 1024**2,
        summaries=summarize_cases(cases),
        cases=cases,
    )
    save(args.output, report)
    return 0 if report["complete"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--model-id", choices=MODELS, required=True)
    parser.add_argument("--phase", choices=("development", "fresh"), required=True)
    parser.add_argument("--tokenizer-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--selection-hash")
    args = parser.parse_args()
    try:
        return run(args)
    except Exception:
        print("reranking worker: invalid input or local execution failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
