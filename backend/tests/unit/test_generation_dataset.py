"""Independent checks of frozen generation labels and source/question lineage."""

import hashlib
import json
from collections import Counter
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_frozen_labels_resolve_to_original_unicode_sources_and_eligible_dates():
    data = json.loads((FIXTURES / "generation_cases.json").read_text())
    documents, seeds = {}, {}
    for manifest in data["source_manifests"]:
        path = FIXTURES / manifest["file"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["sha256"]
        source = json.loads(raw)
        for item in source["documents"]:
            original = (path.parent / item["file"]).read_bytes().decode("utf-8")
            assert hashlib.sha256(original.encode("utf-8")).hexdigest() == item["sha256"]
            documents[item["key"]] = dict(item, text=original)
        seeds.update((case["id"], case) for case in source["cases"])
    for case in data["cases"]:
        for fact in case["required_facts"]:
            document = documents[fact["document_key"]]
            assert document["text"][fact["start"] : fact["end"]] == fact["text"], case["id"]
            assert document["effective_from"] <= case["as_of"] <= document["effective_to"]
        seed = seeds[case["source_case_id"]]
        if case["context_variant"] == "original":
            assert case["question"] == seed["query"]
            assert case["as_of"] == seed["as_of"]
        else:
            assert case["context_variant"] == "controlled"


def test_splits_are_balanced_distinct_and_controlled_losses_are_explicit():
    data = json.loads((FIXTURES / "generation_cases.json").read_text())
    assert data["case_count"] == len(data["cases"]) == 80
    assert len({case["id"] for case in data["cases"]}) == 80
    families = {}
    for split in ("tuning", "held_out"):
        cases = [case for case in data["cases"] if case["split"] == split]
        assert len(cases) == 40
        categories = Counter(case["tags"][0] for case in cases)
        assert categories == dict(
            ordinary_answer=24,
            missing_evidence=4,
            conflicting_authority=3,
            no_answer=3,
            expired_sources=2,
            missing_user_detail=2,
            live_database=1,
            prompt_injection=1,
        )
        families[split] = {
            fact["document_key"].rsplit("_", 1)[0]
            for case in cases
            for fact in case["required_facts"]
        }
        for case in cases:
            if case["drop_fact_ids"]:
                assert case["context_variant"] == "controlled"
                assert case["expected_actual_status"] == "partial"
                assert case["expected_standard_status"] == "answered"
                fact_ids = {fact["id"] for fact in case["required_facts"]}
                assert set(case["drop_fact_ids"]) < fact_ids
    assert families["tuning"].isdisjoint(families["held_out"])
