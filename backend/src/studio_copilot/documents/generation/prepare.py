"""Build actual/standard evidence locally from frozen capture, L6 ranks and raw source snapshots."""

import copy
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from studio_copilot.documents.reranking.artifacts import load_capture, save
from studio_copilot.documents.retrieval.engine import pack_from_records

from .contracts import GenerationError
from .evidence import VERSION, hash_value, make_block, seal_artifact, source_id, validate_artifact

BACKEND = Path(__file__).resolve().parents[4]
CASES_SHA256 = "5cca335eda3f1dcd8e89b8400b93361efb356de9211f2984937e2b60308ffdf5"


def load_cases(path=None):
    path = Path(path) if path else BACKEND / "tests/fixtures/generation_cases.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CASES_SHA256:
        raise GenerationError("invalid_cases", "Use the frozen reviewed generation cases.")
    return json.loads(raw)


def snapshot_source(document, identity, revision=1):
    return dict(
        document_id=str(identity),
        revision=revision,
        title=document["title"],
        filename=document.get("file", "fixture.txt"),
        text=document["text"],
        sha256=document["sha256"],
        effective_from=document["effective_from"],
        effective_to=document["effective_to"],
        document_key=document["key"],
    )


def trim_blocks(blocks, sources, facts):
    by_id = {source_id(s): s for s in sources}
    output = []
    for block in blocks:
        source = by_id[block["source_id"]]
        fragments = copy.deepcopy(block["fragments"])
        for fact in facts:
            if fact["document_key"] != source["document_key"]:
                continue
            remaining = []
            for fragment in fragments:
                a, b = fragment["start"], fragment["end"]
                left, right = max(a, fact["start"]), min(b, fact["end"])
                if left >= right:
                    remaining.append(fragment)
                else:
                    if a < left:
                        remaining.append(dict(fragment, end=left))
                    if right < b:
                        remaining.append(dict(fragment, start=right))
            fragments = remaining
        if fragments:
            output.append(
                make_block(source, block["chunk_id"], "controlled", block["prefix"], fragments)
            )
    return output


