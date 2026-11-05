"""Incremental exports; a manifest is published only after all files succeed."""

import hashlib
import json
import os
import resource
import shutil
import sys
import tempfile
import time
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

from .engine import Chunker


def write_json(stream, value):
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def file_hash(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65_536):
            result.update(block)
    return result.hexdigest()


def export(chunker: Chunker, target: Path, started: float | None = None):
    started = started if started is not None else time.perf_counter()
    target = target.absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation rejects existing directories (even empty), files and symlinks,
    # and prevents two cooperating exporters from racing to replace the same path.
    target.mkdir()
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        stats = {
            kind: {"count": 0, "min_tokens": None, "max_tokens": 0}
            for kind in ("parent", "passage")
        }
        coverage = {"parent": 0, "passage": 0}
        with ExitStack() as stack:
            parents = stack.enter_context((staging / "parents.jsonl").open("w", encoding="utf-8"))
            passages = stack.enter_context((staging / "passages.jsonl").open("w", encoding="utf-8"))
            report = stack.enter_context((staging / "report.txt").open("w", encoding="utf-8"))
            report.write(
                "Offline chunk inspection — not published or available to the agent.\n"
                f"Source: {chunker.source.title}\nRevision: {chunker.source.revision}\n"
                f"SHA-256: {chunker.source.sha256}\n\nFirst 12 search passages:\n"
            )
            for record in chunker.records():
                kind = record["kind"]
                primary = next(span for span in record["source_spans"] if span["role"] == "body")
                if primary["start"] != coverage[kind] or primary["end"] <= primary["start"]:
                    raise ValueError("Chunk coverage is incomplete or out of order.")
                coverage[kind] = primary["end"]
                count = record["token_count"]
                stat = stats[kind]
                stat["count"] += 1
                stat["min_tokens"] = min(stat["min_tokens"] or count, count)
                stat["max_tokens"] = max(stat["max_tokens"], count)
                write_json(parents if kind == "parent" else passages, record)
                if kind == "passage" and stat["count"] <= 12:
                    report.write(
                        f"\n--- {record['id']} ---\n"
                        f"parent={record['parent_id']} tokens={count}\n"
                        f"spans={record['source_spans']}\n"
                        f"{record['text']}\n"
                    )
            if any(end != len(chunker.source.text) for end in coverage.values()):
                raise ValueError("Chunk coverage does not reach the end of the source.")
            report.write(f"\nStatistics: {stats}\nWarnings: {sorted(chunker.warnings)}\n")

        # Binary write preserves BOM/CRLF exactly, including on platforms with newline translation.
        (staging / "source.txt").write_bytes(chunker.source.text.encode("utf-8"))
        for filename, records in (
            ("headings.jsonl", chunker.headings),
            ("sections.jsonl", chunker.section_records()),
        ):
            with (staging / filename).open("w", encoding="utf-8") as stream:
                for record in records:
                    write_json(stream, record)
        files = {
            path.name: {"sha256": file_hash(path), "bytes": path.stat().st_size}
            for path in sorted(staging.iterdir())
        }
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        manifest = {
            "format_version": 1,
            "complete": True,
            "source_id": chunker.source_id,
            "source": chunker.source.metadata(),
            "config": asdict(chunker.config),
            "config_hash": chunker.config_hash,
            "statistics": stats,
            "warnings": sorted(chunker.warnings),
            "coverage_characters": coverage,
            "source_characters": len(chunker.source.text),
            "files": files,
            "metrics": {
                "elapsed_seconds": round(time.perf_counter() - started, 6),
                "process_peak_rss_bytes": peak if sys.platform == "darwin" else peak * 1024,
            },
        }
        with (staging / "manifest.json").open("w", encoding="utf-8") as stream:
            write_json(stream, manifest)
        os.replace(staging, target)
        staging = None
        return manifest
    except BaseException:
        # Never erase preexisting output or another process's files.
        if staging is not None:
            shutil.rmtree(staging)
        try:
            target.rmdir()
        except OSError:
            pass
        raise
