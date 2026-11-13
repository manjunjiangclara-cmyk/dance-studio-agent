"""Run a capped, explicitly paid integrated RAG evaluation in a disposable test schema."""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from evaluations.fixtures import validate_database_url
from studio_copilot.documents.activation import check_setup
from studio_copilot.documents.reranking.dataset import load_dataset as load_sources

from .execute import FIXTURES, execute
from .runner import RunBudget, fingerprint, load_dataset

CASES = FIXTURES / "integrated_rag_cases.json"
CORPUS = FIXTURES / "retrieval_corpus_v2/corpus.json"
FROZEN_CASES_SHA256 = "7aef6bafaa8903f85af78682a46d89ca505e08823783a52ac7b602d04340f963"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("smoke", "evaluation"), required=True)
    parser.add_argument("--case", help="Run one frozen case for diagnostic smoke")
    parser.add_argument("--allow-api", action="store_true", help="Authorize paid provider calls")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-requests", type=int, default=250)
    parser.add_argument("--max-input-tokens", type=int, default=2_000_000)
    parser.add_argument("--max-output-tokens", type=int, default=500_000)
    args = parser.parse_args(argv)
    if hashlib.sha256(CASES.read_bytes()).hexdigest() != FROZEN_CASES_SHA256:
        parser.error("Frozen case manifest changed; review and update its pinned hash first")
    data = load_dataset(CASES)
    cases = data[args.phase]
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error("Unknown case for this phase")
    if not args.allow_api:
        parser.error("Use --allow-api to authorize paid embedding and model requests")
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        parser.error("OPENAI_API_KEY and OPENAI_MODEL are required")
    try:
        url = validate_database_url(os.environ.get("TEST_DATABASE_URL"))
        check_setup()
        load_sources()
        budget = RunBudget(args.max_requests, args.max_input_tokens, args.max_output_tokens)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    output = args.output or (
        Path(__file__).resolve().parents[1]
        / "evaluations/results"
        / f"integrated-rag-{args.phase}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error("Output already exists; choose a fresh path")
    dataset_hash = fingerprint(CASES, CORPUS)
    report = execute(url, cases, budget, output, dataset_hash=dataset_hash, phase=args.phase)
    print(
        json.dumps(
            dict(output=str(output.resolve()), summary=report["summary"], budget=budget.snapshot()),
            indent=2,
        )
    )
    return 0 if report["summary"]["failures"] == 0 and not budget.exhausted else 1


if __name__ == "__main__":
    raise SystemExit(main())
