"""Run frozen whole-agent cases with explicit paid provider and token limits."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from evaluations.fixtures import validate_database_url
from integrated_rag_evaluation.runner import RunBudget
from studio_copilot.documents.activation import check_setup

from .runner import PHASES, execute, load_suite

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests/fixtures/whole_agent_validation_v1"
FROZEN_MANIFEST_SHA256 = "ab7197b2b3f5dd9e2a5d61265e87b85a6d6a6b801b74c2337a6e25e3779b64d1"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=(*PHASES, "all"))
    parser.add_argument("--case", help="Run one named case within the selected phase")
    parser.add_argument("--allow-paid-api", action="store_true")
    parser.add_argument("--max-requests", type=int, required=True)
    parser.add_argument("--max-input-tokens", type=int, required=True)
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    args = parser.parse_args(argv)
    try:
        manifest, business, documents, phases, digest = load_suite(args.fixtures)
        if args.fixtures.resolve() == FIXTURES.resolve() and digest != FROZEN_MANIFEST_SHA256:
            raise ValueError("Frozen fixture manifest changed")
        if not args.allow_paid_api:
            raise ValueError("Use --allow-paid-api to authorize paid provider requests")
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
            raise ValueError("OPENAI_API_KEY and OPENAI_MODEL are required")
        url = validate_database_url(os.environ.get("TEST_DATABASE_URL"))
        check_setup()
        budget = RunBudget(args.max_requests, args.max_input_tokens, args.max_output_tokens)
        if args.output.exists():
            raise ValueError("Output already exists; choose a fresh path")
        cases = (
            [case for phase in PHASES for case in phases[phase]]
            if args.phase == "all"
            else phases[args.phase]
        )
        expected = len(cases)
        if args.case:
            cases = [case for case in cases if case["id"] == args.case]
            if len(cases) != 1:
                raise ValueError("Unknown or duplicate case ID")
            expected = 1
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = execute(
        url,
        cases,
        business,
        documents,
        budget,
        args.output,
        manifest_hash=digest,
        phase=args.phase,
        expected_count=expected,
    )
    report["started_from_manifest"] = manifest.get("created_at")
    report["finished_at"] = datetime.now(UTC).isoformat()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "summary": report["summary"],
                "budget": report["budget"],
            },
            indent=2,
        )
    )
    return 0 if report["summary"]["completed"] == expected and not report["error_type"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