def prepare_evidence(capture_dir, rankings_file, output_dir, tokenizer, *, cases_path=None):
    labels = load_cases(cases_path)
    manifest, dataset = load_capture(capture_dir)
    ranking = json.loads(Path(rankings_file).read_text())
    selected = ranking["selection"]["model_id"]
    if (
        not selected.endswith("MiniLM-L6-v2")
        or not ranking["complete"]
        or ranking["capture"]["records_sha256"] != manifest["records_sha256"]
        or ranking["capture"]["dataset_sha256"] != manifest["dataset_sha256"]
    ):
        raise GenerationError(
            "invalid_ranking", "Use the completed, matching selected-L6 comparison."
        )
    documents = {d["key"]: d for d in dataset["documents"]}
    original_cases = {c["id"]: c for c in dataset["cases"]}
    if [m["sha256"] for m in labels["source_manifests"]] != [
        dataset["base_sha256"],
        dataset["validation_sha256"],
    ]:
        raise GenerationError("invalid_cases", "Generation labels refer to another source dataset.")
    rows = {}
    with (Path(capture_dir) / "candidates.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows[row["case_id"]] = row["snapshot"]
    ranks = {c["id"]: c for c in ranking["models"][selected]["cases"]}
    ranks.update({c["id"]: c for c in ranking["fresh_validation"]["cases"]})
    identity_by_key = {s["key"]: s["document_id"] for s in manifest["source_identities"]}
    sources_by_key = {k: snapshot_source(d, identity_by_key[k]) for k, d in documents.items()}
    # Attack source is an explicit controlled input, never a hidden mutation of a revision.
    attack = labels["attack_document"]
    attack_raw = (Path(cases_path).parent if cases_path else BACKEND / "tests/fixtures") / attack[
        "file"
    ]
    raw = attack_raw.read_bytes()
    if hashlib.sha256(raw).hexdigest() != attack["sha256"]:
        raise GenerationError("invalid_cases", "Attack fixture hash differs.")
    attack_source = snapshot_source(
        dict(attack, text=raw.decode("utf-8"), key="generation_attack"),
        uuid5(NAMESPACE_URL, attack["sha256"]),
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    index = []
    try:
        for case in labels["cases"]:
            original = original_cases[case["source_case_id"]]
            if case["as_of"] != original["as_of"] or (
                case["context_variant"] == "original" and case["question"] != original["query"]
            ):
                raise GenerationError("invalid_cases", "Question/source lineage differs.")
            snapshot = rows[case["source_case_id"]]
            hashes = [r["text_sha256"] for r in ranks[case["source_case_id"]]["rankings"][:6]]
            candidates = {c["text_sha256"]: c for c in snapshot["candidates"]}
            if any(h not in candidates for h in hashes):
                raise GenerationError(
                    "invalid_ranking", "Ranked text is absent from candidate capture."
                )
            selected_candidates = [candidates[h] for h in hashes]
            packed, _, _ = pack_from_records(selected_candidates, snapshot["parents"], tokenizer)
            by_run = {
                c["run_id"]: sources_by_key[c["document_key"]] for c in snapshot["candidates"]
            }
            original_blocks = []
            sources = {}
            for item in packed:
                source = by_run[item["run_id"]]
                sources[source_id(source)] = source
                block = make_block(
                    source, item["chunk_id"], item["kind"], item["prefix"], item["source_spans"]
                )
                if block["text"] != item["text"]:
                    raise GenerationError(
                        "invalid_evidence", "Captured text does not match raw source ranges."
                    )
                original_blocks.append(block)
            for variant in ("actual", "standard"):
                blocks = copy.deepcopy(original_blocks)
                variant_sources = copy.deepcopy(sources)
                if variant == "actual" and case["drop_fact_ids"]:
                    dropped = [
                        f for f in case["required_facts"] if f["id"] in case["drop_fact_ids"]
                    ]
                    blocks = trim_blocks(blocks, list(variant_sources.values()), dropped)
                if variant == "standard":
                    for fact in case["required_facts"]:
                        source = sources_by_key[fact["document_key"]]
                        if source["text"][fact["start"] : fact["end"]] != fact["text"]:
                            raise GenerationError(
                                "invalid_cases", "Fact labels differ from original Unicode source."
                            )
                        if any(
                            b["source_id"] == source_id(source)
                            and any(
                                f["start"] <= fact["start"] and f["end"] >= fact["end"]
                                for f in b["fragments"]
                            )
                            for b in blocks
                        ):
                            continue
                        separator = source["text"].rfind("\n\n", 0, fact["start"])
                        left = separator + 2 if separator >= 0 else 0
                        right = source["text"].find("\n\n", fact["end"])
                        if right < 0:
                            right = len(source["text"])
                        variant_sources[source_id(source)] = source
                        blocks.append(
                            make_block(
                                source,
                                "oracle:" + fact["id"],
                                "oracle",
                                "",
                                [dict(start=left, end=right, role="body")],
                            )
                        )
                if case["inject"]:
                    variant_sources[source_id(attack_source)] = attack_source
                    blocks.append(
                        make_block(
                            attack_source,
                            "controlled-attack",
                            "controlled",
                            "",
                            [dict(start=0, end=len(attack_source["text"]), role="body")],
                        )
                    )
                artifact = seal_artifact(
                    dict(
                        version=VERSION,
                        case_id=case["id"],
                        question=case["question"],
                        as_of=case["as_of"],
                        variant=variant,
                        sources=list(variant_sources.values()),
                        blocks=blocks,
                        provenance=dict(
                            source_case_id=case["source_case_id"],
                            retrieval_question=original["query"],
                            context_variant=case["context_variant"],
                            controlled_drop=case["drop_fact_ids"] if variant == "actual" else [],
                            injection=case["inject"],
                            capture_sha256=manifest["records_sha256"],
                            rankings_sha256=hash_value(ranking),
                        ),
                    )
                )
                validate_artifact(artifact, tokenizer)
                name = f"{case['id']}-{variant}.json"
                save(output / name, artifact)
                index.append(
                    dict(
                        case_id=case["id"],
                        variant=variant,
                        file=name,
                        artifact_sha256=artifact["artifact_sha256"],
                    )
                )
        result = dict(
            version="generation-evidence-set-v1",
            complete=True,
            cases_sha256=CASES_SHA256,
            source_dataset_sha256=dataset["source_sha256"],
            capture_sha256=manifest["records_sha256"],
            artifacts=index,
            index_sha256=hash_value(index),
        )
        save(output / "manifest.json", result)
        return result
    except Exception:
        save(output / "manifest.json", dict(complete=False, artifacts=index))
        raise
