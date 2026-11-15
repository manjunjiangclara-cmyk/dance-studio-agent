"""Frozen labels, shared paid-call budget, and reproducible report summaries."""

import hashlib
import json
from datetime import date
from pathlib import Path

from studio_copilot.documents.reranking.dataset import load_dataset as load_sources


class BudgetExceeded(RuntimeError):
    """The explicit evaluation cap was reached before a provider call."""


class Ticket:
    def __init__(self, estimated_input, reserved_output):
        self.estimated_input = estimated_input
        self.reserved_output = reserved_output
        self.settled = False


class RunBudget:
    def __init__(self, max_requests, max_input_tokens, max_output_tokens):
        if min(max_requests, max_input_tokens, max_output_tokens) < 1:
            raise ValueError("Evaluation caps must be positive")
        self.limits = (max_requests, max_input_tokens, max_output_tokens)
        self.requests = self.input_tokens = self.output_tokens = 0
        self.reserved_input_tokens = self.reserved_output_tokens = 0
        self.exhausted = False
        self.unknown_usage = 0

    def reserve(self, estimated_input, reserved_output):
        if min(estimated_input, reserved_output) < 0:
            raise ValueError("Negative token reservation")
        if (
            self.requests + 1 > self.limits[0]
            or self.input_tokens + estimated_input > self.limits[1]
            or self.output_tokens + reserved_output > self.limits[2]
        ):
            self.exhausted = True
            raise BudgetExceeded("Evaluation paid-call budget exhausted")
        self.requests += 1
        self.input_tokens += estimated_input
        self.output_tokens += reserved_output
        self.reserved_input_tokens += estimated_input
        self.reserved_output_tokens += reserved_output
        return Ticket(estimated_input, reserved_output)

    def record(self, ticket, actual_input, actual_output):
        if ticket.settled:
            raise ValueError("Evaluation reservation already settled")
        ticket.settled = True
        if actual_input is None or actual_output is None:
            self.unknown_usage += 1
            return
        if min(actual_input, actual_output) < 0:
            raise ValueError("Negative reported token usage")
        self.input_tokens += actual_input - ticket.estimated_input
        self.output_tokens += actual_output - ticket.reserved_output

    def snapshot(self):
        return dict(
            requests=self.requests,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            unknown_usage=self.unknown_usage,
            unknown_usage_calls=self.unknown_usage,
            reserved_input_tokens=self.reserved_input_tokens,
            reserved_output_tokens=self.reserved_output_tokens,
            exhausted=self.exhausted,
            limits=dict(zip(("requests", "input_tokens", "output_tokens"), self.limits)),
        )


def fingerprint(dataset_path, corpus_path):
    """Hash the manifest and every source byte, independent of execution time."""
    digest = hashlib.sha256(Path(dataset_path).read_bytes())
    corpus_bytes = Path(corpus_path).read_bytes()
    digest.update(corpus_bytes)
    corpus = json.loads(corpus_bytes)
    root = Path(corpus_path).parent
    for source in sorted(corpus["documents"], key=lambda item: item["key"]):
        digest.update(source["key"].encode())
        digest.update((root / source["file"]).read_bytes())
    return digest.hexdigest()


def output_hash(row):
    content = {key: row[key] for key in ("draft", "document_evidence")}
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def load_dataset(path, source_manifest=None):
    data = json.loads(Path(path).read_text())
    if data.get("version") not in {"integrated-rag-v1", "integrated-rag-v2"}:
        raise ValueError("Unsupported integrated evaluation version")
    if len(data.get("smoke", [])) != 5 or len(data.get("evaluation", [])) != 30:
        raise ValueError("Expected five smoke and thirty evaluation cases")
    if data["version"] == "integrated-rag-v2" and source_manifest is None:
        raise ValueError("Fresh validation requires its frozen source manifest")
    if source_manifest is None:
        sources = load_sources()
    else:
        manifest_path = Path(source_manifest)
        sources = json.loads(manifest_path.read_text())
        if sources.get("version") != "integrated-rag-validation-sources-v2":
            raise ValueError("Unexpected validation source version")
        for source in sources["documents"]:
            if Path(source["file"]).name != source["file"] or "\\" in source["file"]:
                raise ValueError("Invalid validation source filename")
            raw = (manifest_path.parent / source["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError("Frozen source content changed")
            source["text"] = raw.decode("utf-8")
        if (
            data.get("source_manifest_sha256")
            != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        ):
            raise ValueError("Frozen source manifest changed")
    by_key = {source["key"]: source for source in sources["documents"]}
    if len(by_key) != len(sources["documents"]):
        raise ValueError("Validation source keys must be unique")
    seen = set()
    for case in [*data["smoke"], *data["evaluation"]]:
        if not case["id"] or case["id"] in seen or not case["question"].strip():
            raise ValueError("Case IDs and questions must be nonempty and unique")
        seen.add(case["id"])
        as_of = date.fromisoformat(case["as_of"])
        for fact in case["required_facts"]:
            source = by_key[fact["document_key"]]
            if source["text"][fact["start"] : fact["end"]] != fact["text"]:
                raise ValueError("Frozen fact differs from source bytes")
            start = source.get("effective_from")
            end = source.get("effective_to")
            if (start and as_of < date.fromisoformat(start)) or (
                end and as_of > date.fromisoformat(end)
            ):
                raise ValueError("Frozen fact is outside its source dates")
    return data


REVIEW_FIELDS = (
    "supported",
    "complete",
    "correct_refusal",
    "false_refusal",
    "citation_relevant",
    "teacher_ready",
)


def summarize(results):
    reviewed = [
        row["review"]
        for row in results
        if row.get("status") == "completed" and isinstance(row.get("review"), dict)
    ]
    summary = dict(
        total=len(results),
        completed=sum(row.get("status") == "completed" for row in results),
        failures=sum(row.get("status") != "completed" for row in results),
        reviewed=len(reviewed),
        failure_stages={
            stage: sum(stage in row.get("failure_stages", []) for row in results)
            for stage in ("retrieval", "answer", "composition", "agent")
        },
    )
    for field in REVIEW_FIELDS:
        values = [review[field] for review in reviewed if type(review.get(field)) is bool]
        summary[field] = dict(count=sum(values), denominator=len(values))
    return summary
