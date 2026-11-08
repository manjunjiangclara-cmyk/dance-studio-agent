"""Offline context expansion uses selected candidates, preserving evidence limits."""

from studio_copilot.documents.retrieval.engine import BUDGET, pack_from_records


class Characters:
    def count(self, text):
        return len(text)


def hit(index, *, text=None, parent_id=None, run_id="run-a"):
    return dict(
        run_id=run_id,
        chunk_id=f"passage-{index}",
        parent_id=parent_id or f"parent-{index}",
        source_spans=[dict(start=index * 10, end=index * 10 + 10, role="body")],
        prefix="",
        text=text or f"Passage {index}",
    )


def parent(index, text=None):
    return dict(
        kind="parent",
        text=text or f"Parent {index}",
        provenance=dict(source_spans=[dict(start=index * 10, end=index * 10 + 30, role="body")]),
    )


def test_parent_expansion_never_includes_unselected_candidates_or_their_context():
    selected = [hit(i) for i in range(6)]
    parents = {f"run-a:parent-{i}": parent(i) for i in range(40)}
    evidence, count, warnings = pack_from_records(selected, parents, Characters())
    assert len(evidence) == 6
    assert {item["chunk_id"] for item in evidence} == {f"parent-{i}" for i in range(6)}
    assert count == len("\n\n".join(item["text"] for item in evidence))
    assert warnings == []


def test_oversized_parent_keeps_passage_instead_of_dropping_selected_evidence():
    selected = [hit(0), hit(1)]
    parents = {"run-a:parent-0": parent(0, "x" * BUDGET), "run-a:parent-1": parent(1)}
    evidence, count, warnings = pack_from_records(selected, parents, Characters())
    assert count <= BUDGET
    assert evidence[0]["kind"] == "passage"
    assert evidence[0]["text"] == selected[0]["text"]
    assert evidence[1]["kind"] == "parent"
    assert "parent_context_budget_limited" in warnings


def test_same_parent_id_in_two_documents_does_not_mix_sources():
    selected = [hit(0, parent_id="same", run_id="a"), hit(1, parent_id="same", run_id="b")]
    parents = {"a:same": parent(0, "Policy"), "b:same": parent(1, "Exception")}
    evidence, _, _ = pack_from_records(selected, parents, Characters())
    assert [(item["run_id"], item["text"]) for item in evidence] == [
        ("a", "Policy"),
        ("b", "Exception"),
    ]
    assert evidence[0]["source_spans"] != evidence[1]["source_spans"]


def test_shared_parent_is_inserted_once_at_first_selected_passage():
    selected = [hit(0, parent_id="shared"), hit(1), hit(2, parent_id="shared")]
    parents = {"run-a:shared": parent(0, "Rule and exception"), "run-a:parent-1": parent(1)}
    evidence, _, _ = pack_from_records(selected, parents, Characters())
    assert [item["text"] for item in evidence] == ["Rule and exception", "Parent 1"]
