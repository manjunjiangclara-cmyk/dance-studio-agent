"""Independent online safety regressions; all providers and source reads are fake."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from datetime import date
from pathlib import Path
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import UUID

import pytest

from studio_copilot.agent.document_answers import document_draft
from studio_copilot.agent.enquiry import validate_answers
from studio_copilot.agent.workflow.nodes import WorkflowNodes
from studio_copilot.documents import online


def state(count=2):
    questions = [f"Question {number}?" for number in range(count)]
    ids = {question: str(UUID(int=index + 1)) for index, question in enumerate(questions)}
    return dict(
        flow="enquiry",
        document_answers_enabled=True,
        context={
            "policy": {"version": "test"},
            "source": {"occurred_at": "2026-06-01T12:00:00+10:00"},
            "student": {},
        },
        interpretation=dict(questions=questions, question_ids=ids, requested_actions=[]),
        evidence=[],
    )


def result_evidence(value, index, *, references=1, status="answered"):
    question = value["interpretation"]["questions"][index]
    question_id = value["interpretation"]["question_ids"][question]
    return dict(
        tool="document_answer",
        result=dict(
            question_id=question_id,
            question=question,
            status=status,
            missing_information=[],
            answer=f"Supported answer {index}.",
            claims=[dict(text=f"Supported answer {index}.")],
            references=[f"document:{index}-{number}" for number in range(references)],
        ),
    )


def config():
    return online.Configuration((UUID(int=90),), Path("fake-tokenizer"), Path("fake-reranker"))


def test_eight_complete_answers_cannot_overflow_global_reference_contract():
    value = state(8)
    value["evidence"] = [result_evidence(value, index, references=6) for index in range(8)]
    draft = document_draft(value)
    assert len(draft.references) <= 40
    assert len(draft.answers) == 8
    assert all(len(item.references) <= 40 for item in draft.answers)
    assert any(item.status == "needs_teacher" for item in draft.answers)


def test_teacher_answer_remains_scoped_and_does_not_fill_other_question():
    value = state()
    questions = value["interpretation"]["questions"]
    question_id = value["interpretation"]["question_ids"][questions[0]]
    value["question_resolutions"] = [
        dict(question_id=question_id, decision="answer", answer="TEACHER_FIRST_QUESTION_ONLY")
    ]
    draft = validate_answers(document_draft(value), value)
    assert draft.answers[0].answer == "TEACHER_FIRST_QUESTION_ONLY"
    assert draft.answers[0].status == "answered"
    assert draft.answers[1].status == "needs_teacher"
    assert "TEACHER_FIRST_QUESTION_ONLY" not in draft.answers[1].answer
    assert draft.answers[1].references == []
    assert draft.body.count("TEACHER_FIRST_QUESTION_ONLY") == 1


@pytest.mark.parametrize("status", ["partial", "needs_clarification", "abstained", "failed"])
def test_noncomplete_results_stay_reviewable_and_out_of_final_claims(status):
    value = state(1)
    value["evidence"] = [result_evidence(value, 0, status=status)]
    draft = document_draft(value)
    assert draft.answers[0].status == "needs_teacher"
    assert not draft.references
    assert "Supported answer" not in draft.body
    assert value["evidence"][0]["result"]["answer"] == "Supported answer 0."


def test_current_source_check_uses_only_retained_document_citations(monkeypatch):
    retained = dict(references=["document:kept"], sources=[dict(run_id=str(UUID(int=90)))])
    discarded = dict(references=["document:discarded"], sources=[dict(run_id=str(UUID(int=91)))])
    run = SimpleNamespace(
        evidence=[dict(tool="document_answer", result=item) for item in [retained, discarded]],
        draft_details=dict(references=["document:kept", "teacher_answer:other"]),
    )
    monkeypatch.setattr(
        online.Configuration, "from_env", classmethod(lambda cls, *a, **kw: config())
    )
    checks = []
    monkeypatch.setattr(
        online,
        "check_identities",
        lambda db, selected, identities, today, **kwargs: checks.append((identities, kwargs)),
    )
    online.require_current_sources(object(), run)
    assert checks == [(retained["sources"], dict(lock=True))]


def test_disabling_after_draft_revokes_retained_citations(monkeypatch):
    run = SimpleNamespace(
        evidence=[dict(tool="document_answer", result=dict(references=["document:kept"]))],
        draft_details=dict(references=["document:kept"]),
    )
    monkeypatch.setattr(online.Configuration, "from_env", classmethod(lambda cls, *a, **kw: None))
    with pytest.raises(online.OnlineError) as error:
        online.require_current_sources(object(), run)
    assert error.value.code == "source_revoked"


def test_source_mutation_during_generation_cannot_return_success(monkeypatch):
    selected = config()
    snapshot = dict(degraded=False, candidates=[], parents=[])
    monkeypatch.setattr(online, "capture", lambda *args, **kwargs: deepcopy(snapshot))
    monkeypatch.setattr(online, "pack_from_records", lambda *args: ([], 0, []))
    monkeypatch.setattr(online, "build_artifact", lambda *args: ({}, [dict(run_id="old")]))
    mutated = []

    def fake_answer(*args, **kwargs):
        mutated.append(True)
        return dict(execution_status="completed", claims=[])

    monkeypatch.setattr(online, "answer", fake_answer)
    monkeypatch.setattr(online, "Session", lambda engine: nullcontext(object()))

    def invalid_source(*args, **kwargs):
        assert mutated == [True]
        raise online.OnlineError("source_changed")

    monkeypatch.setattr(online, "check_identities", invalid_source)
    with pytest.raises(online.OnlineError) as error:
        online.question_answer(
            object(), selected, "Question?", "case", date(2026, 6, 1), object(), object()
        )
    assert error.value.code == "source_changed"


def test_missing_resources_gives_reviewable_failure_without_provider(monkeypatch):
    attempted = []

    def missing(*args):
        attempted.append(args)
        raise RuntimeError("PRIVATE_RESOURCE_ERROR")

    monkeypatch.setattr(online, "Session", lambda engine: nullcontext(object()))
    monkeypatch.setattr(online, "source_rows", lambda *args: [])
    monkeypatch.setattr(online, "resources", missing)
    monkeypatch.setattr(
        online,
        "question_answer",
        lambda *args, **kwargs: pytest.fail("provider path ran after initialization failed"),
    )
    value = state(1)
    gathered = online.gather(object(), value, config=config())
    assert attempted == [(config().tokenizer_cache, config().reranker_cache)]
    assert gathered["evidence"][0]["result"]["status"] == "failed"
    assert "PRIVATE_RESOURCE_ERROR" not in str(gathered)
    assert gathered["warnings"]


def test_concurrent_cold_resources_constructs_one_local_model(monkeypatch):
    online._resources.cache_clear()
    ready, release, start = Event(), Event(), Barrier(5)
    tokenizers, models = [], []

    def tokenizer(path):
        tokenizers.append(object())
        ready.set()
        assert release.wait(timeout=5)
        return tokenizers[-1]

    def model(path, identity):
        assert identity == online.L6
        models.append(object())
        return models[-1]

    monkeypatch.setattr(online, "Tokenizer", tokenizer)
    monkeypatch.setattr(online, "LocalReranker", model)

    def load():
        start.wait(timeout=5)
        return online.resources(Path("tokens"), Path("model"))

    try:
        with ThreadPoolExecutor(max_workers=4) as workers:
            futures = [workers.submit(load) for _ in range(4)]
            start.wait(timeout=5)
            assert ready.wait(timeout=5)
            release.set()
            results = [future.result(timeout=5) for future in futures]
        assert len(tokenizers) == len(models) == 1
        assert all(result[0] is tokenizers[0] and result[1] is models[0] for result in results)
    finally:
        release.set()
        online._resources.cache_clear()


def test_all_teacher_resolved_questions_skip_sources_resources_and_providers(monkeypatch):
    value = state(1)
    question_id = next(iter(value["interpretation"]["question_ids"].values()))
    value["question_resolutions"] = [
        dict(question_id=question_id, decision="answer", answer="Explicit teacher answer.")
    ]

    def forbidden(*args, **kwargs):
        pytest.fail("Teacher-resolved questions must not initialize or call document resources")

    monkeypatch.setattr(online, "Session", forbidden)
    monkeypatch.setattr(online, "resources", forbidden)
    monkeypatch.setattr(online, "question_answer", forbidden)
    assert online.gather(object(), value, config=config()) == dict(evidence=[], warnings=[])


def test_document_draft_hides_citation_tokens_but_keeps_teacher_references():
    value = state(1)
    evidence = result_evidence(value, 0)
    evidence["result"].update(
        answer="A trial costs $20. [E0123456789abcdef01234567] [Eabcdef0123456789abcdef01]",
        claims=[
            {
                "text": "A trial costs $20. [E0123456789abcdef01234567]",
                "citations": [
                    {"evidence_id": "E0123456789abcdef01234567", "quote": "A trial costs $20."},
                    {"evidence_id": "Eabcdef0123456789abcdef01", "quote": "A trial costs $20."},
                ],
            }
        ],
        references=["document:E0123456789abcdef01234567", "document:Eabcdef0123456789abcdef01"],
    )
    value["evidence"] = [evidence]
    before = deepcopy(evidence)
    draft = document_draft(value)
    assert "A trial costs $20." in draft.body
    assert "A trial costs $20." in draft.answers[0].answer
    for token in (
        "[E0123456789abcdef01234567]",
        "[Eabcdef0123456789abcdef01]",
        "document:E0123456789abcdef01234567",
        "document:Eabcdef0123456789abcdef01",
    ):
        assert token not in draft.body
        assert token not in draft.answers[0].answer
    assert draft.references == [
        "document:E0123456789abcdef01234567",
        "document:Eabcdef0123456789abcdef01",
    ]
    assert draft.answers[0].references == draft.references
    assert value["evidence"][0] == before


@pytest.mark.parametrize(
    "marker",
    [
        "[Eabcdef0123456789abcdef01]",
        "Eabcdef0123456789abcdef01",
        "document:Eabcdef0123456789abcdef01",
        "[document:Eabcdef0123456789abcdef01]",
    ],
)
def test_unexpected_internal_ids_are_removed_from_student_claims(marker):
    value = state(1)
    evidence = result_evidence(value, 0)
    evidence["result"]["claims"][0]["text"] = f"A trial costs $20. {marker}"
    value["evidence"] = [evidence]
    draft = document_draft(value)
    assert draft.answers[0].answer == "A trial costs $20."
    assert marker not in draft.body
    assert draft.references == evidence["result"]["references"]


def test_document_generation_instructions_use_teacher_voice_and_structured_citations():
    from studio_copilot.documents.generation.provider import GENERATE

    instructions = " ".join(GENERATE.lower().split())
    assert "teacher speaking directly to the student" in instructions
    assert "warm" in instructions and "collaborative" in instructions
    assert "evidence ids and citations in their structured fields" in instructions


@pytest.mark.parametrize(
    "body",
    ["", " ", "x" * 20_001, "See [Eabcdef0123456789abcdef01]", "teacher_answer:secret"],
)
def test_invalid_composition_uses_grounded_fallback_without_losing_citations(body):
    value = state(1)
    value["warnings"] = []
    value["evidence"] = [result_evidence(value, 0)]
    model = SimpleNamespace(compose_document_email=lambda context: body)
    draft = WorkflowNodes(SimpleNamespace(engine=None), model).draft(value)["draft"]
    assert "Supported answer 0." in draft["body"]
    assert draft["references"] == ["document:0-0"]
    assert "composition" in draft["rationale"].lower()
