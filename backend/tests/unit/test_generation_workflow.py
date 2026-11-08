"""Independent offline export, paid-gate, paired evaluation and review integrity tests."""

import json
from copy import deepcopy

import pytest

from studio_copilot.documents.generation import evaluation
from studio_copilot.documents.generation.contracts import GenerationError
from studio_copilot.documents.generation.evidence import hash_value
from tests.unit.test_generation_engine import Provider, candidate, verification
from tests.unit.test_generation_evidence import Characters, artifact


def evidence_set(tmp_path, monkeypatch):
    case = dict(
        id="case-one",
        question="What is the exception?",
        as_of="2027-06-01",
        split="tuning",
        expected_standard_status="answered",
        required_facts=[dict(patterns=[["no fee"]])],
        forbidden_patterns=["invented"],
    )
    monkeypatch.setattr(evaluation, "load_cases", lambda: dict(cases=[case]))
    directory = tmp_path / "evidence"
    directory.mkdir()
    items = []
    from studio_copilot.documents.generation.evidence import seal_artifact

    for variant in ("actual", "standard"):
        value = artifact()
        value["variant"] = variant
        value = seal_artifact(value)
        name = variant + ".json"
        evaluation.save(directory / name, value)
        items.append(
            dict(
                case_id="case-one",
                variant=variant,
                file=name,
                artifact_sha256=value["artifact_sha256"],
            )
        )
    evaluation.save(
        directory / "manifest.json",
        dict(
            complete=True,
            cases_sha256=evaluation.CASES_SHA256,
            artifacts=items,
            index_sha256=hash_value(items),
        ),
    )
    return directory


def test_plan_never_constructs_provider_and_counts_optional_requests(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)
    result = evaluation.plan(folder, Characters(), compare_verification=True)
    assert result["generation_requests"] == 2
    assert result["verification_requests_max"] == 2
    assert result["questions"] == 1
    assert result["model_requests"] is False


def test_evaluation_gate_precedes_inputs_outputs_and_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(
        evaluation, "selected_inputs", lambda *a, **k: pytest.fail("read before gate")
    )
    output = tmp_path / "absent"
    with pytest.raises(GenerationError):
        evaluation.evaluate_directory(
            "missing",
            output,
            Characters(),
            provider_factory=lambda: pytest.fail("provider before gate"),
        )
    assert not output.exists()


def test_existing_output_prevents_paid_work(tmp_path, monkeypatch):
    output = tmp_path / "existing"
    output.mkdir()
    monkeypatch.setattr(
        evaluation, "selected_inputs", lambda *a, **k: pytest.fail("read output conflict")
    )
    with pytest.raises(GenerationError):
        evaluation.evaluate_directory("missing", output, Characters(), allow_api=True)
    assert list(output.iterdir()) == []


def test_all_inputs_validate_before_first_provider(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)
    bad = json.loads((folder / "standard.json").read_text())
    bad["question"] = "tampered"
    evaluation.save(folder / "standard.json", bad)
    output = tmp_path / "result"
    with pytest.raises(GenerationError):
        evaluation.evaluate_directory(
            folder,
            output,
            Characters(),
            allow_api=True,
            provider_factory=lambda: pytest.fail("paid work before full validation"),
        )
    assert not output.exists()


def test_pair_exports_one_writer_per_artifact_and_unreviewed_semantics(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)
    providers = []

    def factory():
        p = Provider(candidate(artifact()), verification())
        providers.append(p)
        return p

    output = tmp_path / "result"
    report = evaluation.evaluate_directory(
        folder,
        output,
        Characters(),
        allow_api=True,
        compare_verification=True,
        workers=2,
        provider_factory=factory,
    )
    assert len(providers) == 2
    assert all(len(p.generated) == len(p.verified) == 1 for p in providers)
    assert report["real_provider"] is False
    records = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
    assert len(records) == 4
    assert report["results_sha256"] == evaluation.digest(output / "results.jsonl")
    for summary in report["summaries"].values():
        assert summary["semantic_support_rate"] is None
        assert summary["semantic_review_status"] == "unreviewed"
        assert summary["diagnostic_required_fact_coverage"] == 1.0
    assert (output / "report.md").exists()
    assert not list(tmp_path.glob(".generation-*"))


