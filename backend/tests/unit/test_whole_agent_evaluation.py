"""Unpaid contract checks using generated fixtures, never the blind case contents."""

import hashlib
import json

import pytest

from whole_agent_evaluation.__main__ import FIXTURES, FROZEN_MANIFEST_SHA256
from whole_agent_evaluation.runner import PHASES, case_risk_type, load_suite, summarize


def make_fixture(tmp_path):
    root = tmp_path / "frozen"
    root.mkdir()
    (root / "documents").mkdir()
    (root / "documents/policy.md").write_text("# Fictional policy\n")
    (root / "business.json").write_text(json.dumps({"students": [], "classes": [], "absences": []}))
    for phase, count in PHASES.items():
        cases = [
            {
                "id": f"{phase}-{number}",
                "category": "document_qa",
                "message": "What is the policy?",
                "as_of": "2027-06-01",
                "setup": {"document_keys": ["policy"]},
                "expected": {"route": "enquiry"},
            }
            for number in range(count)
        ]
        (root / f"{phase}.json").write_text(json.dumps(cases))
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }
    manifest = {
        "version": "whole-agent-validation-v1",
        "files": files,
        "documents": [
            {
                "key": "policy",
                "title": "Fictional policy",
                "file": "documents/policy.md",
                "sha256": files["documents/policy.md"],
                "effective_from": "2027-01-01",
                "effective_to": "2027-12-31",
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


def test_load_suite_validates_counts_and_hashes(tmp_path):
    root = make_fixture(tmp_path)
    _, business, sources, phases, digest = load_suite(root)
    assert business["students"] == []
    assert len(sources) == 1
    assert [len(phases[name]) for name in PHASES] == [5, 100, 25]
    assert len(digest) == 64
    (root / "documents/policy.md").write_text("Changed")
    with pytest.raises(ValueError, match="Frozen fixture changed"):
        load_suite(root)


def test_load_suite_rejects_unsafe_path(tmp_path):
    root = make_fixture(tmp_path)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"]["../outside"] = "0" * 64
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe fixture path"):
        load_suite(root)


def test_category_summary_retains_partial_results():
    result = summarize(
        [
            {"category": "makeup_absence", "status": "completed"},
            {"category": "makeup_absence", "status": "failed"},
        ],
        100,
    )
    assert result["expected"] == 100
    assert result["attempted"] == 2
    assert result["categories"]["makeup_absence"] == {"completed": 1, "failed": 1}


def test_independent_manifest_remains_pinned():
    assert hashlib.sha256((FIXTURES / "manifest.json").read_bytes()).hexdigest() == (
        FROZEN_MANIFEST_SHA256
    )


def test_risk_type_comes_from_frozen_setup():
    assert case_risk_type({"setup": {"risk_type": "identity_privacy"}}) == "identity_privacy"
