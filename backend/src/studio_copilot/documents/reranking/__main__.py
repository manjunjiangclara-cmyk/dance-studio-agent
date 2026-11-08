"""Explicit offline reranking experiment; normal search remains unchanged."""

import argparse
import json
import sys
from pathlib import Path

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache

from .compare import compare_directory
from .prepare import capture_directory, plan
from .runtime import RerankError, prepare_models


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-models")
    prepare.add_argument("--model-cache", type=Path, required=True)
    prepare.add_argument("--allow-download", action="store_true")
    dry = commands.add_parser("plan")
    dry.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    capture = commands.add_parser("capture")
    capture.add_argument("--output-dir", type=Path, required=True)
    capture.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    capture.add_argument("--allow-api", action="store_true")
    compare = commands.add_parser("compare")
    compare.add_argument("--capture-dir", type=Path, required=True)
    compare.add_argument("--model-cache", type=Path, required=True)
    compare.add_argument("--output-dir", type=Path, required=True)
    compare.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-models":
            result = dict(
                models=prepare_models(args.model_cache, allow_download=args.allow_download)
            )
        elif args.command == "plan":
            result = plan(Tokenizer(args.tokenizer_cache))
        elif args.command == "capture":
            # The paid gate must precede tokenizer or database setup.
            from studio_copilot.documents.retrieval.experiment import require_api

            require_api(args.allow_api)
            result = capture_directory(
                args.output_dir, Tokenizer(args.tokenizer_cache), allow_api=args.allow_api
            )
        else:
            result = compare_directory(
                args.capture_dir, args.model_cache, args.output_dir, args.tokenizer_cache
            )
        print(
            json.dumps(
                dict(
                    complete=result.get("complete", True),
                    output_dir=str(getattr(args, "output_dir", "")),
                    adoption=result.get("adoption"),
                    plan=result if args.command == "plan" else None,
                ),
                ensure_ascii=False,
            )
        )
        return 0 if result.get("complete", True) else 1
    except Exception as error:
        code = getattr(error, "code", "invalid_setup")
        message = (
            str(error)
            if isinstance(error, RerankError)
            else "Check local setup and explicit permissions."
        )
        print(f"reranking: {code}: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
