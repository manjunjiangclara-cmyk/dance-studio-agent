"""Checksummed streaming capture artifacts shared by all offline comparison workers."""

import hashlib
import json
from pathlib import Path

from studio_copilot.documents.retrieval.corpus import applicable

from .dataset import load_dataset
from .runtime import RerankError, digest


def save(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )


def load_capture(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    dataset = load_dataset()
    if (
        not manifest.get("complete")
        or not manifest.get("schema_cleaned")
        or manifest["dataset_sha256"] != dataset["source_sha256"]
        or manifest["records_sha256"] != digest(directory / "candidates.jsonl")
        or manifest["cases"] != len(dataset["cases"])
    ):
        raise RerankError(
            "invalid_capture", "Capture is incomplete, altered, or from another dataset."
        )
    # Fully validate the bounded JSONL before constructing any neural model.
    for _case, _snapshot in records(directory, dataset, fresh=False):
        pass
    return manifest, dataset


def records(directory, dataset, *, fresh=False):
    with (Path(directory) / "candidates.jsonl").open(encoding="utf-8") as stream:
        for case in dataset["cases"]:
            line = stream.readline()
            if not line:
                raise RerankError("invalid_capture", "Candidate capture is truncated.")
            item = json.loads(line)
            if item["case_id"] != case["id"]:
                raise RerankError("invalid_capture", "Captured case order differs.")
            snapshot = item["snapshot"]
            if len(snapshot["candidates"]) > 40 or snapshot.get("degraded"):
                raise RerankError("invalid_capture", "Invalid candidate snapshot.")
            validate_snapshot(case, snapshot, dataset)
            if (case["split"] == "fresh_validation") == fresh:
                yield case, snapshot
        if stream.read().strip():
            raise RerankError("invalid_capture", "Unexpected additional captured cases.")


def validate_snapshot(case, snapshot, dataset):
    candidates = snapshot["candidates"]
    if len({c["text_sha256"] for c in candidates}) != len(candidates):
        raise RerankError("invalid_capture", "Duplicate candidate identities.")
    documents = {d["key"]: d for d in dataset["documents"]}
    required_parents = set()
    for candidate in candidates:
        if (
            hashlib.sha256(candidate["text"].encode("utf-8")).hexdigest()
            != candidate["text_sha256"]
        ):
            raise RerankError("invalid_capture", "Candidate text hash mismatch.")
        if len(candidate.get("other_sources", [])) > 3:
            raise RerankError("invalid_capture", "Visible reference cap exceeded.")
        for reference in (candidate, *candidate.get("other_sources", [])):
            document = documents[reference["document_key"]]
            if (
                not applicable(document, case["as_of"])
                or reference["revision"] != 1
                or any(
                    reference[field] != document[field]
                    for field in ("effective_from", "effective_to")
                )
            ):
                raise RerankError("invalid_capture", "Candidate source/date is ineligible.")
            for span in reference["source_spans"]:
                if not 0 <= span["start"] < span["end"] <= len(document["text"]):
                    raise RerankError("invalid_capture", "Source range is invalid.")
        if candidate["parent_id"]:
            key = f"{candidate['run_id']}:{candidate['parent_id']}"
            required_parents.add(key)
            parent = snapshot["parents"][key]
            if parent["kind"] != "parent" or parent["chunk_id"] != candidate["parent_id"]:
                raise RerankError("invalid_capture", "Parent identity differs.")
    if set(snapshot["parents"]) != required_parents:
        raise RerankError("invalid_capture", "Captured parent set differs from candidate parents.")
