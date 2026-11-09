"""Offline generation entry points. Paid operations require explicit permission."""

import argparse
import json
import signal
import sys
from pathlib import Path

from studio_copilot.documents.chunking.tokenizer import Tokenizer, default_cache
from studio_copilot.documents.operations.runtime import add_arguments

from .contracts import GenerationError
from .engine import require_api
from .evaluation import answer_directory, evaluate_directory, plan, review_directory
from .prepare import prepare_evidence


def _main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline grounded generation and optional verification."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-evidence")
    prepare.add_argument("--capture-dir", type=Path, required=True)
    prepare.add_argument("--rankings-file", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    for name in ("plan", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--evidence-dir", type=Path, required=True)
        command.add_argument("--split", choices=("tuning", "held_out"))
        command.add_argument("--limit", type=int)
        command.add_argument("--compare-verification", action="store_true")
        command.add_argument("--tokenizer-cache", type=Path, default=default_cache())
        if name == "evaluate":
            command.add_argument("--allow-api", action="store_true")
            command.add_argument("--output-dir", type=Path, required=True)
            command.add_argument("--workers", type=int, default=1)
    command = commands.add_parser("answer")
    command.add_argument("--evidence-file", type=Path, required=True)
    command.add_argument("--output-dir", type=Path, required=True)
    command.add_argument("--allow-api", action="store_true")
    command.add_argument("--verify", action="store_true")
    command.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    command = commands.add_parser("review")
    command.add_argument("--results-dir", type=Path, required=True)
    command.add_argument("--adjudication-file", type=Path, required=True)
    command.add_argument("--output-dir", type=Path, required=True)
    for subparser in commands.choices.values():
        add_arguments(subparser)
    args = parser.parse_args(argv)
    try:
        if args.command in {"answer", "evaluate"}:
            require_api(args.allow_api)
        if args.command == "review":
            result = review_directory(args.results_dir, args.adjudication_file, args.output_dir)
        else:
            try:
                tokenizer = Tokenizer(args.tokenizer_cache)
            except ValueError as error:
                raise GenerationError("tokenizer", str(error)) from None
            if args.command == "prepare-evidence":
                result = prepare_evidence(
                    args.capture_dir, args.rankings_file, args.output_dir, tokenizer
                )
            elif args.command == "plan":
                result = plan(
                    args.evidence_dir,
                    tokenizer,
                    split=args.split,
                    limit=args.limit,
                    compare_verification=args.compare_verification,
                )
            elif args.command == "evaluate":
                result = evaluate_directory(
                    args.evidence_dir,
                    args.output_dir,
                    tokenizer,
                    allow_api=True,
                    compare_verification=args.compare_verification,
                    split=args.split,
                    limit=args.limit,
                    workers=args.workers,
                )
            else:
                result = answer_directory(
                    args.evidence_file,
                    args.output_dir,
                    tokenizer,
                    allow_api=True,
                    verify=args.verify,
                )
        print(json.dumps(result, ensure_ascii=False))
        if args.command in {"answer", "evaluate"} and (
            result.get("execution_status") == "failed"
            or result.get("technical_failures", 0)
            or any(
                summary.get("technical_failures", 0)
                for summary in result.get("summaries", {}).values()
            )
        ):
            return 1
        return 0
    except GenerationError as error:
        print(f"generation: {error.code}: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print(
            "generation: operation failed; inspect inputs, resources and permissions.",
            file=sys.stderr,
        )
        return 1


def main(argv=None):
    from studio_copilot.documents.operations.runtime import run_cli

    return run_cli(_main, argv)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
    raise SystemExit(main())
