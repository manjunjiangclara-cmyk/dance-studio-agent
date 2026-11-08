"""Independent reranking contracts; no torch, downloads or hosted model calls."""

import math

import pytest

from studio_copilot.documents.reranking.runtime import RerankError


class CharacterTokenizer:
    """Expose exact IDs so a lost tail or broken overlap cannot hide in decoding."""

    model_max_length = 512
    pad_token_id = 0

    def encode(self, text, add_special_tokens=False):
        return [ord(character) for character in text]

    def num_special_tokens_to_add(self, pair=False):
        return 3 if pair else 2

    def build_inputs_with_special_tokens(self, first, second=None):
        return [1, *first, 2, *(second or []), 2]

    def create_token_type_ids_from_sequences(self, first, second=None):
        return [0] * (len(first) + 2) + [1] * (len(second or []) + 1)

    def prepare_for_model(self, ids, pair_ids=None, **kwargs):
        values = self.build_inputs_with_special_tokens(ids, pair_ids)
        return dict(
            input_ids=values,
            attention_mask=[1] * len(values),
            token_type_ids=self.create_token_type_ids_from_sequences(ids, pair_ids),
        )


def passage_ids(pair, query):
    return pair["input_ids"][len(query) + 2 : -1]


def test_windows_preserve_entire_tail_and_fixed_overlap():
    from studio_copilot.documents.reranking.runtime import build_windows

    query = "question"
    text = "".join(chr(1000 + i) for i in range(1400))
    windows = build_windows(query, text, CharacterTokenizer())
    assert len(windows) > 1
    assert all(len(pair["input_ids"]) <= 512 for pair in windows)
    pieces = [passage_ids(pair, query) for pair in windows]
    recovered = pieces[0][:]
    for left, right in zip(pieces, pieces[1:]):
        assert left[-64:] == right[:64]
        recovered.extend(right[64:])
    assert recovered == [ord(character) for character in text]
    assert pieces[-1][-1] == ord(text[-1])


def test_question_limit_uses_model_tokens_and_keeps_boundary_question():
    from studio_copilot.documents.reranking.runtime import build_windows

    assert build_windows("中" * 256, "Tail evidence.", CharacterTokenizer())
    with pytest.raises(RerankError) as caught:
        build_windows("中" * 257, "Tail evidence.", CharacterTokenizer())
    assert "question" in str(caught.value).lower() or "query" in str(caught.value).lower()


def test_short_pair_has_exact_question_and_passage_without_truncation():
    from studio_copilot.documents.reranking.runtime import build_windows

    query, passage = "What?", "Café\r\n中文🙂<|endoftext|>"
    pairs = build_windows(query, passage, CharacterTokenizer())
    assert len(pairs) == 1
    assert pairs[0]["input_ids"] == [
        1,
        *map(ord, query),
        2,
        *map(ord, passage),
        2,
    ]


def test_max_window_score_promotes_tail_evidence_and_batches_at_sixteen():
    from studio_copilot.documents.reranking.runtime import score_candidates

    calls = []
    candidates = [dict(text="a" * 1500 + "Z", text_sha256=f"{i:064x}") for i in range(20)]

    def score_pairs(pairs):
        calls.append(pairs)
        return [9.0 if ord("Z") in pair["input_ids"] else 1.0 for pair in pairs]

    ranked = score_candidates("q", candidates, CharacterTokenizer(), score_pairs)
    assert len(ranked) == 20
    assert all(0 < len(batch) <= 16 for batch in calls)
    assert sum(map(len, calls)) == sum(item["window_count"] for item in ranked)
    assert all(item["window_count"] > 1 for item in ranked)
    assert all(item["rerank_score"] == 9 for item in ranked)
    assert [item["text_sha256"] for item in ranked] == [item["text_sha256"] for item in candidates]
    assert all("rerank_score" not in item for item in candidates)


def test_score_order_and_original_rank_ties_are_deterministic():
    from studio_copilot.documents.reranking.runtime import score_candidates

    candidates = [
        dict(text="low", text_sha256="f" * 64),
        dict(text="high", text_sha256="e" * 64),
        dict(text="high", text_sha256="a" * 64),
    ]
    ranked = score_candidates(
        "q",
        candidates,
        CharacterTokenizer(),
        lambda pairs: [2.0 if ord("h") in pair["input_ids"] else 0.0 for pair in pairs],
    )
    assert [item["text"] for item in ranked] == ["high", "high", "low"]
    assert ranked[0]["text_sha256"] == "e" * 64
    assert ranked[1]["text_sha256"] == "a" * 64


@pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf])
def test_nonfinite_scores_fail_instead_of_silent_baseline(score):
    from studio_copilot.documents.reranking.runtime import score_candidates

    with pytest.raises(RerankError):
        score_candidates(
            "q",
            [dict(text="evidence", text_sha256="a" * 64)],
            CharacterTokenizer(),
            lambda pairs: [score],
        )


