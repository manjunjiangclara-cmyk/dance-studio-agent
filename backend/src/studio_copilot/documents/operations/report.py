"""Aggregate only strict operational events; never echo untrusted event fields."""

import json
import math
import os
import shutil
import tempfile
from pathlib import Path

from .budget import OperationsError
from .telemetry import COUNTS, safe_event


def summarize(events_file, output_dir):
    output = Path(output_dir)
    if output.exists():
        raise OperationsError("output_exists", "Choose a new summary directory.")
    groups = {}
    with Path(events_file).open(encoding="utf-8") as stream:
        while line := stream.readline(65537):
            if len(line) > 65536:
                raise OperationsError("invalid_events", "Operational event exceeds size limit.")
            try:
                raw = json.loads(line)
                event = safe_event(raw) if isinstance(raw, dict) else None
            except (ValueError, TypeError):
                event = None
            if event is None or raw.get("version") != "document-operations-v1":
                raise OperationsError("invalid_events", "Invalid operational event.")
            key = event["operation"] + "/" + event["stage"]
            group = groups.setdefault(
                key,
                dict(events=0, failures=0, degraded=0, durations=[], counts={k: 0 for k in COUNTS}),
            )
            group["events"] += 1
            group["failures"] += event["status"] == "failure"
            group["degraded"] += event["status"] == "degraded"
            if "seconds" in event:
                group["durations"].append(event["seconds"])
            for field in COUNTS:
                group["counts"][field] += event.get(field, 0)
    for group in groups.values():
        durations = sorted(group.pop("durations"))
        group["duration_samples"] = len(durations)
        group["small_sample"] = len(durations) < 20
        group["p50_seconds"] = durations[math.ceil(len(durations) * 0.5) - 1] if durations else None
        group["p95_seconds"] = (
            durations[math.ceil(len(durations) * 0.95) - 1] if durations else None
        )
        group["failure_rate"] = group["failures"] / group["events"]
        hits, misses = group["counts"]["cache_hits"], group["counts"]["cache_misses"]
        group["cache_hit_rate"] = hits / (hits + misses) if hits + misses else None
    result = dict(
        version="document-operations-summary-v1",
        groups=dict(sorted(groups.items())),
        note="Operational samples only; no semantic-quality or latency SLA claim.",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".operations-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        (temporary / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        lines = [
            "# Document operations",
            "",
            result["note"],
            "",
            "| Stage | Events | Failures | p50 s | p95 s | Small sample |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for key, group in result["groups"].items():
            lines.append(
                f"| {key} | {group['events']} | {group['failures']} | "
                f"{group['p50_seconds']} | {group['p95_seconds']} | "
                f"{group['small_sample']} |"
            )
        (temporary / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Refuse even an empty pre-existing output directory.
        output.mkdir(mode=0o700)
        for path in temporary.iterdir():
            path.rename(output / path.name)
    finally:
        shutil.rmtree(temporary)
    return result
