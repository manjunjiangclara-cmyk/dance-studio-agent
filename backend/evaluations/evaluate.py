"""Opt-in paid end-to-end email evaluations: python -m evaluations.evaluate --help."""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Preserve the original script entry point as well as module invocation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluations.cases import CATALOG, DATASET, POLICY, load_scenarios
from evaluations.fixtures import isolated_database, validate_database_url
from evaluations.model import MeasuredModel
from evaluations.runner import build_report, run_scenario


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be at least 1.")
    return number


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="List scenarios without DB or model calls."
    )
    parser.add_argument("--live", action="store_true", help="Run paid calls to OPENAI_MODEL.")
    parser.add_argument(
        "--case", action="append", default=[], help="Select a scenario ID; repeatable."
    )
    parser.add_argument(
        "--repeat", type=positive_int, default=1, help="Independent runs per scenario."
    )
    parser.add_argument(
        "--max-calls-per-case",
        type=positive_int,
        default=24,
        help="Adapter request budget per scenario, excluding bounded SDK retries.",
    )
    parser.add_argument(
        "--output", type=Path, help="JSON report path; default: evaluations/results/."
    )
    args = parser.parse_args(argv)
    scenarios = load_scenarios()
    unknown = set(args.case) - {s.id for s in scenarios}
    if unknown:
        parser.error("Unknown scenario IDs: " + ", ".join(sorted(unknown)))
    selected = [s for s in scenarios if not args.case or s.id in args.case]
    if args.list:
        for scenario in selected:
            print(f"{scenario.id}: {scenario.description}")
        return 0
    if not args.live:
        parser.error("Use --list to inspect scenarios, or --live to run paid model evaluations.")
    try:
        url = validate_database_url(os.environ.get("TEST_DATABASE_URL"))
    except ValueError:
        parser.error(
            "Set TEST_DATABASE_URL using postgresql+psycopg, a _test database, and no URL options."
        )
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        parser.error("Set OPENAI_API_KEY and OPENAI_MODEL before running live evaluations.")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output or Path(__file__).with_name("results") / f"{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset_hash = hashlib.sha256(
        DATASET.read_bytes() + CATALOG.read_bytes() + POLICY.read_bytes()
    ).hexdigest()
    results = []
    for repeat in range(1, args.repeat + 1):
        for scenario in selected:
            model = None
            try:
                # Migrate the isolated schema before constructing a model client.
                with isolated_database(url) as engine:
                    model = MeasuredModel(args.max_calls_per_case)
                    result = run_scenario(engine, scenario, model)
            except Exception as error:
                result = {
                    "case": scenario.id,
                    "passed": False,
                    "checks": [],
                    "error_type": type(error).__name__,
                    "human_review": "pending",
                }
            finally:
                if model is not None:
                    model.client.close()
            result["repeat"] = repeat
            results.append(result)
            report = build_report(results, os.environ["OPENAI_MODEL"], dataset_hash)
            output.write_text(json.dumps(report, indent=2, default=str) + "\n")
            failed = [c["name"] for c in result["checks"] if not c["passed"]]
            status = "PASS" if result["passed"] else "FAIL"
            detail = ", ".join(failed) or result.get("error_type", "")
            print(f"{status} {scenario.id} (repeat {repeat}) {detail}", flush=True)
    print(f"{report['passed']}/{report['total']} automated passes. Human draft review pending.")
    print(f"Report: {output.resolve()}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