def record(*, failed=False):
    return dict(
        case_id="one",
        split="held_out",
        variant="standard",
        path="baseline",
        result=dict(
            execution_status="failed" if failed else "completed",
            status=None if failed else "answered",
            claims=[] if failed else [dict(id="c1", text="A misleading paraphrase")],
            citation_counts=dict(valid=1, total=1),
        ),
        diagnostic=dict(
            expected_status="answered",
            status_matches_label=not failed,
            lexical_fact_matches=1 if not failed else 0,
            required_facts=1,
            forbidden_pattern_matches=[],
        ),
    )


def test_lexical_match_does_not_establish_semantic_faithfulness():
    rows = [record()]
    ordinary = evaluation.summarize(rows)
    assert ordinary["held_out/standard/baseline"]["semantic_support_rate"] is None
    review = dict(
        results_sha256="fixed",
        reviewer="independent-reviewer",
        reviews=[
            dict(
                case_id="one",
                variant="standard",
                path="baseline",
                claims={"c1": False},
                complete_answer=False,
                appropriate_status=False,
            )
        ],
    )
    result = evaluation.summarize(rows, adjudication=review, results_sha256="fixed")
    assert result["held_out/standard/baseline"]["semantic_support_rate"] == 0
    assert result["held_out/standard/baseline"]["semantic_complete_answer_rate"] == 0


@pytest.mark.parametrize("damage", ["hash", "missing_review", "invented_claim", "duplicate_review"])
def test_independent_review_must_bind_exact_outputs_and_claims(damage):
    review = dict(
        results_sha256="fixed",
        reviewer="independent-reviewer",
        reviews=[
            dict(
                case_id="one",
                variant="standard",
                path="baseline",
                claims={"c1": True},
                complete_answer=True,
                appropriate_status=True,
            )
        ],
    )
    if damage == "hash":
        review["results_sha256"] = "changed"
    elif damage == "missing_review":
        review["reviews"] = []
    elif damage == "invented_claim":
        review["reviews"][0]["claims"] = {"other": True}
    else:
        review["reviews"].append(deepcopy(review["reviews"][0]))
    with pytest.raises(GenerationError):
        evaluation.summarize([record()], adjudication=review, results_sha256="fixed")


def test_technical_failure_remains_in_answerable_denominator():
    rows = [record(), record(failed=True)]
    rows[1]["case_id"] = "two"
    summary = evaluation.summarize(rows)["held_out/standard/baseline"]
    assert summary["cases"] == 2
    assert summary["technical_failures"] == 1
    assert summary["diagnostic_complete_answer"] == 0.5
    assert summary["diagnostic_required_fact_coverage"] == 0.5


def test_atomic_failed_export_removes_temporary_directory(tmp_path):
    def fail(directory):
        (directory / "partial.json").write_text("partial")
        raise RuntimeError("failed")

    output = tmp_path / "result"
    with pytest.raises(RuntimeError):
        evaluation.atomic_export(output, fail)
    assert not output.exists()
    assert not list(tmp_path.glob(".generation-*"))


@pytest.mark.parametrize("command", ["answer", "evaluate"])
def test_cli_paid_gate_precedes_tokenizer_and_outputs(tmp_path, monkeypatch, command):
    from studio_copilot.documents.generation import __main__ as cli

    monkeypatch.setattr(cli, "Tokenizer", lambda *a: pytest.fail("tokenizer before gate"))
    option = "--evidence-file" if command == "answer" else "--evidence-dir"
    assert cli.main([command, option, "missing", "--output-dir", str(tmp_path / "absent")]) == 1
    assert not (tmp_path / "absent").exists()


def test_paid_export_failure_preserves_flushed_records_and_incomplete_manifest(tmp_path):
    def fail(directory):
        evaluation.save(directory / "manifest.json", dict(complete=True))
        (directory / "reports.jsonl").write_text('{"calls": [{"input_tokens": 5}]}\n')
        raise RuntimeError("secret sentinel")

    output = tmp_path / "retained"
    with pytest.raises(RuntimeError):
        evaluation.atomic_export(output, fail, preserve_failure=True)
    assert (output / "reports.jsonl").exists()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["complete"] is False
    assert (output / "incomplete.json").exists()
    assert "secret sentinel" not in (output / "incomplete.json").read_text()


def test_status_only_verifier_downgrade_is_counted(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)
    providers = []

    def factory():
        output = Provider(candidate(artifact()), verification(status="partial"))
        providers.append(output)
        return output

    manifest = evaluation.evaluate_directory(
        folder,
        tmp_path / "result",
        Characters(),
        allow_api=True,
        compare_verification=True,
        provider_factory=factory,
    )
    assert manifest["paired_changes"]["removed_claims"] == 0
    assert manifest["paired_changes"]["status_only_downgrades"] == 2
    assert manifest["paired_changes"]["changed_cases"] == 2


