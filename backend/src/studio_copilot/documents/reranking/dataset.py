"""Frozen old tuning/diagnostic cases and previously unused validation families."""

import hashlib
import json
from pathlib import Path

from studio_copilot.documents.retrieval.corpus import applicable, load_corpus, source

from .runtime import RerankError

BACKEND = Path(__file__).resolve().parents[4]
VALIDATION_SHA256 = "b7a547a4e8fc4d860eae288c5ddf8b0741a1a18e6f1a16eb0f3622a9a26e6934"


def load_dataset():
    original = load_corpus(BACKEND / "tests/fixtures/retrieval_corpus_v2/corpus.json")
    path = BACKEND / "tests/fixtures/reranking_validation/validation.json"
    raw = path.read_bytes()
    fresh_hash = hashlib.sha256(raw).hexdigest()
    if fresh_hash != VALIDATION_SHA256:
        raise RerankError("invalid_fixture", "Use the frozen reviewed validation fixture.")
    fresh = json.loads(raw)
    if (
        fresh["version"] != "reranking-validation-v1"
        or len(fresh["documents"]) != 8
        or len(fresh["cases"]) != 50
    ):
        raise RerankError("invalid_fixture", "Unexpected validation dataset shape.")
    documents = original["documents"]
    for document in fresh["documents"]:
        if Path(document["file"]).name != document["file"] or "\\" in document["file"]:
            raise RerankError("invalid_fixture", "Invalid local filename.")
        content = (path.parent / document["file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != document["sha256"]:
            raise RerankError("invalid_fixture", "Source hash mismatch.")
        document["text"] = content.decode("utf-8")
        source(document)
        documents.append(document)
    by_key = {d["key"]: d for d in documents}
    if len(by_key) != 24:
        raise RerankError("invalid_fixture", "Document keys must be unique.")
    for case in original["cases"]:
        if case["split"] == "held_out":
            case["split"] = "diagnostic"
    cases = [*original["cases"], *fresh["cases"]]
    if len({c["id"] for c in cases}) != 150:
        raise RerankError("invalid_fixture", "Case IDs must be unique.")
    if (
        sum(c["answerable"] for c in fresh["cases"]) != 40
        or sum(c["expected_empty"] for c in fresh["cases"]) != 2
    ):
        raise RerankError("invalid_fixture", "Expected forty answerable and ten diagnostic cases.")
    for case in cases:
        if (
            case["split"] not in {"tuning", "diagnostic", "fresh_validation"}
            or bool(case["evidence"]) != case["answerable"]
        ):
            raise RerankError("invalid_fixture", "Invalid case split or labels.")
        if case["expected_empty"] and any(applicable(d, case["as_of"]) for d in documents):
            raise RerankError("invalid_fixture", "Expected-empty date includes applicable sources.")
        for label in case["evidence"]:
            document = by_key[label["document_key"]]
            if (
                not applicable(document, case["as_of"])
                or not 0 <= label["start"] < label["end"] <= len(document["text"])
                or document["text"][label["start"] : label["end"]] != label["text"]
            ):
                raise RerankError("invalid_fixture", "Evidence source/date/range differs.")
    identity = hashlib.sha256((original["source_sha256"] + fresh_hash).encode()).hexdigest()
    return dict(
        version="reranking-dataset-v1",
        source_sha256=identity,
        base_sha256=original["source_sha256"],
        validation_sha256=fresh_hash,
        documents=documents,
        cases=cases,
        notes=fresh.get("notes", []),
    )
