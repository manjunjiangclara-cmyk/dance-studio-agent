"""Independent scoring/fixture checks for the frozen larger retrieval corpus."""

import os
from pathlib import Path

import pytest

from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.chunking.tokenizer import default_cache
from studio_copilot.documents.embedding.provider import EmbeddingProfile

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "retrieval_corpus_v2" / "corpus.json"


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


def test_plan_has_no_database_provider_or_key_dependency(tokenizer, monkeypatch):
    from studio_copilot.documents.retrieval import corpus

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(corpus, "make_engine", lambda *a, **kw: pytest.fail("DB accessed"))
    monkeypatch.setattr(corpus, "Embedder", lambda *a, **kw: pytest.fail("Provider created"))
    report = corpus.plan(CORPUS, tokenizer, EmbeddingProfile())
    assert report["dry_run"] is True
    assert report["cases"] == 100
    assert report["documents"] == 16
    assert report["unique_question_requests"] > 0
    assert report["fresh_document_unique_inputs"] > 16


def test_evidence_coverage_cannot_cross_document_identities():
    from studio_copilot.documents.retrieval import corpus

    label = dict(document_key="current_policy", start=10, end=20)
    wrong_source = [dict(document_key="expired_policy", start=0, end=100)]
    assert corpus.covered(label, wrong_source) is False
    assert corpus.covered(label, [dict(document_key="current_policy", start=10, end=20)])
    # Adjoining ranges may cover one label, but only within that label's document.
    assert (
        corpus.covered(
            label,
            [
                dict(document_key="current_policy", start=10, end=15),
                dict(document_key="expired_policy", start=15, end=20),
            ],
        )
        is False
    )
    assert corpus.covered(
        label,
        [
            dict(document_key="current_policy", start=10, end=15),
            dict(document_key="current_policy", start=15, end=20),
        ],
    )


def test_multiple_required_evidence_counts_partial_coverage_separately():
    from studio_copilot.documents.retrieval import corpus

    labels = [
        dict(document_key="policy", start=10, end=20),
        dict(document_key="exceptions", start=10, end=20),
    ]
    ranking = [
        [dict(document_key="distractor", start=10, end=20)],
        [dict(document_key="policy", start=10, end=20)],
        [dict(document_key="exceptions", start=10, end=20)],
    ]
    partial = corpus.measures(labels, ranking, 2)
    assert partial == dict(recall=0.5, all_evidence=False, reciprocal_rank=0.5)
    complete = corpus.measures(labels, ranking, 3)
    assert complete == dict(recall=1.0, all_evidence=True, reciprocal_rank=0.5)


def test_modified_source_bytes_are_rejected_before_estimation(tmp_path, tokenizer):
    import shutil

    from studio_copilot.documents.retrieval import corpus
    from studio_copilot.documents.retrieval.engine import RetrievalError

    target = tmp_path / "fixture"
    shutil.copytree(CORPUS.parent, target)
    source = target / "attendance_2027.md"
    source.write_bytes(source.read_bytes() + b"\nHidden policy change.\n")
    with pytest.raises(RetrievalError):
        corpus.plan(target / "corpus.json", tokenizer, EmbeddingProfile())


def test_isolated_runner_requires_explicit_paid_permission_before_setup(tmp_path):
    import subprocess
    import sys

    output = tmp_path / "must-not-exist"
    environment = dict(os.environ, DATABASE_URL="invalid-scheme://must-not-connect")
    environment.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_retrieval_corpus.py",
            "--output-dir",
            str(output),
            "--tokenizer-cache",
            str(tmp_path / "missing-tokenizer"),
        ],
        cwd=CORPUS.parents[3],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode != 0
    diagnostic = result.stdout + result.stderr
    assert "allow-api" in diagnostic or "api_permission" in diagnostic
    assert not output.exists()
    assert "Traceback" not in result.stderr


def test_isolated_runner_rejects_non_test_database_before_provider_or_output(tmp_path):
    import subprocess
    import sys

    output = tmp_path / "must-not-exist"
    environment = dict(
        os.environ,
        TEST_DATABASE_URL="postgresql+psycopg://nobody:secret-sentinel@127.0.0.1:1/studio_copilot",
        DATABASE_URL="postgresql+psycopg://nobody:secret-sentinel@127.0.0.1:1/studio_copilot",
    )
    environment.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_retrieval_corpus.py",
            "--output-dir",
            str(output),
            "--tokenizer-cache",
            str(tmp_path / "missing-tokenizer"),
            "--allow-api",
        ],
        cwd=CORPUS.parents[3],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode != 0
    diagnostic = result.stdout + result.stderr
    assert "_test" in diagnostic
    assert "secret-sentinel" not in diagnostic
    assert not output.exists()
    assert "Traceback" not in result.stderr
