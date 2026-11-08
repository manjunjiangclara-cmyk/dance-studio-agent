"""SDK contract checks use an injected client; no hosted requests are made."""

import json
from types import SimpleNamespace

import pytest

from studio_copilot.documents.generation.contracts import Candidate, GenerationError
from studio_copilot.documents.generation.provider import GenerationProvider


def parsed_candidate():
    return Candidate.model_validate(
        dict(status="abstained", claims=[], missing_information=[], reason_code="no_evidence")
    )


class Responses:
    def __init__(self, response=None, failure=None):
        self.response = response
        self.failure = failure
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return self.response


def client(*, status="completed", parsed=True, failure=None):
    response = SimpleNamespace(
        status=status,
        output_parsed=parsed_candidate() if parsed else None,
        usage=SimpleNamespace(input_tokens=17, output_tokens=9),
    )
    return SimpleNamespace(responses=Responses(response, failure))


def test_structured_request_disables_storage_and_has_no_tools_or_hidden_retry():
    sdk = client()
    provider = GenerationProvider(client=sdk, model="fixture-model")
    result = provider.generate(dict(question="Café 中文🙂?", evidence=[]))
    assert result.status == "abstained"
    assert len(sdk.responses.calls) == 1
    call = sdk.responses.calls[0]
    assert call["model"] == "fixture-model"
    assert call["store"] is False
    assert call["text_format"] is Candidate
    assert "tools" not in call
    assert json.loads(call["input"])["question"] == "Café 中文🙂?"
    assert provider.real_provider is False
    assert provider.calls[0]["input_tokens"] == 17
    assert provider.calls[0]["output_tokens"] == 9
    assert provider.calls[0]["succeeded"] is True


@pytest.mark.parametrize(
    ("status", "parsed", "expected"),
    [("incomplete", True, "incomplete_response"), ("completed", False, "model_refusal")],
)
def test_refusal_or_truncation_retains_usage_and_is_not_business_abstention(
    status, parsed, expected
):
    sdk = client(status=status, parsed=parsed)
    provider = GenerationProvider(client=sdk, model="fixture-model")
    with pytest.raises(GenerationError) as caught:
        provider.generate(dict(question="What?", evidence=[]))
    assert caught.value.code == expected
    assert len(sdk.responses.calls) == 1
    assert provider.calls[0]["input_tokens"] == 17
    assert provider.calls[0]["output_tokens"] == 9
    assert provider.calls[0]["succeeded"] is False
    assert provider.calls[0]["seconds"] >= 0


def test_transport_error_is_sanitized_and_never_retried():
    sdk = client(failure=RuntimeError("credential-secret-sentinel"))
    provider = GenerationProvider(client=sdk, model="fixture-model")
    with pytest.raises(GenerationError) as caught:
        provider.generate(dict(question="What?", evidence=[]))
    assert caught.value.code == "provider_error"
    assert "credential-secret-sentinel" not in str(caught.value)
    assert len(sdk.responses.calls) == 1
    assert provider.calls[0]["input_tokens"] is None
    assert provider.calls[0]["succeeded"] is False


def test_real_client_construction_disables_sdk_retries(monkeypatch):
    from studio_copilot.documents.generation import provider as module

    constructed = []
    sdk = client()
    monkeypatch.setenv("OPENAI_API_KEY", "never-printed-fake-key")
    monkeypatch.setenv("OPENAI_MODEL", "fixture-model")

    def make_client(**kwargs):
        constructed.append(kwargs)
        return sdk

    monkeypatch.setattr(module, "OpenAI", make_client)
    model = module.GenerationProvider()
    assert constructed == [dict(timeout=30.0, max_retries=0)]
    assert model.model == "fixture-model"
    assert sdk.responses.calls == []
