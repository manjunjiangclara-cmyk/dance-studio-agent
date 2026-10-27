"""Live evaluation budgets and target guards cannot silently pass after fallback."""

import json
from types import SimpleNamespace

import pytest

from evaluations.cases import load_scenarios
from evaluations.fixtures import validate_database_url
from evaluations.model import MeasuredModel
from evaluations.runner import run_scenario
from studio_copilot.agent.contracts import ModelError
from studio_copilot.agent.openai_model import OpenAIModel


@pytest.mark.parametrize(
    "url",
    [
        None,
        "not-a-url",
        "sqlite:///studio_test",
        "postgresql+psycopg://localhost/studio",
        "postgresql+psycopg://localhost/studio_test?options=-csearch_path=public",
    ],
)
def test_database_guard_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        validate_database_url(url)


def measured(monkeypatch):
    monkeypatch.setattr(OpenAIModel, "__init__", lambda self: None)
    return MeasuredModel(max_calls=1)


def test_budget_prevents_another_request(monkeypatch):
    model = measured(monkeypatch)
    calls = []

    def request(self, operation, **kwargs):
        calls.append(operation)
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=10, output_tokens=3))

    monkeypatch.setattr(OpenAIModel, "_request", request)
    model._request(json.loads)
    with pytest.raises(ModelError, match="budget"):
        model._request(json.loads)
    assert len(calls) == 1
    assert model.exhausted
    assert model.calls[0]["input_tokens"] == 10


def test_completed_response_with_no_parsed_output_is_a_model_failure(monkeypatch):
    model = measured(monkeypatch)
    model.model = "synthetic-model"
    model.client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=lambda **kw: SimpleNamespace(status="completed", output_parsed=None, usage=None)
        )
    )
    monkeypatch.setattr(
        model, "_privacy_for", lambda context: SimpleNamespace(redact=lambda value: value)
    )
    with pytest.raises(ModelError, match="declined"):
        model.route({})
    assert model.calls[0]["completed"]
    assert model.failures == ["route"]


def test_fallback_cannot_hide_a_failed_request_or_exhausted_budget(monkeypatch):
    model = measured(monkeypatch)
    model.calls = [{"completed": False, "operation": "synthetic"}]
    model.failures = ["draft"]
    model.exhausted = True

    def unavailable(*args):
        raise RuntimeError("synthetic-secret-must-not-appear")

    monkeypatch.setattr("evaluations.runner.seed_studio", unavailable)
    result = run_scenario(None, load_scenarios()[0], model)
    assert not result["passed"]
    failed = {c["name"] for c in result["checks"] if not c["passed"]}
    assert {
        "all_model_calls_completed",
        "within_model_call_budget",
        "all_model_steps_succeeded",
    } <= failed
    assert "synthetic-secret-must-not-appear" not in json.dumps(result)
