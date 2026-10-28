"""CLI listing and failed runs must remain safe without a model or database."""

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from workflow_evaluations import evaluate


def test_list_never_constructs_a_database_or_model(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Listing scenarios must not construct a database or model.")

    monkeypatch.setattr(evaluate, "isolated_database", forbidden)
    monkeypatch.setattr(evaluate, "MeasuredModel", forbidden)
    monkeypatch.setattr(evaluate, "validate_database_url", forbidden)
    assert evaluate.main(["--list", "--case", "makeup_approval"]) == 0
    output = capsys.readouterr().out
    assert "makeup_approval:" in output
    assert "followup_correction:" not in output


def test_live_calls_require_explicit_opt_in(capsys):
    with pytest.raises(SystemExit) as error:
        evaluate.main([])
    assert error.value.code == 2
    assert "--live" in capsys.readouterr().err


def test_unknown_case_is_rejected_before_live_setup(capsys):
    with pytest.raises(SystemExit) as error:
        evaluate.main(["--live", "--case", "not_a_case"])
    assert error.value.code == 2
    assert "Unknown scenario IDs" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--repeat", "--max-calls-per-case"])
def test_zero_limits_are_rejected(flag):
    with pytest.raises(SystemExit) as error:
        evaluate.main(["--list", flag, "0"])
    assert error.value.code == 2


def test_failed_case_closes_client_cleans_context_and_writes_safe_report(
    monkeypatch,
    tmp_path,
    capsys,
):
    events = []

    @contextmanager
    def isolated(url):
        events.append("database_opened")
        try:
            yield object()
        finally:
            events.append("database_cleaned")

    def model(max_calls):
        events.append("model_created")
        return SimpleNamespace(client=SimpleNamespace(close=lambda: events.append("model_closed")))

    def failing_case(*args):
        raise RuntimeError("synthetic-provider-secret")

    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://localhost/evaluations_test")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-model")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-unit-test-key")
    monkeypatch.setattr(evaluate, "isolated_database", isolated)
    monkeypatch.setattr(evaluate, "MeasuredModel", model)
    monkeypatch.setattr(evaluate, "run_scenario", failing_case)
    output = tmp_path / "report.json"
    exit_code = evaluate.main(["--live", "--case", "makeup_approval", "--output", str(output)])
    assert exit_code == 1
    assert events == ["database_opened", "model_created", "database_cleaned", "model_closed"]
    report = json.loads(output.read_text())
    assert report["passed"] == 0
    assert report["total"] == 1
    assert report["results"][0]["error_type"] == "RuntimeError"
    assert "synthetic-provider-secret" not in output.read_text() + capsys.readouterr().out