def test_interruption_drains_completed_paid_reports_before_preserving_export(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)
    original = evaluation.as_completed

    def interrupted(futures):
        iterator = original(futures)
        yield next(iterator)
        raise KeyboardInterrupt

    monkeypatch.setattr(evaluation, "as_completed", interrupted)
    output = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        evaluation.evaluate_directory(
            folder,
            output,
            Characters(),
            allow_api=True,
            compare_verification=True,
            workers=2,
            provider_factory=lambda: Provider(candidate(artifact()), verification()),
        )
    rows = [json.loads(line) for line in (output / "reports.jsonl").read_text().splitlines()]
    assert rows
    assert all(row["baseline"]["execution_status"] == "completed" for row in rows)
    assert json.loads((output / "manifest.json").read_text())["complete"] is False
    assert (output / "incomplete.json").exists()


def test_required_fact_review_is_semantic_and_missing_judgments_remain_unknown():
    rows = [record()]
    base = dict(
        case_id="one",
        variant="standard",
        path="baseline",
        claims={"c1": True},
        complete_answer=False,
        appropriate_status=False,
    )
    review = dict(results_sha256="fixed", reviewer="independent", reviews=[base])
    result = evaluation.summarize(rows, adjudication=review, results_sha256="fixed")
    assert result["held_out/standard/baseline"]["semantic_required_fact_coverage"] is None
    base["required_facts"] = {"f1": False}
    result = evaluation.summarize(rows, adjudication=review, results_sha256="fixed")
    assert result["held_out/standard/baseline"]["semantic_required_fact_coverage"] == 0
    base["required_facts"] = {"invented": True}
    with pytest.raises(GenerationError):
        evaluation.summarize(rows, adjudication=review, results_sha256="fixed")


def test_unreviewed_quality_targets_are_unknown_not_passing():
    summary = evaluation.summarize([record()])["held_out/standard/baseline"]
    assert summary["quality_targets"]["passed"] is None


def test_cli_preserves_actionable_missing_tokenizer_error(tmp_path, monkeypatch, capsys):
    from studio_copilot.documents.generation import __main__ as cli

    def absent(*args):
        raise ValueError("Tokenizer asset is missing. Run --prepare-tokenizer first.")

    monkeypatch.setattr(cli, "Tokenizer", absent)
    assert cli.main(["plan", "--evidence-dir", str(tmp_path)]) == 1
    error = capsys.readouterr().err
    assert "tokenizer" in error
    assert "--prepare-tokenizer" in error


def test_single_answer_report_includes_original_citations_and_escaped_source_text(
    tmp_path, monkeypatch
):
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    evidence_file = tmp_path / "evidence.json"
    evaluation.save(evidence_file, value)
    result = answer(value, Characters(), allow_api=True, provider=Provider(candidate(value)))
    result["answer"] += " <script>alert(1)</script> [link](javascript:bad)"
    monkeypatch.setattr(evaluation, "answer", lambda *args, **kwargs: result)
    output = tmp_path / "answer"
    evaluation.answer_directory(evidence_file, output, Characters(), allow_api=True)
    report = (output / "answer.md").read_text()
    assert "Exception: no fee." in report
    assert "revision 1" in report
    assert value["sources"][0]["sha256"] in report
    assert "Metadata missing_information" in report
    assert "<script>" not in report
    assert "&lt;script&gt;" in report
    assert "[link](javascript:bad)" not in report


def test_factually_complete_partial_answer_does_not_count_as_complete_output():
    rows = [record()]
    rows[0]["result"]["status"] = "partial"
    review = dict(
        results_sha256="fixed",
        reviewer="independent",
        reviews=[
            dict(
                case_id="one",
                variant="standard",
                path="baseline",
                claims={"c1": True},
                required_facts={"f1": True},
                complete_answer=True,
                appropriate_status=False,
            )
        ],
    )
    result = evaluation.summarize(rows, adjudication=review, results_sha256="fixed")
    summary = result["held_out/standard/baseline"]
    assert summary["semantic_factual_completeness_rate"] == 1.0
    assert summary["semantic_complete_answer_rate"] == 0
    assert summary["semantic_complete_answer_counts"] == dict(complete=0, total=1)


