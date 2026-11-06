"""Input rejection happens before database work or paid provider construction."""

import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.retrieval.engine import RetrievalError, search


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(
        Path(os.environ.get("STUDIO_TOKENIZER_CACHE", "/tmp/studio-chunking-tokenizer"))
    )


class NoDatabase:
    def __getattr__(self, name):
        raise AssertionError(f"Invalid request accessed database: {name}")


@pytest.mark.parametrize("query", ["", "  \n\t", "policy\x00text", "a" * 4097, "💃" * 400])
def test_invalid_query_rejected_before_database(tokenizer, query):
    with pytest.raises(RetrievalError):
        search(NoDatabase(), [uuid4()], query, date(2026, 6, 1), tokenizer, mode="keyword")


@pytest.mark.parametrize("mode", ["vector", "hybrid"])
def test_api_mode_requires_explicit_paid_permission_before_database(tokenizer, mode):
    with pytest.raises(RetrievalError):
        search(NoDatabase(), [uuid4()], "policy", date(2026, 6, 1), tokenizer, mode=mode)


def test_empty_run_selection_rejected_before_database(tokenizer):
    with pytest.raises(RetrievalError):
        search(NoDatabase(), [], "policy", date(2026, 6, 1), tokenizer, mode="keyword")


def test_unknown_mode_rejected_before_database(tokenizer):
    with pytest.raises(RetrievalError):
        search(NoDatabase(), [uuid4()], "policy", date(2026, 6, 1), tokenizer, mode="rerank")


class FakeEngine:
    disposed = False

    def dispose(self):
        self.disposed = True


def cli_args(*extra):
    return [
        "search",
        "--run-id",
        str(uuid4()),
        "--query",
        "cancellations",
        "--as-of",
        "2026-06-01",
        *extra,
    ]


def test_cli_json_preserves_unicode_and_closes_engine(monkeypatch, capsys):
    import json

    from studio_copilot.documents.retrieval import __main__ as cli

    engine = FakeEngine()
    monkeypatch.setattr(cli, "make_engine", lambda: engine)
    monkeypatch.setattr(cli, "Tokenizer", lambda *args: object())
    captured = {}

    def fake_search(*args, **kwargs):
        captured.update(kwargs)
        return {"results": [{"text": "Café 💃"}], "degraded": False}

    monkeypatch.setattr(cli, "search", fake_search)
    assert cli.main(cli_args("--mode", "keyword", "--format", "json")) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["text"] == "Café 💃"
    assert captured["mode"] == "keyword" and captured["allow_api"] is False
    assert engine.disposed


def test_cli_database_failure_does_not_print_secrets(monkeypatch, capsys):
    from sqlalchemy.exc import OperationalError

    from studio_copilot.documents.retrieval import __main__ as cli

    monkeypatch.setattr(cli, "Tokenizer", lambda *args: object())

    def broken():
        raise OperationalError(
            "postgresql://password-secret@host/db", {}, Exception("password-secret")
        )

    monkeypatch.setattr(cli, "make_engine", broken)
    assert cli.main(cli_args()) == 1
    output = capsys.readouterr()
    assert "password-secret" not in output.out + output.err
    assert "database operation failed" in output.err


def test_cli_error_returns_nonzero_and_disposes_engine(monkeypatch, capsys):
    from studio_copilot.documents.retrieval import __main__ as cli

    engine = FakeEngine()
    monkeypatch.setattr(cli, "make_engine", lambda: engine)
    monkeypatch.setattr(cli, "Tokenizer", lambda *args: object())

    def rejected(*args, **kwargs):
        raise RetrievalError("source_missing", "Selected run not found.")

    monkeypatch.setattr(cli, "search", rejected)
    assert cli.main(cli_args()) == 1
    assert "source_missing" in capsys.readouterr().err
    assert engine.disposed


@pytest.mark.parametrize(
    "arguments", [["search"], cli_args("--as-of", "invalid"), cli_args("--mode", "rerank")]
)
def test_cli_invalid_arguments_never_connect_database(monkeypatch, arguments):
    from studio_copilot.documents.retrieval import __main__ as cli

    monkeypatch.setattr(cli, "make_engine", lambda: pytest.fail("Parser error connected DB"))
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2
