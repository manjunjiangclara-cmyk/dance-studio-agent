"""Fresh validation is pinned before any models are run."""

import shutil
from collections import Counter

import pytest

from studio_copilot.documents.reranking.runtime import RerankError


def test_frozen_dataset_has_disjoint_splits_and_exact_source_aware_labels(monkeypatch):
    from studio_copilot.documents.reranking.dataset import load_dataset

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "invalid://must-not-be-used")
    loaded = load_dataset()
    assert len(loaded["documents"]) == 24
    assert Counter(case["split"] for case in loaded["cases"]) == {
        "tuning": 50,
        "diagnostic": 50,
        "fresh_validation": 50,
    }
    assert len({case["id"] for case in loaded["cases"]}) == 150
    by_key = {document["key"]: document for document in loaded["documents"]}
    fresh = [case for case in loaded["cases"] if case["split"] == "fresh_validation"]
    assert sum(case["answerable"] for case in fresh) == 40
    assert sum(case["expected_empty"] for case in fresh) == 2
    assert (
        sum(len({label["document_key"] for label in case["evidence"]}) > 1 for case in fresh) == 16
    )
    for case in loaded["cases"]:
        for label in case["evidence"]:
            doc = by_key[label["document_key"]]
            assert doc["text"][label["start"] : label["end"]] == label["text"]
            assert doc["effective_from"] <= case["as_of"] <= doc["effective_to"]


@pytest.mark.parametrize("damage", ["source", "manifest"])
def test_fixture_changes_fail_before_inference_or_database_access(tmp_path, monkeypatch, damage):
    from studio_copilot.documents.reranking import dataset

    fixtures = tmp_path / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    for name in ("retrieval_corpus_v2", "reranking_validation"):
        shutil.copytree(dataset.BACKEND / "tests" / "fixtures" / name, fixtures / name)
    monkeypatch.setattr(dataset, "BACKEND", tmp_path)
    filename = "guest_office.md" if damage == "source" else "validation.json"
    target = fixtures / "reranking_validation" / filename
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(RerankError):
        dataset.load_dataset()
