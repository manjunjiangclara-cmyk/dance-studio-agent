"""python -m studio_copilot.documents.embedding {plan,run,status,smoke}"""

import argparse
import json
import signal
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.operations import current
from studio_copilot.documents.operations.runtime import add_arguments
from studio_copilot.persistence.database import make_engine

from .pipeline import plan, run
from .provider import Embedder, EmbeddingError, EmbeddingProfile
from .store import Store


def _main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit PostgreSQL embedding preparation.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = commands.add_parser(name)
        command.add_argument("--document-id", type=UUID, required=True)
        command.add_argument("--revision", type=int, required=True)
        command.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    command = commands.add_parser("status")
    command.add_argument("--run-id", type=UUID, required=True)
    commands.add_parser("smoke", help="Paid real API check using two fixed fictional sentences.")
    for subparser in commands.choices.values():
        add_arguments(subparser)
    args = parser.parse_args(argv)
    engine = None
    try:
        profile = EmbeddingProfile.from_env()
        if args.command == "smoke":
            vectors, usage = Embedder(profile).embed(
                [
                    "Fictional studio: trial classes require teacher approval.",
                    "Fictional studio: bring a labelled water bottle.",
                ]
            )
            print(
                json.dumps(
                    dict(
                        vectors=len(vectors),
                        dimensions=profile.dimensions,
                        reported_tokens=usage,
                        model=profile.model,
                        operations=current().budget.snapshot(),
                    )
                )
            )
            return 0
        engine = make_engine()
        if args.command == "status":
            result = Store(engine, profile).status(args.run_id)
        else:
            if args.revision < 1:
                parser.error("--revision must be positive.")
            function = plan if args.command == "plan" else run
            options = (
                {}
                if args.command == "plan"
                else {
                    "progress": lambda value: current().event(
                        "embedding", "context", items=value.get("embedded_passages", 0)
                    )
                }
            )
            result = function(
                engine,
                args.document_id,
                args.revision,
                Tokenizer(args.tokenizer_cache),
                profile,
                **options,
            )
        result.setdefault("operations", current().budget.snapshot())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except EmbeddingError as error:
        print(f"embedding: {error.code}: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "embedding: database operation failed; check migrations and database availability.",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError):
        print(
            "embedding: invalid source/configuration or missing tokenizer; check CLI setup.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


def main(argv=None):
    from studio_copilot.documents.operations.runtime import run_cli

    return run_cli(_main, argv)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
    raise SystemExit(main())