@pytest.mark.parametrize("scores", [[], [1.0, 2.0]])
def test_wrong_score_count_cannot_drop_or_fabricate_passages(scores):
    from studio_copilot.documents.reranking.runtime import score_candidates

    with pytest.raises(RerankError):
        score_candidates(
            "q",
            [dict(text="evidence", text_sha256="a" * 64)],
            CharacterTokenizer(),
            lambda pairs: scores,
        )


def test_model_preparation_requires_opt_in_before_creating_cache(tmp_path):
    from studio_copilot.documents.reranking.runtime import prepare_models

    cache = tmp_path / "absent"
    with pytest.raises(RerankError):
        prepare_models(cache)
    assert not cache.exists()


def test_loading_missing_model_is_clear_offline_error(tmp_path, monkeypatch):
    from studio_copilot.documents.reranking.runtime import LocalReranker

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RerankError) as caught:
        LocalReranker(tmp_path / "absent", "cross-encoder/ms-marco-MiniLM-L6-v2")
    assert "Traceback" not in str(caught.value)
    assert any(word in str(caught.value).lower() for word in ("missing", "prepare", "cache"))


def prepared_cache(tmp_path):
    import hashlib
    import json

    model_id = "cross-encoder/ms-marco-MiniLM-L6-v2"
    folder = tmp_path / "ms-marco-MiniLM-L6-v2"
    folder.mkdir()
    files = {"config.json": b"{}", "model.safetensors": b"weights", "vocab.txt": b"a\nb\n"}
    for name, raw in files.items():
        (folder / name).write_bytes(raw)
    (folder / "manifest.json").write_text(
        json.dumps(
            dict(
                model_id=model_id,
                revision="a" * 40,
                files={name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
            )
        )
    )
    return model_id, folder


@pytest.mark.parametrize("damage", ["changed", "missing", "extra", "symlink"])
def test_offline_model_cache_rejects_corruption_and_unmanifested_files(tmp_path, damage):
    from studio_copilot.documents.reranking.runtime import verify_model

    model_id, folder = prepared_cache(tmp_path)
    assert verify_model(tmp_path, model_id)["revision"] == "a" * 40
    if damage == "changed":
        (folder / "vocab.txt").write_text("changed tokenizer")
    elif damage == "missing":
        (folder / "vocab.txt").unlink()
    elif damage == "extra":
        (folder / "unreviewed.py").write_text("raise RuntimeError('never execute')")
    else:
        (folder / "config.json").unlink()
        (folder / "config.json").symlink_to(folder / "vocab.txt")
    with pytest.raises(RerankError) as caught:
        verify_model(tmp_path, model_id)
    assert caught.value.code == "model_cache_invalid"


def test_model_cache_identity_cannot_be_relabelled_as_second_model(tmp_path):
    import json

    from studio_copilot.documents.reranking.runtime import verify_model

    model_id, folder = prepared_cache(tmp_path)
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["model_id"] = "cross-encoder/ms-marco-MiniLM-L12-v2"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(RerankError):
        verify_model(tmp_path, model_id)


@pytest.mark.parametrize("count", [2, 41])
def test_reranking_rejects_duplicate_or_unbounded_candidate_lists(count):
    from studio_copilot.documents.reranking.runtime import score_candidates

    candidates = [dict(text="text", text_sha256="a" * 64) for _ in range(count)]
    with pytest.raises(RerankError):
        score_candidates("q", candidates, CharacterTokenizer(), lambda pairs: pytest.fail("scored"))


@pytest.mark.parametrize("revision", ["main", "latest", "a" * 39, "g" * 40])
def test_model_cache_requires_immutable_commit_identity(tmp_path, revision):
    import json

    from studio_copilot.documents.reranking.runtime import verify_model

    model_id, folder = prepared_cache(tmp_path)
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["revision"] = revision
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(RerankError):
        verify_model(tmp_path, model_id)


def test_local_model_constructor_enforces_cpu_offline_safe_loading(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    from studio_copilot.documents.reranking.runtime import LocalReranker

    model_id, folder = prepared_cache(tmp_path)
    model = Mock()
    model.to.return_value = model
    model.eval.return_value = model
    model.config = SimpleNamespace(num_labels=1, max_position_embeddings=512)
    tokenizer_constructor = Mock(return_value=CharacterTokenizer())
    model_constructor = Mock(return_value=model)
    dtype = object()
    threads = Mock()
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            __version__="test-torch",
            float32=dtype,
            set_num_threads=threads,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            __version__="test-transformers",
            AutoTokenizer=SimpleNamespace(from_pretrained=tokenizer_constructor),
            AutoModelForSequenceClassification=SimpleNamespace(from_pretrained=model_constructor),
        ),
    )
    scorer = LocalReranker(tmp_path, model_id)
    threads.assert_called_once_with(4)
    tokenizer_constructor.assert_called_once_with(
        folder,
        local_files_only=True,
        trust_remote_code=False,
    )
    model_constructor.assert_called_once_with(
        folder,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        torch_dtype=dtype,
    )
    model.to.assert_called_once_with("cpu")
    model.eval.assert_called_once_with()
    assert scorer.identity["runtime"]["device"] == "cpu"
    assert scorer.identity["runtime"]["dtype"] == "float32"
    assert scorer.load_seconds >= 0
