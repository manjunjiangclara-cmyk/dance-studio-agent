"""Independent capture-schema tests: no network, models, database or tokenizer downloads."""

import copy
import hashlib
import json
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import pytest

from studio_copilot.documents.generation import prepare
from studio_copilot.documents.generation.contracts import GenerationError
from studio_copilot.documents.generation.evidence import load_artifact, source_id
from studio_copilot.documents.reranking import artifacts
from studio_copilot.documents.reranking.dataset import load_dataset
from studio_copilot.documents.reranking.runtime import RerankError


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    labels = prepare.load_cases()
    chosen = {"gen-tuning-01", "gen-tuning-25", "gen-tuning-32", "gen-tuning-40"}
    labels["cases"] = [c for c in labels["cases"] if c["id"] in chosen]
    dataset = load_dataset()
    seeds = {c["source_case_id"] for c in labels["cases"]}
    dataset["cases"] = [c for c in dataset["cases"] if c["id"] in seeds]
    docs = {d["key"]: d for d in dataset["documents"]}
    identities = {k: str(uuid5(NAMESPACE_URL, "generation-document:" + k)) for k in docs}
    folder = tmp_path / "capture"
    folder.mkdir()
    rows, rankings = [], []
    for case in dataset["cases"]:
        facts = (
            case["evidence"]
            or next(c for c in dataset["cases"] if c["evidence"] and c["as_of"] == case["as_of"])[
                "evidence"
            ]
        )
        grouped = {}
        for fact in facts:
            grouped.setdefault(fact["document_key"], []).append(fact)
        candidates, parents = [], {}
        for key, labels_in_doc in grouped.items():
            doc = docs[key]
            run_id = str(uuid5(NAMESPACE_URL, "generation-run:" + key))
            parent_id = "parent:" + key
            left = min(f["start"] for f in labels_in_doc)
            right = max(f["end"] for f in labels_in_doc)
            parents[f"{run_id}:{parent_id}"] = dict(
                kind="parent",
                chunk_id=parent_id,
                text=doc["text"][left:right],
                provenance=dict(source_spans=[dict(start=left, end=right, role="body")]),
            )
            for index, fact in enumerate(labels_in_doc):
                candidates.append(
                    dict(
                        text=fact["text"],
                        text_sha256=hashlib.sha256(fact["text"].encode()).hexdigest(),
                        document_key=key,
                        document_id=identities[key],
                        revision=1,
                        effective_from=doc["effective_from"],
                        effective_to=doc["effective_to"],
                        run_id=run_id,
                        chunk_id=f"passage:{key}:{index}",
                        parent_id=parent_id,
                        prefix="",
                        source_spans=[dict(start=fact["start"], end=fact["end"], role="body")],
                        other_sources=[],
                    )
                )
        rows.append(
            dict(
                case_id=case["id"],
                snapshot=dict(candidates=candidates, parents=parents, degraded=False),
            )
        )
        rankings.append(
            dict(id=case["id"], rankings=[dict(text_sha256=c["text_sha256"]) for c in candidates])
        )
    records = folder / "candidates.jsonl"
    records.write_text("".join(json.dumps(r) + "\n" for r in rows))
    manifest = dict(
        complete=True,
        schema_cleaned=True,
        cases=len(rows),
        dataset_sha256=dataset["source_sha256"],
        records_sha256=hashlib.sha256(records.read_bytes()).hexdigest(),
        source_identities=[dict(key=k, document_id=v) for k, v in identities.items()],
    )
    (folder / "manifest.json").write_text(json.dumps(manifest))
    model = "cross-encoder/ms-marco-MiniLM-L6-v2"
    ranking = dict(
        complete=True,
        selection=dict(model_id=model),
        capture={k: manifest[k] for k in ("records_sha256", "dataset_sha256")},
        models={model: dict(cases=rankings)},
        fresh_validation=dict(cases=[]),
    )
    rank_file = tmp_path / "ranks.json"
    rank_file.write_text(json.dumps(ranking))
    monkeypatch.setattr(artifacts, "load_dataset", lambda: copy.deepcopy(dataset))
    monkeypatch.setattr(prepare, "load_cases", lambda *args: copy.deepcopy(labels))
    return SimpleNamespace(
        folder=folder,
        rank_file=rank_file,
        ranking=ranking,
        labels=labels,
        tokenizer=SimpleNamespace(count=lambda value: len(value) // 4),
        output=tmp_path / "evidence",
    )


def run(data):
    return prepare.prepare_evidence(data.folder, data.rank_file, data.output, data.tokenizer)


def artifact(data, case, variant):
    return load_artifact(data.output / f"{case}-{variant}.json", data.tokenizer)


def test_original_lineage_parent_packing_and_oracle_preservation(inputs):
    result = run(inputs)
    assert result["complete"] and len(result["artifacts"]) == 8
    actual = artifact(inputs, "gen-tuning-01", "actual")
    standard = artifact(inputs, "gen-tuning-01", "standard")
    assert actual["blocks"] == standard["blocks"]
    assert actual["blocks"][0]["kind"] == "parent"
    assert actual["question"] == actual["provenance"]["retrieval_question"]
    assert actual["provenance"]["context_variant"] == "original"


def test_controlled_drop_removes_parent_evidence_and_oracle_restores(inputs):
    run(inputs)
    case = next(c for c in inputs.labels["cases"] if c["id"] == "gen-tuning-25")
    dropped = next(f for f in case["required_facts"] if f["id"] in case["drop_fact_ids"])
    actual = artifact(inputs, case["id"], "actual")
    standard = artifact(inputs, case["id"], "standard")
    assert all(dropped["text"] not in b["text"] for b in actual["blocks"])
    assert any(case["required_facts"][0]["text"] in b["text"] for b in actual["blocks"])
    assert all(
        any(f["text"] in b["text"] for b in standard["blocks"]) for f in case["required_facts"]
    )
    assert actual["provenance"]["controlled_drop"] == case["drop_fact_ids"]
    assert standard["provenance"]["controlled_drop"] == []


def test_no_answer_oracle_keeps_retrieved_distractors(inputs):
    run(inputs)
    actual = artifact(inputs, "gen-tuning-32", "actual")
    standard = artifact(inputs, "gen-tuning-32", "standard")
    assert actual["blocks"] and actual["blocks"] == standard["blocks"]


def test_injection_has_explicit_valid_source_in_both_variants(inputs):
    run(inputs)
    for variant in ("actual", "standard"):
        item = artifact(inputs, "gen-tuning-40", variant)
        source = next(s for s in item["sources"] if s["document_key"] == "generation_attack")
        block = next(b for b in item["blocks"] if b["source_id"] == source_id(source))
        assert block["kind"] == "controlled" and block["text"] == source["text"]
        assert "CANARY-POLICY-OVERRIDE" in block["text"] and item["provenance"]["injection"]


@pytest.mark.parametrize("damage", ["incomplete", "model", "capture", "dataset"])
def test_ranking_identity_mismatch_rejected_before_export(inputs, damage):
    if damage == "incomplete":
        inputs.ranking["complete"] = False
    elif damage == "model":
        inputs.ranking["selection"]["model_id"] = "cross-encoder/ms-marco-MiniLM-L12-v2"
    else:
        field = "records_sha256" if damage == "capture" else "dataset_sha256"
        inputs.ranking["capture"][field] = "wrong"
    inputs.rank_file.write_text(json.dumps(inputs.ranking))
    with pytest.raises(GenerationError) as error:
        run(inputs)
    assert error.value.code == "invalid_ranking" and not inputs.output.exists()


def test_tampered_capture_rejected_by_real_capture_loader(inputs):
    with (inputs.folder / "candidates.jsonl").open("a") as stream:
        stream.write("tampered")
    with pytest.raises(RerankError) as error:
        run(inputs)
    assert error.value.code == "invalid_capture" and not inputs.output.exists()


def test_unknown_ranked_candidate_rejected_with_incomplete_manifest(inputs):
    model = inputs.ranking["selection"]["model_id"]
    inputs.ranking["models"][model]["cases"][0]["rankings"][0]["text_sha256"] = "absent"
    inputs.rank_file.write_text(json.dumps(inputs.ranking))
    with pytest.raises(GenerationError) as error:
        run(inputs)
    assert error.value.code == "invalid_ranking"
    assert not json.loads((inputs.output / "manifest.json").read_text())["complete"]


def test_export_refuses_overwrite_without_damaging_existing_manifest(inputs):
    run(inputs)
    before = (inputs.output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        run(inputs)
    assert (inputs.output / "manifest.json").read_bytes() == before


def test_oracle_supplements_a_natural_miss_without_removing_original_context(inputs):
    case = next(c for c in inputs.labels["cases"] if c["id"] == "gen-tuning-25")
    record_path = inputs.folder / "candidates.jsonl"
    rows = [json.loads(line) for line in record_path.read_text().splitlines()]
    row = next(r for r in rows if r["case_id"] == case["source_case_id"])
    first = row["snapshot"]["candidates"][0]
    row["snapshot"]["candidates"] = [first]
    parent = row["snapshot"]["parents"][f"{first['run_id']}:{first['parent_id']}"]
    parent["text"] = first["text"]
    parent["provenance"]["source_spans"] = copy.deepcopy(first["source_spans"])
    record_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
    manifest_path = inputs.folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["records_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest))
    inputs.ranking["capture"]["records_sha256"] = digest
    model = inputs.ranking["selection"]["model_id"]
    rank = next(
        r for r in inputs.ranking["models"][model]["cases"] if r["id"] == case["source_case_id"]
    )
    rank["rankings"] = [dict(text_sha256=first["text_sha256"])]
    inputs.rank_file.write_text(json.dumps(inputs.ranking))
    run(inputs)
    standard = artifact(inputs, case["id"], "standard")
    assert any(b["text"] == first["text"] for b in standard["blocks"])
    assert any(b["kind"] == "oracle" for b in standard["blocks"])
    assert all(
        any(f["text"] in b["text"] for b in standard["blocks"]) for f in case["required_facts"]
    )
