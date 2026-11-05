"""Run with python -m studio_copilot.documents.chunking --help."""

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from studio_copilot.persistence.database import make_engine

from .engine import Chunker
from .export import export
from .sources import load_file, load_revision
from .tokenizer import Tokenizer, default_cache, prepare


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline, revision-pinned document chunk inspection."
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--file", type=Path)
    inputs.add_argument("--document-id", type=UUID)
    inputs.add_argument("--prepare-tokenizer", action="store_true")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--title", help="Optional local-file title; defaults to its filename stem.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    args = parser.parse_args(argv)
    if args.prepare_tokenizer:
        if args.revision is not None or args.title is not None or args.output_dir is not None:
            parser.error("Tokenizer preparation does not accept source or output options.")
    else:
        if args.output_dir is None:
            parser.error("--output-dir is required.")
        if args.document_id is not None and (args.revision is None or args.revision < 1):
            parser.error("--document-id requires an explicit positive --revision.")
        if args.file is not None and args.revision is not None:
            parser.error("--revision applies only to --document-id.")
        if args.document_id is not None and args.title is not None:
            parser.error("A revision's title is immutable; --title applies only to --file.")
    try:
        if args.prepare_tokenizer:
            prepare(args.tokenizer_cache)
            print(f"Verified tokenizer asset saved in {args.tokenizer_cache}")
            return 0
        started = time.perf_counter()
        tokenizer = Tokenizer(args.tokenizer_cache)
        if args.file:
            source = load_file(args.file, args.title)
        else:
            engine = make_engine()
            try:
                source = load_revision(engine, args.document_id, args.revision)
            finally:
                engine.dispose()
        result = export(Chunker(source, tokenizer), args.output_dir, started)
        print(
            json.dumps(
                {
                    "output_dir": str(args.output_dir),
                    "statistics": result["statistics"],
                    "metrics": result["metrics"],
                    "warnings": result["warnings"],
                }
            )
        )
        return 0
    except SQLAlchemyError:
        # Database exception strings can contain connection credentials; do not echo them.
        print("chunking: unable to read the requested database revision.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"chunking: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Let export's finally/exception cleanup run on an ordinary process termination.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
    raise SystemExit(main())
