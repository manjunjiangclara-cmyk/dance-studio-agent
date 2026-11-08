"""Prompt routing and provenance regressions, not fake semantic-quality evidence."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from studio_copilot.documents.generation import engine, evaluation
from studio_copilot.documents.generation.contracts import Candidate, Citation, GenerationError
from studio_copilot.documents.generation.evidence import (
    hash_value,
    make_block,
    model_payload,
    resolve_quote,
    seal_artifact,
    source_id,
)
from studio_copilot.documents.generation.provider import (
    GENERATE,
    GENERATE_V2,
    VERIFY,
    GenerationProvider,
    generation_prompt,
    prompt_metadata,
)
from tests.unit.test_generation_engine import Provider, candidate
from tests.unit.test_generation_evidence import Characters, artifact
from tests.unit.test_generation_provider import client
from tests.unit.test_generation_workflow import evidence_set


def test_v1_prompt_is_byte_for_byte_frozen_and_remains_default():
    frozen = json.loads(
        (
            Path(__file__).parents[3] / "docs/measurements/generation-freeze-2026-11-08.json"
        ).read_text()
    )
    assert GENERATE == frozen["prompts"]["generate"]
    assert VERIFY == frozen["prompts"]["verify"]
    assert generation_prompt() == GENERATE
    assert prompt_metadata()["prompt_sha256"] == frozen["prompt_sha256"]
    assert generation_prompt("v2") == GENERATE_V2 != GENERATE
    assert prompt_metadata("v2")["prompt_sha256"] != frozen["prompt_sha256"]


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_selected_writer_reaches_sdk_with_identical_source_payload(version):
    value = artifact()
    before = deepcopy(value)
    sdk = client()
    provider = GenerationProvider(client=sdk, model="fake", prompt_version=version)
    result = engine.answer(
        value, Characters(), allow_api=True, provider=provider, prompt_version=version
    )
    assert len(sdk.responses.calls) == 1
    call = sdk.responses.calls[0]
    assert call["instructions"] == generation_prompt(version)
    assert json.loads(call["input"]) == model_payload(value, prompt_version=version)
    assert call["store"] is False
    assert value == before
    assert result["prompt_version"] == f"grounded-generation-{version}"
    assert result["calls"][0]["instructions_sha256"] == hash_value(generation_prompt(version))
    assert result["calls"][0]["generation_config"]["max_retries"] == 0
    assert result["verification_applied"] is False


@pytest.mark.parametrize(
    "missing", [["Which rule governs the requested charge?"], [" ", "Need date"]]
)
def test_answered_with_declared_unknowns_is_downgraded(missing):
    value = artifact()
    output = candidate(value).model_copy(update={"missing_information": missing})
    result = engine.validate_candidate(value, output)
    assert result["status"] == "partial"
    assert result["reason_code"] == "insufficient_evidence"
    assert result["state_adjustments"] == ["answered_with_missing_information"]
    assert result["claims"]


def test_empty_missing_information_never_upgrades_partial():
    value = artifact()
    output = candidate(value).model_copy(update={"status": "partial", "missing_information": []})
    assert engine.validate_candidate(value, output)["status"] == "partial"


def test_invalid_quote_takes_precedence_over_status_adjustment():
    value = artifact()
    raw = candidate(value).model_dump()
    raw["missing_information"] = ["Unresolved authority"]
    raw["claims"][0]["citations"][0]["quote"] = "forged citation"
    result = engine.validate_candidate(value, Candidate.model_validate(raw))
    assert result["status"] == "abstained"
    assert result["reason_code"] == "invalid_citations"
    assert not result["claims"]


def test_source_conflict_does_not_automatically_prevent_answering_a_comparison():
    value = artifact()
    output = candidate(value).model_copy(update={"reason_code": "conflicting_sources"})
    # Code cannot decide whether a question asks for comparison or authority selection.
    assert engine.validate_candidate(value, output)["status"] == "answered"


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_empty_evidence_preserves_version_and_makes_zero_calls(version):
    value = artifact()
    value["blocks"] = []
    value = seal_artifact(value)
    provider = Provider(candidate(artifact()))
    result = engine.answer(
        value, Characters(), allow_api=True, provider=provider, prompt_version=version
    )
    assert result["status"] == "abstained"
    assert not provider.generated
    assert result["calls"] == []
    assert result["prompt_version"] == f"grounded-generation-{version}"


def test_mismatched_injected_provider_cannot_make_a_mislabeled_request():
    sdk = client()
    provider = GenerationProvider(client=sdk, model="fake", prompt_version="v1")
    result = engine.answer(
        artifact(), Characters(), allow_api=True, provider=provider, prompt_version="v2"
    )
    assert result["execution_status"] == "failed"
    assert result["error_code"] == "prompt_mismatch"
    assert not sdk.responses.calls


def test_unknown_version_rejected_before_sdk(monkeypatch):
    monkeypatch.setattr(engine, "GenerationProvider", lambda **kw: pytest.fail("SDK constructed"))
    with pytest.raises(GenerationError, match="version"):
        engine.answer(artifact(), Characters(), allow_api=True, prompt_version="v3")


def test_plan_measures_selected_prompt_without_api(tmp_path, monkeypatch):
    directory = evidence_set(tmp_path, monkeypatch)
    first = evaluation.plan(directory, Characters())
    second = evaluation.plan(directory, Characters(), prompt_version="v2")
    assert second["generation_requests"] == first["generation_requests"] == 2
    assert second["estimated_generation_input_tokens"] - first[
        "estimated_generation_input_tokens"
    ] > 2 * (len(GENERATE_V2) - len(GENERATE))
    assert second["answer_language"] == "en"
    assert second["dataset_role"] == "known_regression_diagnostic"
    assert not second["model_requests"]


def test_evaluation_exports_selected_version_and_no_extra_calls(tmp_path, monkeypatch):
    directory = evidence_set(tmp_path, monkeypatch)
    providers = []

    def factory():
        p = GenerationProvider(client=client(), model="fake", prompt_version="v2")
        providers.append(p)
        return p

    output = tmp_path / "answers"
    manifest = evaluation.evaluate_directory(
        directory,
        output,
        Characters(),
        allow_api=True,
        prompt_version="v2",
        provider_factory=factory,
    )
    assert manifest["prompt_version"] == "grounded-generation-v2"
    assert manifest["requests"] == 2
    assert not manifest["compare_verification"]
    rows = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
    assert all(row["prompt_sha256"] == manifest["prompt_sha256"] for row in rows)
    assert all(len(p.client.responses.calls) == 1 for p in providers)
    assert "neither split is an unseen" in (output / "report.md").read_text()
    assert all(row["diagnostic"]["semantic_support"] is None for row in rows)


def test_v2_budget_check_uses_the_selected_instructions_before_calling_model():
    class Meter(Characters):
        def count(self, value):
            return 20001 if value.startswith(GENERATE_V2) else super().count(value)

    value = artifact()
    provider = Provider(candidate(value))
    result = engine.answer(value, Meter(), allow_api=True, prompt_version="v2", provider=provider)
    assert result["error_code"] == "request_limit"
    assert not provider.generated


def test_table_header_and_unicode_quotes_remain_distinct_original_ranges():
    value = artifact()
    source = value["sources"][0]
    original = (
        "| Route | Location or segment | Operational note |\r\n| MC-12 | Café 🙂 | 15:45 |\r\n"
    )
    source["text"] = original
    import hashlib

    source["sha256"] = hashlib.sha256(original.encode()).hexdigest()
    boundary = original.index("\n") + 1
    block = make_block(
        source,
        "table",
        "passage",
        "Navigation prefix",
        [
            dict(start=0, end=boundary, role="table_header"),
            dict(start=boundary, end=len(original), role="body"),
        ],
    )
    value["blocks"] = [block]
    value = seal_artifact(value)
    assert block["source_id"] == source_id(source)
    for quote, role in [("Location or segment", "table_header"), ("Café 🙂", "body")]:
        citation = resolve_quote(value, Citation(evidence_id=block["id"], quote=quote))
        assert citation["role"] == role
        assert original[citation["start"] : citation["end"]] == quote
    assert model_payload(value)["evidence"][0]["text"] == block["text"]
    assert (
        resolve_quote(value, Citation(evidence_id=block["id"], quote="Navigation prefix")) is None
    )


def test_cli_v2_selection_is_explicit_and_default_stays_v1(tmp_path, monkeypatch, capsys):
    from studio_copilot.documents.generation import __main__ as cli

    directory = evidence_set(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "Tokenizer", lambda path: Characters())
    args = ["plan", "--evidence-dir", str(directory)]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["prompt_version"] == "grounded-generation-v1"
    assert cli.main([*args, "--prompt-version", "v2"]) == 0
    assert json.loads(capsys.readouterr().out)["answer_language"] == "en"
    with pytest.raises(SystemExit):
        cli.main([*args, "--answer-language", "zh"])


@pytest.mark.parametrize("english", [True, False])
def test_primary_review_cannot_satisfy_independent_acceptance(english):
    from tests.unit.test_generation_workflow import record

    row = record()
    row["answer_language"] = "en"
    review = dict(
        results_sha256="fixed",
        reviewer="primary reviewer",
        independent=False,
        reviews=[
            dict(
                case_id="one",
                variant="standard",
                path="baseline",
                claims={"c1": True},
                required_facts={"f1": True},
                complete_answer=True,
                appropriate_status=True,
                english_answer=english,
            )
        ],
    )
    metrics = evaluation.summarize([row], adjudication=review, results_sha256="fixed")[
        "held_out/standard/baseline"
    ]
    assert metrics["semantic_review_status"] == "reviewed_primary_only"
    assert metrics["quality_targets"]["criteria"]["independent_review"] is False
    assert metrics["quality_targets"]["passed"] is not True
    assert metrics["english_answer_rate"] == int(english)
    assert metrics["quality_targets"]["criteria"]["english_answer"] is english


def test_english_quality_is_unknown_until_explicit_review():
    from tests.unit.test_generation_workflow import record

    row = record()
    row["answer_language"] = "en"
    metrics = evaluation.summarize([row])["held_out/standard/baseline"]
    assert metrics["english_answer_rate"] is None
    assert metrics["quality_targets"]["criteria"]["english_answer"] is None
    assert metrics["quality_targets"]["passed"] is None


def test_v2_exposes_real_body_discontinuities_without_leaking_missing_text_or_labels():
    value = artifact()
    source = value["sources"][0]
    visible = source["text"]
    first = visible.index(" ") + 1
    last = visible.rindex(" ")
    assert first < last
    block = make_block(
        source,
        "gapped",
        "passage",
        "",
        [
            dict(start=0, end=first, role="body"),
            dict(start=last, end=len(visible), role="body"),
        ],
    )
    value["blocks"] = [block]
    value["provenance"] = dict(controlled_drop=["gold-secret-fact-id"])
    value = seal_artifact(value)
    before = deepcopy(value)
    legacy = model_payload(value)
    current = model_payload(value, prompt_version="v2")
    assert legacy["evidence"][0]["text"] == current["evidence"][0]["text"]
    assert "source_ranges" not in legacy["evidence"][0]
    assert current["evidence"][0]["omitted_body_ranges"] == [dict(start=first, end=last)]
    assert visible[first:last] not in json.dumps(current, ensure_ascii=False)
    assert "gold-secret-fact-id" not in json.dumps(current)
    assert value == before


def test_copied_table_header_does_not_mark_unselected_rows_as_missing_body():
    value = artifact()
    source = value["sources"][0]
    block = make_block(
        source,
        "header",
        "passage",
        "",
        [
            dict(start=0, end=2, role="table_header"),
            dict(start=5, end=len(source["text"]), role="body"),
        ],
    )
    value["blocks"] = [block]
    value = seal_artifact(value)
    assert model_payload(value, prompt_version="v2")["evidence"][0]["omitted_body_ranges"] == []


@pytest.mark.parametrize("cases", [["unknown"], ["case-one", "case-one"]])
def test_unknown_or_duplicate_diagnostic_selection_fails_before_api(tmp_path, monkeypatch, cases):
    directory = evidence_set(tmp_path, monkeypatch)
    with pytest.raises(GenerationError, match="case IDs"):
        evaluation.plan(directory, Characters(), case_ids=cases)


def test_targeted_diagnostic_selection_preserves_frozen_labels(tmp_path, monkeypatch):
    directory = evidence_set(tmp_path, monkeypatch)
    labels = evaluation.load_cases()
    identifier = labels["cases"][0]["id"]
    result = evaluation.plan(directory, Characters(), prompt_version="v2", case_ids=[identifier])
    assert result["artifacts"] == 2
    assert result["case_ids"] == [identifier]
    assert evaluation.load_cases() == labels
    with pytest.raises(GenerationError):
        evaluation.plan(directory, Characters(), case_ids=[identifier], limit=1)
