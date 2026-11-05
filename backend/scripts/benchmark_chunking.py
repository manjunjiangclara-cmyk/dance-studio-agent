"""Exercise exact-10-MB sources in fresh offline CLI processes, no model calls.

Run from backend: python scripts/benchmark_chunking.py --output-dir /tmp/chunk-benchmark
Prepare the tokenizer first. Outputs are intentionally outside the repository.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache

SIZE = 10_000_000
TAIL = b"\nEND_OF_SOURCE_10MB\n"
CASES = {
    "single-line": (b"", b"longunbrokenword", b""),
    "short-blocks": (b"# Rules\n\n", b"A\n\n", b""),
    "many-headings": (b"", b"# Same\nRule.\n\n", b""),
    "unicode": (b"# Unicode\n\n", "舞蹈课 👩🏽‍🦰 café e\u0301。\n\n".encode(), b""),
    "table": (
        b"# Fees\n\n| Term | Rule |\n| --- | --- |\n",
        b"| One | Approval is required. |\n",
        b"",
    ),
    "code": (b"# Example\n\n```text\n", b"# literal heading <script>x</script>\n", b"\n```\n"),
    "giant-row": (
        b"# Fees\n\n| Term | Rule |\n| --- | --- |\n| One | ",
        b"Conditions and exceptions. ",
        b" |\n",
    ),
}


def write_case(path, prefix, unit, suffix):
    available = SIZE - len(prefix) - len(suffix) - len(TAIL)
    count, remainder = divmod(available, len(unit))
    # Padding avoids cutting a Unicode codepoint or changing the exact byte target.
    with path.open("wb") as stream:
        stream.write(prefix)
        for _ in range(count // 1000):
            stream.write(unit * 1000)
        stream.write(unit * (count % 1000))
        stream.write(b" " * remainder + suffix + TAIL)
    assert path.stat().st_size == SIZE


def verify(output, tokenizer):
    manifest = json.loads((output / "manifest.json").read_text())
    original = (output / "source.txt").read_bytes()
    assert len(original) == SIZE and original.endswith(TAIL)
    assert hashlib.sha256(original).hexdigest() == manifest["source"]["sha256"]
    source_text = original.decode()
    for kind, limit in (("parent", 2400), ("passage", 900)):
        cursor, count = 0, 0
        with (output / f"{kind}s.jsonl").open() as stream:
            for line in stream:
                record = json.loads(line)
                body = next(span for span in record["source_spans"] if span["role"] == "body")
                assert body["start"] == cursor < body["end"]
                cursor, count = body["end"], count + 1
                assert record["token_count"] == tokenizer.count(record["text"]) <= limit
        assert cursor == len(source_text)
        assert count == manifest["statistics"][kind]["count"]
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path, default=default_cache())
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    args = parser.parse_args()
    tokenizer = Tokenizer(args.tokenizer_cache)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    results = {}
    for case in args.cases:
        source = args.output_dir / f"{case}.md"
        output = args.output_dir / case
        write_case(source, *CASES[case])
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "studio_copilot.documents.chunking",
                "--file",
                str(source),
                "--output-dir",
                str(output),
                "--tokenizer-cache",
                str(args.tokenizer_cache),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode:
            raise RuntimeError(f"{case}: {completed.stderr}")
        manifest = verify(output, tokenizer)
        results[case] = {
            "metrics": manifest["metrics"],
            "statistics": manifest["statistics"],
            "warnings": manifest["warnings"],
            "source_bytes": SIZE,
        }
        print(json.dumps({case: results[case]}), flush=True)
        (args.output_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
