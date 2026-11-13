"""Attach independent case judgments only when every output hash matches."""

import argparse
import json
from pathlib import Path

from .runner import REVIEW_FIELDS, output_hash, summarize


def merge(report, review):
    rows = report["results"]
    judgments = review["results"]
    by_id = {item["id"]: item for item in judgments}
    if len(by_id) != len(judgments) or set(by_id) != {row["id"] for row in rows}:
        raise ValueError("Independent review must cover every result exactly once")
    for row in rows:
        judgment = by_id[row["id"]]
        expected = output_hash(row)
        if row.get("output_sha256") != expected or judgment.get("output_sha256") != expected:
            raise ValueError("Independent judgment refers to a different draft or evidence")
        if not isinstance(judgment.get("issues"), list):
            raise ValueError("Every judgment needs an issue list")
        for field in REVIEW_FIELDS:
            if judgment.get(field) is not None and type(judgment[field]) is not bool:
                raise ValueError("Review metrics must be true, false, or null")
        row["output_sha256"] = expected
        row["review"] = {field: judgment.get(field) for field in REVIEW_FIELDS} | {
            "issues": judgment["issues"],
            "critical": bool(judgment.get("critical", False)),
        }
    report["review_method"] = review.get("method", "independent AI review")
    report["summary"] = summarize(rows)
    report["decision"] = decision(report["summary"], rows, report.get("phase"))
    return report


def decision(summary, rows, phase=None):
    expected = {"smoke": 5, "evaluation": 30}.get(phase)
    if expected is None or summary["total"] != expected:
        return "hold: incomplete case set"
    if summary["reviewed"] != summary["completed"] or summary["failures"]:
        return "hold: incomplete or technically failed evaluation"
    if any(
        any(
            type(row["review"].get(field)) is not bool
            for field in ("supported", "complete", "citation_relevant", "teacher_ready")
        )
        or (
            row.get("expected_status") != "needs_teacher"
            and not any(
                type(row["review"].get(field)) is bool
                for field in ("correct_refusal", "false_refusal")
            )
        )
        for row in rows
    ):
        return "hold: incomplete review judgments"
    if any(row["review"].get("critical") for row in rows):
        return "hold: critical unsupported or omitted condition"
    targets = {
        "supported": (0.95, True),
        "complete": (0.90, True),
        "correct_refusal": (0.95, True),
        "false_refusal": (0.10, False),
    }
    for field, (threshold, minimum) in targets.items():
        metric = summary[field]
        if metric["denominator"] == 0:
            return f"improve: {field} has no evaluable cases"
        rate = metric["count"] / metric["denominator"]
        if (minimum and rate < threshold) or (not minimum and rate > threshold):
            return f"improve: {field} missed the existing quality target"
    return "pilot candidate: targets met on fictional evaluation only"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output already exists")
    result = merge(json.loads(args.report.read_text()), json.loads(args.review.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"decision": result["decision"], "summary": result["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
