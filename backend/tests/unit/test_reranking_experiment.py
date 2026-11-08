"""Independent offline scoring and adoption gates use no DB or provider."""

from copy import deepcopy

import pytest

from studio_copilot.documents.reranking.runtime import RerankError


class Characters:
    def count(self, text):
        return len(text)


def example():
    case = dict(
        id="fresh-rule",
        split="validation",
        query="Which rule and exception apply?",
        as_of="2027-06-01",
        answerable=True,
        expected_empty=False,
        evidence=[dict(document_key="policy", start=10, end=20)],
        tags=[],
    )
    candidates = [
        dict(
            run_id=f"run-{i}",
            chunk_id=f"passage-{i}",
            parent_id=None,
            document_key="policy" if i == 6 else "distractor",
            document_id=f"document-{i}",
            revision=1,
            text_sha256=f"{i:064x}",
            text=f"Passage {i}",
            prefix="",
            source_spans=[dict(start=10, end=20, role="body")],
            other_sources=[],
            effective_from="2027-01-01",
            effective_to="2027-12-31",
        )
        for i in range(7)
    ]
    return case, dict(candidates=candidates, parents={}, source_runs=[])


class TailFirst:
    def rank(self, query, candidates):
        return [
            dict(item, rerank_score=float(i), window_count=1)
            for i, item in reversed(list(enumerate(candidates)))
        ]


def test_replay_promotes_evidence_from_same_candidates_without_mutation(monkeypatch):
    from studio_copilot.documents.reranking.experiment import evaluate_case

    case, snapshot = example()
    original = deepcopy(snapshot)
    baseline = evaluate_case(case, snapshot, Characters())
    reranked = evaluate_case(case, snapshot, Characters(), scorer=TailFirst())
    assert baseline["final_at_6"]["recall"] == 0
    assert baseline["fused_at_20"]["recall"] == 1
    assert reranked["final_at_6"]["recall"] == 1
    assert reranked["final_at_6"]["reciprocal_rank"] == 1
    assert reranked["returned_results"] == 6
    assert snapshot == original


def test_identical_integer_offsets_in_other_document_never_satisfy_evidence():
    from studio_copilot.documents.reranking.experiment import evaluate_case

    case, snapshot = example()
    snapshot["candidates"][6]["document_key"] = "expired-policy"
    report = evaluate_case(case, snapshot, Characters(), scorer=TailFirst())
    assert report["final_at_6"]["recall"] == 0
    assert report["expanded_evidence"]["recall"] == 0


def test_visible_alternate_reference_credits_source_but_not_unpacked_parent():
    from studio_copilot.documents.reranking.experiment import evaluate_case

    case, snapshot = example()
    snapshot["candidates"] = snapshot["candidates"][:1]
    snapshot["candidates"][0]["other_sources"] = [
        dict(
            run_id="actual-rule",
            document_key="policy",
            source_spans=[dict(start=10, end=20)],
        )
    ]
    report = evaluate_case(case, snapshot, Characters())
    assert report["final_at_6"]["recall"] == 1
    assert report["expanded_evidence"]["recall"] == 0


def test_scorer_failure_is_an_explicit_miss_instead_of_baseline_fallback():
    from studio_copilot.documents.reranking.experiment import evaluate_case

    class Broken:
        def rank(self, query, candidates):
            raise RerankError("invalid_scores", "sensitive diagnostic must not leak")

    case, snapshot = example()
    # Put evidence first, proving a silent fallback would incorrectly count a hit.
    snapshot["candidates"].reverse()
    report = evaluate_case(case, snapshot, Characters(), scorer=Broken())
    assert report["failed"] is True
    assert report["final_at_6"]["recall"] == 0
    assert report["final_at_6"]["all_evidence"] is False
    assert "sensitive diagnostic" not in str(report)


def passing_summary():
    return dict(
        final_at_6=dict(recall=0.95, reciprocal_rank=0.90, all_evidence=0.925),
        multi_source_all_evidence=0.90,
        failed=0,
        date_exclusion_checks_pass=True,
    )


def test_adoption_requires_fresh_complete_evidence_gain_and_all_safety_gates():
    from studio_copilot.documents.reranking.experiment import adoption

    baseline = passing_summary()
    improved = deepcopy(baseline)
    improved["final_at_6"]["all_evidence"] += 0.025
    assert adoption(baseline, improved, 2.0)["recommended"] is True
    assert adoption(baseline, baseline, 0.1)["recommended"] is False


@pytest.mark.parametrize(
    "regression", ["recall", "mrr", "multi_source", "failure", "date", "latency"]
)
def test_improved_complete_evidence_cannot_hide_other_adoption_regressions(regression):
    from studio_copilot.documents.reranking.experiment import adoption

    baseline = passing_summary()
    improved = deepcopy(baseline)
    improved["final_at_6"]["all_evidence"] = 1.0
    latency = 1.0
    if regression == "recall":
        improved["final_at_6"]["recall"] = 0.94
    elif regression == "mrr":
        improved["final_at_6"]["reciprocal_rank"] = 0.88
    elif regression == "multi_source":
        improved["multi_source_all_evidence"] = 0.89
    elif regression == "failure":
        improved["failed"] = 1
    elif regression == "date":
        improved["date_exclusion_checks_pass"] = False
    else:
        latency = 2.0001
    result = adoption(baseline, improved, latency)
    assert result["recommended"] is False
    assert result["reasons"]


def test_failed_answerable_stays_in_summary_denominator_and_noanswers_are_separate():
    from studio_copilot.documents.reranking.experiment import evaluate_case, summarize_cases

    case, snapshot = example()
    case["split"] = "fresh_validation"
    success = evaluate_case(case, snapshot, Characters(), scorer=TailFirst())
    failed = deepcopy(success)
    failed.update(id="failed", failed=True)
    for stage in ("fused_at_20", "final_at_6", "expanded_evidence"):
        failed[stage] = dict(recall=0.0, all_evidence=False, reciprocal_rank=0.0)
    missing = deepcopy(case)
    missing.update(id="unanswerable", answerable=False, evidence=[])
    unanswered = evaluate_case(missing, snapshot, Characters())
    result = summarize_cases([success, failed, unanswered])["fresh_validation"]
    assert result["answerable"] == 2
    assert result["failed"] == 1
    assert result["final_at_6"]["recall"] == 0.5
    assert result["final_at_6"]["all_evidence"] == 0.5
    assert result["unanswerable_with_results"] == 1


def test_expected_empty_case_with_any_result_fails_date_exclusion_summary():
    from studio_copilot.documents.reranking.experiment import evaluate_case, summarize_cases

    case, snapshot = example()
    case.update(answerable=False, expected_empty=True, evidence=[], split="fresh_validation")
    result = evaluate_case(case, snapshot, Characters())
    assert summarize_cases([result])["fresh_validation"]["date_exclusion_checks_pass"] is False
    result = evaluate_case(case, dict(snapshot, candidates=[]), Characters())
    assert summarize_cases([result])["fresh_validation"]["date_exclusion_checks_pass"] is True
