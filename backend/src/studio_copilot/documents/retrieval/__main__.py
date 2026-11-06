"""Explicit retrieval CLI; stdout is a local inspection artifact, never HTML."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingError
from studio_copilot.persistence.database import make_engine

from .engine import RetrievalError, search
from .evaluation import evaluate


def render(result):
    lines = [f"Retrieval: {result['mode']} | date: {result['as_of']}"]
    lines.extend(f"Warning: {warning}" for warning in result["warnings"])
    for index, hit in enumerate(result["results"], 1):
        lines.extend(
            [
                f"\n{index}. {hit['title']} | revision {hit['revision']}",
                f"Document: {hit['document_id']} | run: {hit['run_id']}",
                f"Section: {' > '.join(hit['heading_path'])}",
                f"Chunk: {hit['chunk_id']} | parent: {hit['parent_id']}",
                f"Effective: {hit['effective_from']} to {hit['effective_to']}",
                f"Source ranges: {json.dumps(hit['source_spans'])}",
                f"Keyword rank: {hit['keyword_rank']} | vector rank: {hit['vector_rank']} "
                f"| RRF: {hit['rrf_score']:.6f}",
                f"Source occurrences: {hit['total_sources']}",
                hit["text"],
            ]
        )
        for ref in hit["other_sources"]:
            lines.append(
                f"Also: {ref['document_id']} revision {ref['revision']} chunk {ref['chunk_id']}"
            )
    if not result["results"]:
        lines.append("No matching passages.")
    lines.append(f"\nEvidence ({result['evidence_tokens']} tokens):")
    for item in result["evidence"]:
        lines.extend([f"\n[{item['kind']}: {item['chunk_id']}]", item["text"]])
    lines.append("\nScores express retrieval rank, not answer confidence.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect explicitly selected document revisions.")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("search")
    command.add_argument("--run-id", action="append", type=UUID, required=True)
    command.add_argument("--query", required=True)
    command.add_argument("--as-of", type=date.fromisoformat, required=True)
    command.add_argument("--mode", choices=["keyword", "vector", "hybrid"], default="hybrid")
    command.add_argument("--allow-api", action="store_true", help="Allow paid question embedding.")
    command.add_argument("--format", choices=["text", "json"], default="text")
    command.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    evaluator = commands.add_parser(
        "evaluate", help="Evaluate source-labelled questions; no reranker."
    )
    evaluator.add_argument("--run-id", type=UUID, required=True)
    evaluator.add_argument("--cases", type=Path, required=True)
    evaluator.add_argument("--mode", choices=["keyword", "vector", "hybrid"], default="keyword")
    evaluator.add_argument("--allow-api", action="store_true")
    evaluator.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    evaluator.set_defaults(format="json")
    args = parser.parse_args(argv)
    engine = None
    try:
        tokenizer = Tokenizer(args.tokenizer_cache)
        engine = make_engine()
        if args.command == "evaluate":
            result = evaluate(
                engine, args.run_id, args.cases, tokenizer, mode=args.mode, allow_api=args.allow_api
            )
        else:
            result = search(
                engine,
                args.run_id,
                args.query,
                args.as_of,
                tokenizer,
                mode=args.mode,
                allow_api=args.allow_api,
            )
        print(json.dumps(result, ensure_ascii=False) if args.format == "json" else render(result))
        return 0
    except (RetrievalError, EmbeddingError) as error:
        print(f"retrieval: {error.code}: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "retrieval: database operation failed; check migrations and availability.",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError):
        print(
            "retrieval: invalid configuration or missing tokenizer; check CLI setup.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
