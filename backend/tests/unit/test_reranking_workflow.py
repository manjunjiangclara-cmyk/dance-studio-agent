"""Independent artifact, CLI, and selection workflow checks; no models or API calls."""

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from studio_copilot.documents.reranking.runtime import MODELS, RerankError, digest


def small_case(identifier, split="tuning"):
    return dict(
        id=identifier,
        split=split,
        query="Question?",
        as_of="2027-06-01",
        answerable=True,
        expected_empty=False,
        evidence=[dict(document_key="policy", start=0, end=3)],
        tags=[],
    )


def artifact(tmp_path, monkeypatch):
    from studio_copilot.documents.reranking import artifacts

    folder = tmp_path / "capture"
    folder.mkdir()
    dataset = dict(source_sha256="dataset-fixed", cases=[small_case("one")], notes=[], documents=[])
    snapshot = dict(candidates=[], parents={}, degraded=False)
    records = folder / "candidates.jsonl"
    records.write_text(json.dumps(dict(case_id="one", snapshot=snapshot)) + "\n")
    manifest = dict(
        complete=True,
        schema_cleaned=True,
        dataset_sha256=dataset["source_sha256"],
        records_sha256=digest(records),
        cases=1,
        real_openai=False,
    )
    (folder / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(artifacts, "load_dataset", lambda: dataset)
    return folder, manifest, dataset


@pytest.mark.parametrize("damage", ["checksum", "incomplete", "uncleaned", "dataset", "count"])
def test_corrupt_capture_is_rejected_before_any_model_verification(tmp_path, monkeypatch, damage):
    from studio_copilot.documents.reranking import compare

    folder, manifest, _ = artifact(tmp_path, monkeypatch)
    if damage == "checksum":
        (folder / "candidates.jsonl").write_text("changed")
    else:
        key, value = {
            "incomplete": ("complete", False),
            "uncleaned": ("schema_cleaned", False),
            "dataset": ("dataset_sha256", "other-dataset"),
            "count": ("cases", 2),
        }[damage]
        manifest[key] = value
        (folder / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(compare, "verify_model", lambda *a: pytest.fail("Model touched"))
    output = tmp_path / "must-not-exist"
    with pytest.raises(RerankError):
        compare.compare_directory(folder, tmp_path / "cache", output, tmp_path / "tokenizer")
    assert not output.exists()


@pytest.mark.parametrize("command", ["capture", "prepare-models"])
def test_cli_opt_in_gates_precede_tokenizer_database_and_cache(tmp_path, monkeypatch, command):
    from studio_copilot.documents.reranking import __main__ as cli

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TEST_DATABASE_URL", "invalid://secret-sentinel")
    monkeypatch.setattr(cli, "Tokenizer", lambda *a: pytest.fail("Tokenizer touched before gate"))
    output = tmp_path / "must-not-exist"
    if command == "capture":
        args = ["capture", "--output-dir", str(output), "--tokenizer-cache", str(output)]
    else:
        args = ["prepare-models", "--model-cache", str(output)]
    assert cli.main(args) == 1
    assert not output.exists()


def worker_args(tmp_path, **kwargs):
    return SimpleNamespace(
        capture_dir=tmp_path / "capture",
        model_cache=tmp_path / "cache",
        model_id=MODELS[0],
        phase="fresh",
        tokenizer_cache=tmp_path / "tokenizer",
        output=tmp_path / "result.json",
        selection_file=tmp_path / "selection.json",
        selection_hash=kwargs.get("selection_hash"),
    )


@pytest.mark.parametrize("damage", ["hash", "model", "revision", "capture", "dataset"])
def test_fresh_worker_rejects_mismatched_frozen_selection_before_loading_model(
    tmp_path, monkeypatch, damage
):
    from studio_copilot.documents.reranking import worker

    args = worker_args(tmp_path)
    manifest = dict(records_sha256="records-fixed", dataset_sha256="dataset-fixed")
    monkeypatch.setattr(worker, "load_capture", lambda *a: (manifest, dict(cases=[])))
    monkeypatch.setattr(worker, "verify_model", lambda *a: dict(revision="a" * 40))
    monkeypatch.setattr(worker, "Tokenizer", lambda *a: pytest.fail("Tokenizer touched"))
    monkeypatch.setattr(worker, "LocalReranker", lambda *a: pytest.fail("Model loaded"))
    selection = dict(
        model_id=MODELS[0],
        revision="a" * 40,
        records_sha256="records-fixed",
        dataset_sha256="dataset-fixed",
    )
    if damage != "hash":
        key = {
            "model": "model_id",
            "revision": "revision",
            "capture": "records_sha256",
            "dataset": "dataset_sha256",
        }[damage]
        selection[key] = "wrong"
    args.selection_file.write_text(json.dumps(selection))
    args.selection_hash = "wrong" if damage == "hash" else digest(args.selection_file)
    with pytest.raises(RerankError) as caught:
        worker.run(args)
    assert caught.value.code == "invalid_selection"
    assert not args.output.exists()


def model_report(complete=True, all_evidence=1.0):
    summary = dict(
        final_at_6=dict(all_evidence=all_evidence, recall=1.0, reciprocal_rank=1.0),
        multi_source_all_evidence=None,
        failed=0,
        date_exclusion_checks_pass=True,
        rerank_latency=dict(p95=0.1),
    )
    return dict(
        complete=complete,
        real_local_model=False,
        summaries=dict(
            tuning=deepcopy(summary),
            diagnostic=deepcopy(summary),
            fresh_validation=deepcopy(summary),
        ),
        cases=[],
    )


def test_selection_ignores_diagnostic_quality_and_ties_prefer_l6():
    from studio_copilot.documents.reranking.compare import select_model

    reports = {model: model_report() for model in MODELS}
    reports[MODELS[0]]["summaries"]["diagnostic"]["final_at_6"]["all_evidence"] = 0
    assert select_model(reports) == MODELS[0]
    reports[MODELS[1]]["summaries"]["tuning"]["final_at_6"]["all_evidence"] = 0.9
    assert select_model(reports) == MODELS[0]


def setup_comparison(tmp_path, monkeypatch):
    from studio_copilot.documents.reranking import compare

    manifest = dict(
        records_sha256="records-fixed", dataset_sha256="dataset-fixed", real_openai=False
    )
    dataset = dict(notes=[], cases=[])
    monkeypatch.setattr(compare, "load_capture", lambda *a: (manifest, dataset))
    monkeypatch.setattr(compare, "verify_model", lambda *a: dict(revision="a" * 40))
    monkeypatch.setattr(compare, "Tokenizer", lambda *a: SimpleNamespace(count=len))

    # A minimal real-shaped baseline supplies fresh validation summary/adoption inputs.
    def records(*args, fresh=False):
        if fresh:
            yield small_case("fresh", "fresh_validation"), dict(candidates=[], parents={})

    monkeypatch.setattr(compare, "records", records)
    return compare, tmp_path / "output"


def test_selection_is_saved_and_hashable_before_any_fresh_worker(tmp_path, monkeypatch):
    compare, output = setup_comparison(tmp_path, monkeypatch)
    order = []

    def phase(capture, cache, tokenizer, target, model_id, phase, selection=None):
        order.append((phase, model_id))
        report = model_report()
        if phase == "fresh":
            assert selection == output / "selection.json"
            frozen = json.loads(selection.read_text())
            assert digest(selection)
            assert frozen["model_id"] == model_id == MODELS[0]
            assert frozen["revision"] == "a" * 40
            assert frozen["records_sha256"] == "records-fixed"
            assert frozen["dataset_sha256"] == "dataset-fixed"
            assert frozen["gates"]["complete_evidence_gain"] == 0.025
            assert frozen["tuning_report_hashes"] == {
                model: digest(output / (model.split("/")[1] + "-development.json"))
                for model in MODELS
            }
        target.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(compare, "run_phase", phase)
    report = compare.compare_directory(tmp_path / "capture", tmp_path / "cache", output, tmp_path)
    assert order == [("development", MODELS[0]), ("development", MODELS[1]), ("fresh", MODELS[0])]
    assert report["complete"] is True, report
    assert report["semantic_quality_measured"] is False
    assert report["adoption"]["recommended"] is False


def test_worker_failure_retains_partial_report_and_never_claims_success(tmp_path, monkeypatch):
    compare, output = setup_comparison(tmp_path, monkeypatch)

    def phase(capture, cache, tokenizer, target, model_id, phase, selection=None):
        if model_id == MODELS[1]:
            raise RerankError("worker_failed", "sensitive diagnostic")
        report = model_report()
        target.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(compare, "run_phase", phase)
    report = compare.compare_directory(tmp_path / "capture", tmp_path / "cache", output, tmp_path)
    persisted = json.loads((output / "comparison.json").read_text())
    assert persisted == report
    assert report["complete"] is False
    assert report["semantic_quality_measured"] is False
    assert report["error_code"] == "worker_failed"
    assert MODELS[0] in report["models"]
    assert "sensitive diagnostic" not in json.dumps(report)
    assert not (output / "selection.json").exists()


@pytest.mark.parametrize("damage", ["truncated", "order", "degraded", "too_many", "extra_record"])
def test_checksummed_but_structurally_invalid_capture_fails_before_models(
    tmp_path, monkeypatch, damage
):
    from studio_copilot.documents.reranking import compare

    folder, manifest, _ = artifact(tmp_path, monkeypatch)
    record = dict(case_id="one", snapshot=dict(candidates=[], parents={}, degraded=False))
    if damage == "truncated":
        raw = ""
    else:
        if damage == "order":
            record["case_id"] = "different-case"
        elif damage == "degraded":
            record["snapshot"]["degraded"] = True
        elif damage == "too_many":
            record["snapshot"]["candidates"] = [{}] * 41
        raw = json.dumps(record) + "\n"
        if damage == "extra_record":
            raw += json.dumps(record) + "\n"
    (folder / "candidates.jsonl").write_text(raw)
    manifest["records_sha256"] = digest(folder / "candidates.jsonl")
    (folder / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(compare, "verify_model", lambda *a: pytest.fail("Model touched"))
    with pytest.raises(RerankError) as caught:
        compare.compare_directory(folder, tmp_path / "cache", tmp_path / "output", tmp_path)
    assert caught.value.code == "invalid_capture"


@pytest.mark.parametrize(
    "damage", ["text", "duplicate", "expired", "references", "range", "parent"]
)
def test_snapshot_validation_rejects_wrong_text_sources_ranges_or_parent_sets(
    tmp_path, monkeypatch, damage
):
    import hashlib

    from studio_copilot.documents.reranking.artifacts import load_capture

    folder, manifest, dataset = artifact(tmp_path, monkeypatch)
    dataset["documents"] = [
        dict(
            key="policy",
            text="abc",
            effective_from="2027-01-01",
            effective_to="2027-12-31",
        )
    ]
    candidate = dict(
        document_key="policy",
        revision=1,
        effective_from="2027-01-01",
        effective_to="2027-12-31",
        run_id="run",
        chunk_id="chunk",
        parent_id=None,
        text="abc",
        text_sha256=hashlib.sha256(b"abc").hexdigest(),
        source_spans=[dict(start=0, end=3)],
        other_sources=[],
    )
    snapshot = dict(candidates=[candidate], parents={}, degraded=False)
    if damage == "text":
        candidate["text"] = "altered"
    elif damage == "duplicate":
        snapshot["candidates"].append(deepcopy(candidate))
    elif damage == "expired":
        dataset["documents"][0]["effective_to"] = "2026-12-31"
    elif damage == "references":
        candidate["other_sources"] = [deepcopy(candidate)] * 4
    elif damage == "range":
        candidate["source_spans"][0]["end"] = 4
    else:
        snapshot["parents"] = {"unexpected-parent": {}}
    path = folder / "candidates.jsonl"
    path.write_text(json.dumps(dict(case_id="one", snapshot=snapshot)) + "\n")
    manifest["records_sha256"] = digest(path)
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(RerankError) as caught:
        load_capture(folder)
    assert caught.value.code == "invalid_capture"


def test_offline_worker_process_receives_no_provider_or_database_credentials(tmp_path, monkeypatch):
    from studio_copilot.documents.reranking import compare

    monkeypatch.setenv("OPENAI_API_KEY", "do-not-forward")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://private.invalid/v1")
    monkeypatch.setenv("DATABASE_URL", "private-database")
    monkeypatch.setenv("TEST_DATABASE_URL", "private-test-database")
    output = tmp_path / "report.json"

    def subprocess_run(command, *, env, **kwargs):
        assert not any(name.startswith("OPENAI_") for name in env)
        assert "DATABASE_URL" not in env and "TEST_DATABASE_URL" not in env
        assert env["HF_HUB_OFFLINE"] == env["TRANSFORMERS_OFFLINE"] == "1"
        assert env["HF_HUB_DISABLE_TELEMETRY"] == "1"
        output.write_text(json.dumps(dict(complete=False)))
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(compare.subprocess, "run", subprocess_run)
    report = compare.run_phase(tmp_path, tmp_path, tmp_path, output, MODELS[0], "development")
    assert report["complete"] is False


def test_importing_ordinary_cli_does_not_import_optional_neural_packages():
    import subprocess
    import sys

    code = (
        "import sys; import studio_copilot.documents.reranking.__main__; "
        "assert 'torch' not in sys.modules; "
        "assert 'transformers' not in sys.modules; "
        "assert 'huggingface_hub' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stderr


def test_worker_model_load_failure_saves_explicit_failed_cases(tmp_path, monkeypatch):
    from studio_copilot.documents.reranking import worker

    args = worker_args(tmp_path)
    args.phase = "development"
    case = small_case("one")
    candidate = dict(
        text="abc",
        text_sha256="a" * 64,
        run_id="run",
        chunk_id="chunk",
        parent_id=None,
        document_key="policy",
        source_spans=[dict(start=0, end=3)],
        prefix="",
        other_sources=[],
    )
    monkeypatch.setattr(worker, "load_capture", lambda *a: ({}, dict(cases=[case])))
    monkeypatch.setattr(worker, "verify_model", lambda *a: dict(revision="a" * 40))
    monkeypatch.setattr(worker, "Tokenizer", lambda *a: SimpleNamespace(count=len))
    monkeypatch.setattr(
        worker,
        "records",
        lambda *a, **kw: iter(
            [
                (case, dict(candidates=[candidate], parents={})),
            ]
        ),
    )

    def unavailable(*args):
        raise RuntimeError("private model load traceback")

    monkeypatch.setattr(worker, "LocalReranker", unavailable)
    assert worker.run(args) == 1
    report = json.loads(args.output.read_text())
    assert report["complete"] is False
    assert report["real_local_model"] is False
    assert report["summaries"]["tuning"]["answerable"] == 1
    assert report["summaries"]["tuning"]["failed"] == 1
    assert report["summaries"]["tuning"]["final_at_6"]["recall"] == 0
    assert report["cases"][0]["error_code"] == "model_load_failed"
    assert "private model load" not in json.dumps(report)