def test_failed_single_answer_exports_failure_and_cli_exits_nonzero(tmp_path, monkeypatch):
    from studio_copilot.documents.generation import __main__ as cli
    from studio_copilot.documents.generation.engine import answer as engine_answer

    class Failed(Provider):
        def generate(self, payload):
            raise RuntimeError("secret sentinel")

    value = artifact()
    evidence_file = tmp_path / "evidence.json"
    evaluation.save(evidence_file, value)
    monkeypatch.setattr(cli, "Tokenizer", lambda *args: Characters())
    monkeypatch.setattr(
        evaluation,
        "answer",
        lambda value, tokenizer, **kwargs: engine_answer(
            value, tokenizer, allow_api=True, provider=Failed(None)
        ),
    )
    output = tmp_path / "failure"
    assert (
        cli.main(
            [
                "answer",
                "--evidence-file",
                str(evidence_file),
                "--output-dir",
                str(output),
                "--allow-api",
            ]
        )
        == 1
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["complete"] is True
    assert manifest["execution_status"] == "failed"
    assert manifest["technical_failures"] == 1
    result = json.loads((output / "answer.json").read_text())
    assert result["answer"] == ""
    assert result["claims"] == []
    assert "secret sentinel" not in (output / "answer.json").read_text()


def test_evaluation_technical_failures_produce_nonzero_cli_exit(tmp_path, monkeypatch):
    from studio_copilot.documents.generation import __main__ as cli

    monkeypatch.setattr(cli, "Tokenizer", lambda *args: Characters())
    monkeypatch.setattr(
        cli,
        "evaluate_directory",
        lambda *args, **kwargs: dict(
            complete=True, technical_failures=1, execution_status="failed"
        ),
    )
    assert (
        cli.main(
            [
                "evaluate",
                "--evidence-dir",
                "missing",
                "--output-dir",
                str(tmp_path / "output"),
                "--allow-api",
            ]
        )
        == 1
    )


def test_business_abstention_is_successful_cli_execution(tmp_path, monkeypatch):
    from studio_copilot.documents.generation import __main__ as cli

    value = artifact(blocks=False)
    evidence_file = tmp_path / "evidence.json"
    evaluation.save(evidence_file, value)
    monkeypatch.setattr(cli, "Tokenizer", lambda *args: Characters())
    output = tmp_path / "abstained"
    assert (
        cli.main(
            [
                "answer",
                "--evidence-file",
                str(evidence_file),
                "--output-dir",
                str(output),
                "--allow-api",
            ]
        )
        == 0
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["execution_status"] == "completed"
    assert manifest["technical_failures"] == 0


def test_answer_markdown_write_failure_retains_paid_json_and_usage(tmp_path, monkeypatch):
    from pathlib import Path

    from studio_copilot.documents.generation.engine import answer as engine_answer

    value = artifact()
    evidence_file = tmp_path / "evidence.json"
    evaluation.save(evidence_file, value)
    result = engine_answer(value, Characters(), allow_api=True, provider=Provider(candidate(value)))
    result["calls"] = [dict(input_tokens=17, output_tokens=9)]
    monkeypatch.setattr(evaluation, "answer", lambda *args, **kwargs: result)
    original = Path.write_text

    def failing(path, *args, **kwargs):
        if path.name == "answer.md":
            raise OSError("disk error")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing)
    output = tmp_path / "retained"
    with pytest.raises(OSError):
        evaluation.answer_directory(evidence_file, output, Characters(), allow_api=True)
    stored = json.loads((output / "answer.json").read_text())
    assert stored["calls"] == [dict(input_tokens=17, output_tokens=9)]
    assert json.loads((output / "manifest.json").read_text())["complete"] is False


def test_generated_invalid_quote_does_not_remain_in_final_citation_metric(tmp_path, monkeypatch):
    folder = evidence_set(tmp_path, monkeypatch)

    def factory():
        output = candidate(artifact())
        invalid = output.claims[0].model_copy(deep=True)
        invalid.id = "invalid"
        invalid.citations[0].quote = "fabricated quote"
        output.claims.append(invalid)
        return Provider(output)

    manifest = evaluation.evaluate_directory(
        folder, tmp_path / "result", Characters(), allow_api=True, provider_factory=factory
    )
    summary = manifest["summaries"]["tuning/actual/baseline"]
    assert summary["citation_validity"] == summary["generated_citation_validity"] == 0.5
    assert summary["generated_citation_counts"] == dict(valid=1, total=2)
    assert summary["final_citation_validity"] == 1.0
    assert summary["final_citation_counts"] == dict(valid=1, total=1, invalid=0)
