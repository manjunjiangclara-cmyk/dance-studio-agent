"""No provider side effects in help/plan/status; safe CLI failures."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from studio_copilot.documents.embedding import __main__ as cli
from studio_copilot.documents.embedding.provider import EmbeddingError


class FakeEngine:
    disposed = False

    def dispose(self):
        self.disposed = True


@pytest.mark.parametrize("command", ["plan", "status"])
def test_read_only_commands_need_no_provider_or_api_key(monkeypatch, capsys, command):
    engine = FakeEngine()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "make_engine", lambda: engine)
    monkeypatch.setattr(cli, "Embedder", lambda *a: pytest.fail("Provider must not be built"))
    if command == "plan":
        monkeypatch.setattr(cli, "Tokenizer", lambda *a: object())
        monkeypatch.setattr(cli, "plan", lambda *a, **k: {"dry_run": True})
        args = ["plan", "--document-id", str(uuid4()), "--revision", "1"]
    else:
        monkeypatch.setattr(cli.Store, "status", lambda *a: {"status": "complete"})
        args = ["status", "--run-id", str(uuid4())]
    assert cli.main(args) == 0
    assert engine.disposed
    assert capsys.readouterr().err == ""


def test_cli_never_prints_database_credentials(monkeypatch, capsys):
    def broken():
        raise OperationalError("postgresql://secret-password", {}, Exception("secret-password"))

    monkeypatch.setattr(cli, "make_engine", broken)
    assert cli.main(["status", "--run-id", str(uuid4())]) == 1
    output = capsys.readouterr()
    assert "secret-password" not in output.err + output.out
    assert "database operation failed" in output.err


def test_cli_invalid_endpoint_is_sanitized(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_EMBEDDING_BASE_URL", "https://user:secret-password@example.test")
    assert cli.main(["status", "--run-id", str(uuid4())]) == 1
    assert "secret-password" not in capsys.readouterr().err


def test_provider_failure_has_code_and_engine_is_closed(monkeypatch, capsys):
    engine = FakeEngine()
    monkeypatch.setattr(cli, "make_engine", lambda: engine)
    monkeypatch.setattr(cli, "Tokenizer", lambda *a: object())

    def failure(*a, **k):
        raise EmbeddingError("busy", "An existing owner is running.")

    monkeypatch.setattr(cli, "run", failure)
    assert cli.main(["run", "--document-id", str(uuid4()), "--revision", "1"]) == 1
    assert "busy" in capsys.readouterr().err
    assert engine.disposed


def test_smoke_is_explicit_and_never_connects_database(monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_engine", lambda: pytest.fail("No DB is needed"))

    class Provider:
        def __init__(self, profile):
            pass

        def embed(self, texts):
            assert len(texts) == 2 and all("Fictional" in text for text in texts)
            return [[1.0] * 1536] * 2, 20

    monkeypatch.setattr(cli, "Embedder", Provider)
    assert cli.main(["smoke"]) == 0
    assert '"reported_tokens": 20' in capsys.readouterr().out
