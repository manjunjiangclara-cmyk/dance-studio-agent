"""Contract checks for the isolated, unpaid integrated RAG evaluation runner."""

import hashlib
import json
import re

import pytest

from integrated_rag_evaluation.review import merge
from integrated_rag_evaluation.runner import (
    BudgetExceeded,
    RunBudget,
    fingerprint,
    output_hash,
    summarize,
)


def test_fingerprint_is_content_based_and_reproducible(tmp_path):
    dataset = tmp_path / "cases.json"
    corpus = tmp_path / "corpus.json"
    source = tmp_path / "policy.md"
    source.write_text("# Policy\nA lesson costs $20.\n", encoding="utf-8")
    dataset.write_text('{"cases": [{"id": "case-1"}]}\n', encoding="utf-8")
    corpus.write_text(
        json.dumps(
            {
                "version": "retrieval-corpus-v2",
                "documents": [
                    {
                        "key": "policy",
                        "title": "Fictional policy",
                        "file": source.name,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "effective_from": "2027-01-01",
                        "effective_to": "2027-12-31",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    first = fingerprint(dataset, corpus)
    assert first == fingerprint(dataset, corpus)
    assert re.fullmatch(r"[0-9a-f]{64}", first)

    dataset.write_text('{"cases": [{"id": "case-2"}]}\n', encoding="utf-8")
    changed_dataset = fingerprint(dataset, corpus)
    assert changed_dataset != first

    dataset.write_text('{"cases": [{"id": "case-1"}]}\n', encoding="utf-8")
    source.write_text("# Policy\nA lesson costs $25.\n", encoding="utf-8")
    assert fingerprint(dataset, corpus) != first

    source.write_text("# Policy\nA lesson costs $20.\n", encoding="utf-8")
    manifest = json.loads(corpus.read_text(encoding="utf-8"))
    manifest["documents"][0]["effective_to"] = "2028-12-31"
    corpus.write_text(json.dumps(manifest), encoding="utf-8")
    assert fingerprint(dataset, corpus) != first


def test_request_cap_rejects_next_call_and_retains_first_result():
    budget = RunBudget(max_requests=1, max_input_tokens=100, max_output_tokens=20)
    ticket = budget.reserve(10, 5)
    budget.record(ticket, actual_input=7, actual_output=3)

    with pytest.raises(BudgetExceeded):
        budget.reserve(10, 5)

    snapshot = budget.snapshot()
    assert snapshot["requests"] == 1
    assert snapshot["input_tokens"] == 7
    assert snapshot["output_tokens"] == 3
    assert snapshot["exhausted"] is True


@pytest.mark.parametrize(
    "limits,reservation",
    [
        ({"max_requests": 2, "max_input_tokens": 9, "max_output_tokens": 10}, (10, 1)),
        ({"max_requests": 2, "max_input_tokens": 10, "max_output_tokens": 9}, (1, 10)),
    ],
)
def test_token_caps_reject_before_provider_call(limits, reservation):
    budget = RunBudget(**limits)
    with pytest.raises(BudgetExceeded):
        budget.reserve(*reservation)
    assert budget.snapshot()["requests"] == 0


def test_unknown_actual_usage_is_preserved_as_unknown():
    budget = RunBudget(max_requests=1, max_input_tokens=100, max_output_tokens=20)
    ticket = budget.reserve(10, 5)
    budget.record(ticket, actual_input=None, actual_output=None)
    snapshot = budget.snapshot()
    assert snapshot["requests"] == 1
    assert snapshot["unknown_usage_calls"] == 1
    assert snapshot["reserved_input_tokens"] >= 10
    assert snapshot["reserved_output_tokens"] >= 5


def test_ticket_cannot_be_settled_twice():
    budget = RunBudget(max_requests=2, max_input_tokens=100, max_output_tokens=20)
    ticket = budget.reserve(10, 5)
    budget.record(ticket, actual_input=7, actual_output=3)
    first = budget.snapshot()

    with pytest.raises(ValueError):
        budget.record(ticket, actual_input=50, actual_output=10)
    assert budget.snapshot() == first


def test_summary_denominators_exclude_failures_and_unreviewed_rows():
    results = [
        {
            "status": "completed",
            "review": {
                "supported": True,
                "complete": False,
                "teacher_ready": False,
                "correct_refusal": None,
                "false_refusal": True,
                "citation_relevant": True,
            },
        },
        {
            "status": "completed",
            "review": {
                "supported": False,
                "complete": True,
                "teacher_ready": True,
                "correct_refusal": True,
                "false_refusal": None,
                "citation_relevant": False,
            },
        },
        {"status": "completed", "review": None},
        {
            "status": "failed",
            "review": {
                "supported": True,
                "complete": True,
                "teacher_ready": True,
                "correct_refusal": True,
                "false_refusal": False,
                "citation_relevant": True,
            },
        },
    ]

    summary = summarize(results)
    assert summary["total"] == 4
    assert summary["completed"] == 3
    assert summary["failures"] == 1
    assert summary["reviewed"] == 2
    for metric, expected in {
        "supported": (1, 2),
        "complete": (1, 2),
        "teacher_ready": (1, 2),
        "correct_refusal": (1, 1),
        "false_refusal": (1, 1),
        "citation_relevant": (1, 2),
    }.items():
        assert summary[metric] == {"count": expected[0], "denominator": expected[1]}


def test_empty_summary_never_reports_a_percentage_without_a_denominator():
    summary = summarize([{"status": "failed", "review": None}])
    assert summary["total"] == summary["failures"] == 1
    assert summary["reviewed"] == 0
    assert summary["supported"] == {"count": 0, "denominator": 0}
    assert summary["correct_refusal"] == {"count": 0, "denominator": 0}


def test_review_requires_exact_output_hash_and_complete_case_coverage():
    row = {
        "id": "one",
        "status": "completed",
        "draft": {"body": "Cited answer"},
        "document_evidence": [{"quote": "Source text"}],
        "review": None,
    }
    judgment = {
        "id": "one",
        "output_sha256": output_hash(row),
        "issues": [],
        "supported": True,
        "complete": True,
        "teacher_ready": True,
        "citation_relevant": True,
        "correct_refusal": None,
        "false_refusal": False,
    }
    with pytest.raises(ValueError):
        merge({"results": [row.copy()]}, {"results": []})
    with pytest.raises(ValueError):
        merge({"results": [row.copy()]}, {"results": [dict(judgment, output_sha256="bad")]})
    merged = merge({"results": [row.copy()]}, {"results": [judgment]})
    assert merged["results"][0]["review"]["supported"] is True
    assert merged["decision"] == "hold: incomplete case set"


def test_partial_review_cannot_be_declared_a_pilot():
    from integrated_rag_evaluation.review import decision

    rows = [{"review": {"supported": True}} for _ in range(30)]
    summary = {
        "total": 30,
        "completed": 30,
        "failures": 0,
        "reviewed": 30,
        "supported": {"count": 30, "denominator": 30},
        "complete": {"count": 30, "denominator": 30},
        "correct_refusal": {"count": 6, "denominator": 6},
        "false_refusal": {"count": 0, "denominator": 24},
    }
    assert decision(summary, rows, "evaluation") == "hold: incomplete review judgments"
