"""Self-contained, source-validated evidence artifacts and exact citation resolution."""

import copy
import hashlib
import json
from datetime import date
from pathlib import Path

from .contracts import GenerationError

VERSION = "generation-evidence-v1"
BUDGET = 12000


def hash_value(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def source_id(source):
    return f"{source['document_id']}:{source['revision']}"


def make_block(source, chunk_id, kind, prefix, fragments):
    # Recombine contiguous overlap/body ranges exactly as the original chunk renderer.
    merged = []
    for fragment in fragments:
        item = dict(fragment)
        if (
            merged
            and item["role"] != "table_header"
            and merged[-1]["role"] != "table_header"
            and merged[-1]["end"] == item["start"]
        ):
            merged[-1]["end"] = item["end"]
            merged[-1]["role"] = "body"
        else:
            merged.append(item)
    parts = ([prefix] if prefix else []) + [source["text"][f["start"] : f["end"]] for f in merged]
    block = dict(
        source_id=source_id(source),
        chunk_id=chunk_id,
        kind=kind,
        prefix=prefix,
        fragments=merged,
        text="\n\n".join(parts),
    )
    block["id"] = "E" + hash_value(block)[:24]
    return block


def seal_artifact(payload):
    output = copy.deepcopy(payload)
    output.pop("artifact_sha256", None)
    output["question_sha256"] = hash_value(
        [output["case_id"], output["question"], output["as_of"], output["variant"]]
    )
    output["artifact_sha256"] = hash_value(output)
    return output


def validate_artifact(artifact, tokenizer):
    try:
        value = copy.deepcopy(artifact)
        expected = value.pop("artifact_sha256")
        if hash_value(value) != expected or value["version"] != VERSION:
            raise ValueError
        if value["question_sha256"] != hash_value(
            [value["case_id"], value["question"], value["as_of"], value["variant"]]
        ):
            raise ValueError
        if (
            not isinstance(value["question"], str)
            or not value["question"].strip()
            or len(value["question"]) > 4096
            or "\x00" in value["question"]
        ):
            raise ValueError
        as_of = date.fromisoformat(value["as_of"])
        if value["variant"] not in {"actual", "standard"} or len(value["blocks"]) > 20:
            raise ValueError
        sources = {}
        for source in value["sources"]:
            raw = source["text"].encode("utf-8")
            if (
                len(raw) > 10_000_000
                or "\x00" in source["text"]
                or hashlib.sha256(raw).hexdigest() != source["sha256"]
                or type(source["revision"]) is not int
                or source["revision"] < 1
            ):
                raise ValueError
            key = source_id(source)
            if key in sources:
                raise ValueError
            sources[key] = source
        seen = set()
        for block in value["blocks"]:
            source = sources[block["source_id"]]
            if (
                source["effective_from"] and as_of < date.fromisoformat(source["effective_from"])
            ) or (source["effective_to"] and as_of > date.fromisoformat(source["effective_to"])):
                raise ValueError
            if block["id"] in seen or not block["fragments"]:
                raise ValueError
            seen.add(block["id"])
            for fragment in block["fragments"]:
                if (
                    type(fragment["start"]) is not int
                    or type(fragment["end"]) is not int
                    or not 0 <= fragment["start"] < fragment["end"] <= len(source["text"])
                    or fragment["role"] not in {"body", "overlap", "table_header"}
                ):
                    raise ValueError
            rebuilt = make_block(
                source, block["chunk_id"], block["kind"], block["prefix"], block["fragments"]
            )
            if rebuilt != block:
                raise ValueError
        if tokenizer.count("\n\n".join(b["text"] for b in value["blocks"])) > BUDGET:
            raise ValueError
        return artifact
    except (KeyError, TypeError, ValueError, OverflowError):
        raise GenerationError(
            "invalid_evidence", "Evidence identity, source, date, range or budget differs."
        ) from None


def load_artifact(path, tokenizer):
    return validate_artifact(json.loads(Path(path).read_text(encoding="utf-8")), tokenizer)


def resolve_quote(artifact, citation):
    blocks = {b["id"]: b for b in artifact["blocks"]}
    sources = {source_id(s): s for s in artifact["sources"]}
    block = blocks.get(citation.evidence_id)
    if block is None:
        return None
    source = sources[block["source_id"]]
    if not citation.quote.strip():
        return None
    for fragment in block["fragments"]:
        text = source["text"][fragment["start"] : fragment["end"]]
        position = text.find(citation.quote)
        if position >= 0:
            start = fragment["start"] + position
            return dict(
                evidence_id=block["id"],
                quote=citation.quote,
                document_id=source["document_id"],
                revision=source["revision"],
                title=source["title"],
                chunk_id=block["chunk_id"],
                sha256=source["sha256"],
                effective_from=source["effective_from"],
                effective_to=source["effective_to"],
                start=start,
                end=start + len(citation.quote),
                role=fragment["role"],
            )
    return None


def model_payload(artifact, *, prompt_version="v1"):
    if prompt_version not in {"v1", "v2"}:
        raise GenerationError("invalid_prompt_version", "Choose prompt version v1 or v2.")
    sources = {source_id(s): s for s in artifact["sources"]}
    payload = dict(
        question=artifact["question"],
        as_of=artifact["as_of"],
        evidence=[
            dict(
                id=b["id"],
                title=sources[b["source_id"]]["title"],
                revision=sources[b["source_id"]]["revision"],
                effective_from=sources[b["source_id"]]["effective_from"],
                effective_to=sources[b["source_id"]]["effective_to"],
                text=b["text"],
            )
            for b in artifact["blocks"]
        ],
    )
    if prompt_version == "v2":
        for item, block in zip(payload["evidence"], artifact["blocks"], strict=True):
            # Expose only the ranges actually supplied, never missing text or evaluation labels.
            item["source_ranges"] = [dict(fragment) for fragment in block["fragments"]]
            item["omitted_body_ranges"] = [
                dict(start=left["end"], end=right["start"])
                for left, right in zip(block["fragments"], block["fragments"][1:])
                if left["role"] != "table_header"
                and right["role"] != "table_header"
                and left["end"] < right["start"]
            ]
    return payload
