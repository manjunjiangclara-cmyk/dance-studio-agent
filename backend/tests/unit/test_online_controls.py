"""Admission, task limits and privacy for online document orchestration; no network."""

from contextlib import nullcontext
from uuid import UUID

import pytest

from studio_copilot.documents import online
from studio_copilot.documents.operations import current
from tests.unit.test_online_review import config, state


def test_disabled_and_makeup_never_initialize_resources(monkeypatch):
    monkeypatch.delenv("STUDIO_DOCUMENT_ANSWERS", raising=False)
    monkeypatch.setattr(online, "resources", lambda *args: pytest.fail("loaded model"))
    assert online.gather(None, state()) is None
    value = state()
    value["flow"] = "makeup"
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    assert online.gather(None, value) is None


@pytest.mark.parametrize(
    "value", ["", "bad", "one,two", ",", str(UUID(int=1)) + "," + str(UUID(int=1))]
)
def test_enabled_configuration_requires_valid_explicit_unique_runs(value, monkeypatch):
    monkeypatch.setenv("STUDIO_DOCUMENT_ANSWERS", "true")
    monkeypatch.setenv("STUDIO_DOCUMENT_RUN_IDS", value)
    monkeypatch.setenv("STUDIO_TOKENIZER_CACHE", "/fake")
    monkeypatch.setenv("STUDIO_RERANKER_CACHE", "/fake")
    with pytest.raises(online.OnlineError):
        online.Configuration.from_env()


def test_request_limits_and_sensitive_failures_are_shared_across_questions(monkeypatch, caplog):
    value = state(10)
    monkeypatch.setattr(online, "Session", lambda *args: nullcontext(object()))
    monkeypatch.setattr(online, "source_rows", lambda *args: [])
    attempts, controls = [], []

    def request(*args, **kwargs):
        control = current()
        controls.append(control)
        attempts.append(True)
        ticket = control.budget.reserve(1, 4000)
        ticket.mark_sent()
        ticket.finish(1, 1)
        raise RuntimeError("PRIVATE_PROVIDER_EXCEPTION")

    monkeypatch.setattr(online, "question_answer", request)
    gathered = online.gather(None, value, config=config(), tokenizer=object(), reranker=object())
    assert len(attempts) == 8
    assert len({id(control) for control in controls}) == 1
    assert len(gathered["evidence"]) == 10
    operations = gathered["evidence"][-1]["result"]["operations"]
    assert operations["attempts"] == 8
    assert "PRIVATE_PROVIDER_EXCEPTION" not in str(gathered) + caplog.text
    assert all(item["result"]["status"] == "failed" for item in gathered["evidence"])


def test_resolved_questions_need_no_resources_and_no_model(monkeypatch):
    value = state(1)
    value["question_resolutions"] = [
        dict(question_id=next(iter(value["interpretation"]["question_ids"].values())))
    ]
    monkeypatch.setattr(online, "resources", lambda *args: pytest.fail("loaded resources"))
    monkeypatch.setattr(online, "question_answer", lambda *args: pytest.fail("made paid request"))
    assert online.gather(None, value, config=config())["evidence"] == []


def test_only_query_identity_is_pseudonymized_and_no_raw_question_is_logged(monkeypatch, caplog):
    value = state(1)
    value["context"]["student"] = dict(name="Private Student", email="private@example.test")
    question = "Private Student asks about private@example.test"
    value["interpretation"]["questions"] = [question]
    value["interpretation"]["question_ids"] = {question: str(UUID(int=1))}
    monkeypatch.setattr(online, "Session", lambda *args: nullcontext(object()))
    monkeypatch.setattr(online, "source_rows", lambda *args: [])
    received = []

    def request(engine, selected, redacted, *args, **kwargs):
        received.append(redacted)
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr(online, "question_answer", request)
    result = online.gather(None, value, config=config(), tokenizer=object(), reranker=object())
    assert "Private Student" not in received[0] and "private@example.test" not in received[0]
    assert result["evidence"][0]["result"]["question"] == question  # Controlled review artifact.
    assert question not in caplog.text


def test_budget_exhaustion_stops_remaining_questions_without_semantic_fallback(monkeypatch):
    value = state(8)
    monkeypatch.setattr(online, "Session", lambda *args: nullcontext(object()))
    monkeypatch.setattr(online, "source_rows", lambda *args: [])
    attempted, sent = [], []

    def request(*args, **kwargs):
        attempted.append(True)
        ticket = current().budget.reserve(250_000, 0)
        sent.append(True)
        ticket.mark_sent()
        ticket.finish()  # Usage unknown; reservation is not refunded.
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr(online, "question_answer", request)
    gathered = online.gather(None, value, config=config(), tokenizer=object(), reranker=object())
    assert len(sent) == 4 and len(attempted) == 5
    results = [item["result"] for item in gathered["evidence"]]
    assert all(item["status"] == "failed" for item in results)
    assert all(item["error_code"] == "budget_exceeded" for item in results[4:])
    assert results[-1]["operations"]["unknown_usage_calls"] == 4


def test_owned_sdk_clients_are_lazy_reused_and_closed_on_failure(monkeypatch):
    from types import SimpleNamespace

    created, closed = [], []

    class Embeddings:
        def __init__(self, profile):
            created.append("embedding")
            self.client = SimpleNamespace(close=lambda: closed.append("embedding"))

        def embed(self, texts):
            return texts

    class Generation:
        def __init__(self):
            created.append("generation")
            self.client = SimpleNamespace(close=lambda: closed.append("generation"))
            self.calls = []

        def generate(self, payload):
            raise RuntimeError("fake failure")

    monkeypatch.setattr(online, "Embedder", Embeddings)
    monkeypatch.setattr(online, "GenerationProvider", Generation)
    with online.providers(None, None):
        assert created == []
    with pytest.raises(RuntimeError):
        with online.providers(None, None) as (embedder, writer):
            embedder.embed(["first"])
            embedder.embed(["second"])
            writer.generate({})
    assert created == closed == ["embedding", "generation"]
