"""Evidence labels measure complete source information, not a one-character overlap."""

from studio_copilot.documents.retrieval.evaluation import covered, measures


def test_source_coverage_can_span_adjacent_passages_but_never_bridge_a_gap():
    label = dict(start=10, end=30)
    assert covered(label, [dict(start=20, end=35), dict(start=5, end=20)])
    assert not covered(label, [dict(start=5, end=19), dict(start=20, end=35)])
    assert not covered(label, [dict(start=29, end=35)])


def test_recall_requires_each_evidence_item_and_mrr_uses_first_relevant_hit():
    labels = [dict(start=10, end=20), dict(start=50, end=60)]
    ranked = [[dict(start=0, end=5)], [dict(start=5, end=25)], [dict(start=45, end=65)]]
    assert measures(labels, ranked, 2) == dict(recall=0.5, all_evidence=False, reciprocal_rank=0.5)
    assert measures(labels, ranked, 3) == dict(recall=1.0, all_evidence=True, reciprocal_rank=0.5)
