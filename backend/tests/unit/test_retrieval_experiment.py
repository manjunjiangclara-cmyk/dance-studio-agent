"""Offline estimates, explicit API gates and invocation-local vector reuse."""

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingError, EmbeddingProfile
from studio_copilot.documents.retrieval import experiment
from studio_copilot.documents.retrieval.engine import RetrievalError

CASES = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_cases.json"


@pytest.fixture
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


def vector():
    return [1.0] + [0.0] * 1535


class Fake:
    def __init__(self):
        self.calls = 0

    def embed(self, texts, before_attempt=lambda: None):
        self.calls += 1
        before_attempt()
        return [vector() for _ in texts], 7


def test_plan_needs_no_db_provider_or_key(tokenizer, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(experiment, "make_engine", lambda: pytest.fail("DB accessed"))
    monkeypatch.setattr(experiment, "Embedder", lambda *a: pytest.fail("Provider created"))
    result = experiment.plan(CASES, tokenizer, EmbeddingProfile())
    assert result["dry_run"]
    assert result["cases"] == 40 and result["splits"] == {"tuning": 20, "held_out": 20}
    assert result["unique_question_requests"] == 38
    assert result["fresh_document_unique_inputs"] > 0
    assert result["fresh_document_estimated_tokens"] > 0


@pytest.mark.parametrize("command", ["prepare", "compare"])
def test_cli_permission_gate_precedes_tokenizer_database_and_provider(command, monkeypatch, capsys):
    monkeypatch.setattr(experiment, "Tokenizer", lambda *a: pytest.fail("Tokenizer constructed"))
    monkeypatch.setattr(experiment, "make_engine", lambda: pytest.fail("DB accessed"))
    args = [command, "--cases", str(CASES)]
    if command == "compare":
        args += ["--run-id", str(uuid4())]
    assert experiment.main(args) == 1
    assert "api_permission" in capsys.readouterr().err


def test_cli_plan_is_read_only_and_emits_manifest(tokenizer, monkeypatch, capsys):
    monkeypatch.setattr(experiment, "Tokenizer", lambda *a: tokenizer)
    monkeypatch.setattr(experiment, "make_engine", lambda: pytest.fail("DB accessed"))
    assert experiment.main(["plan", "--cases", str(CASES)]) == 0
    assert json.loads(capsys.readouterr().out)["cases_sha256"] == experiment.CASES_SHA256


def test_pairing_counts_actual_usage_once_and_does_not_persist_between_instances():
    fake = Fake()
    paired = experiment.PairedProvider(fake)
    first, usage = paired.embed(["cancellation policy"])
    second, reused_usage = paired.embed(["cancellation policy"])
    assert first == second and (usage, reused_usage) == (7, 0)
    assert (paired.requests, paired.attempts, paired.cache_hits, paired.reported_tokens) == (
        1,
        1,
        1,
        7,
    )
    assert paired.real_provider is False
    experiment.PairedProvider(fake).embed(["cancellation policy"])
    assert fake.calls == 2


def test_failed_or_invalid_vectors_never_enter_ephemeral_cache():
    class Broken(Fake):
        def embed(self, texts, before_attempt=lambda: None):
            self.calls += 1
            before_attempt()
            return [[0.0] * 1536], 7

    fake = Broken()
    paired = experiment.PairedProvider(fake)
    for _ in range(2):
        with pytest.raises(EmbeddingError, match="unit norm"):
            paired.embed(["question"])
    assert fake.calls == 2 and paired.cache == {} and paired.cache_hits == 0


def test_fixture_edit_requires_new_reviewed_experiment(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(CASES.read_text() + "\n")
    with pytest.raises(RetrievalError, match="frozen"):
        experiment.fixture(path)


@pytest.mark.parametrize(
    "function,args",
    [
        (experiment.prepare, (None, CASES, None, EmbeddingProfile())),
        (experiment.compare, (None, uuid4(), CASES, None)),
    ],
)
def test_programmatic_api_gate_before_any_access(function, args):
    with pytest.raises(RetrievalError) as error:
        function(*args)
    assert error.value.code == "api_permission"
