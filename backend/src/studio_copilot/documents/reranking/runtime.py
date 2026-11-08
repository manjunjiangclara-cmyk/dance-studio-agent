"""Opt-in local CPU rerankers with explicit downloads and complete passage windowing."""

import hashlib
import json
import math
import re
import shutil
import tempfile
import time
from pathlib import Path

MODELS = (
    "cross-encoder/ms-marco-MiniLM-L6-v2",
    "cross-encoder/ms-marco-MiniLM-L12-v2",
)
PAIR_LIMIT = 512
QUERY_LIMIT = 256
OVERLAP = 64
BATCH = 16
VERSION = "local-rerank-v1"
FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)


class RerankError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def model_directory(cache, model_id):
    if model_id not in MODELS:
        raise RerankError("invalid_model", "Use an explicitly supported reranker.")
    return Path(cache) / model_id.split("/")[1]


def verify_model(cache, model_id):
    directory = model_directory(cache, model_id)
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        files = manifest["files"]
        if (
            manifest["model_id"] != model_id
            or not re.fullmatch(r"[0-9a-f]{40}", manifest["revision"])
            or not files
        ):
            raise ValueError
        if set(files) - set(FILES) or not {"config.json", "model.safetensors"} <= set(files):
            raise ValueError
        if not ({"vocab.txt", "tokenizer.json"} & set(files)):
            raise ValueError
        if {p.name for p in directory.iterdir()} != {*files, "manifest.json"}:
            raise ValueError
        for name, expected in files.items():
            path = directory / name
            if path.is_symlink() or not path.is_file() or digest(path) != expected:
                raise ValueError
        if directory.is_symlink():
            raise ValueError
        return manifest
    except (OSError, ValueError, TypeError, KeyError):
        raise RerankError(
            "model_cache_invalid", "Prepare and verify the local model cache first."
        ) from None


def prepare_models(cache, *, allow_download=False):
    if not allow_download:
        raise RerankError("download_permission", "Model preparation requires --allow-download.")
    from huggingface_hub import HfApi, hf_hub_download

    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    prepared = []
    for model_id in MODELS:
        target = model_directory(cache, model_id)
        if target.exists():
            prepared.append(verify_model(cache, model_id))
            continue
        info = HfApi().model_info(model_id)
        if not re.fullmatch(r"[0-9a-f]{40}", info.sha):
            raise RerankError("invalid_model", "Expected an immutable model revision.")
        available = {s.rfilename for s in info.siblings}
        if not {"config.json", "model.safetensors"} <= available:
            raise RerankError("invalid_model", "Expected safe model weights and configuration.")
        with tempfile.TemporaryDirectory(dir=cache, prefix=".prepare-") as temporary:
            directory = Path(temporary) / "model"
            for name in FILES:
                if name in available:
                    hf_hub_download(model_id, name, revision=info.sha, local_dir=directory)
            shutil.rmtree(directory / ".cache", ignore_errors=True)
            manifest = dict(
                version=VERSION,
                model_id=model_id,
                revision=info.sha,
                files={p.name: digest(p) for p in directory.iterdir()},
            )
            (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            directory.rename(target)
        prepared.append(verify_model(cache, model_id))
    return prepared


def build_windows(query, text, tokenizer):
    question = tokenizer.encode(query, add_special_tokens=False)
    if not question or len(question) > QUERY_LIMIT:
        raise RerankError(
            "rerank_query_too_long", "Reranking requires 1–256 model question tokens."
        )
    passage = tokenizer.encode(text, add_special_tokens=False)
    available = PAIR_LIMIT - len(question) - tokenizer.num_special_tokens_to_add(pair=True)
    if available <= OVERLAP:
        raise RerankError("invalid_tokenizer", "Insufficient passage capacity.")
    windows = []
    start = 0
    while True:
        part = passage[start : start + available]
        encoded = tokenizer.prepare_for_model(
            question,
            pair_ids=part,
            add_special_tokens=True,
            truncation=False,
            return_attention_mask=True,
        )
        if len(encoded["input_ids"]) > PAIR_LIMIT:
            raise RerankError("invalid_tokenizer", "Pair exceeds the model limit.")
        windows.append(dict(encoded))
        if start + available >= len(passage):
            return windows
        start += available - OVERLAP


def score_candidates(query, candidates, tokenizer, score_pairs):
    if len(candidates) > 40:
        raise RerankError("candidate_limit", "Rerank at most forty distinct passages.")
    if len({c["text_sha256"] for c in candidates}) != len(candidates):
        raise RerankError("duplicate_candidates", "Candidate texts must be deduplicated first.")
    windows, owners, counts = [], [], []
    for index, candidate in enumerate(candidates):
        parts = build_windows(query, candidate["text"], tokenizer)
        windows.extend(parts)
        owners.extend([index] * len(parts))
        counts.append(len(parts))
    maxima = [-math.inf] * len(candidates)
    for start in range(0, len(windows), BATCH):
        batch = windows[start : start + BATCH]
        values = list(score_pairs(batch))
        if len(values) != len(batch) or any(not math.isfinite(float(v)) for v in values):
            raise RerankError("invalid_scores", "Expected one finite score per input window.")
        for owner, value in zip(owners[start : start + BATCH], values, strict=True):
            maxima[owner] = max(maxima[owner], float(value))
    ranked = [
        dict(candidate, rerank_score=maxima[i], window_count=counts[i], original_rank=i + 1)
        for i, candidate in enumerate(candidates)
    ]
    return sorted(ranked, key=lambda c: (-c["rerank_score"], c["original_rank"], c["text_sha256"]))


class LocalReranker:
    def __init__(self, cache, model_id):
        started = time.perf_counter()
        self.identity = verify_model(cache, model_id)
        # Optional dependencies are imported only after offline cache verification.
        import torch
        import transformers
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(4)
        directory = model_directory(cache, model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(
            directory, local_files_only=True, trust_remote_code=False
        )
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(
                directory,
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
                torch_dtype=torch.float32,
            )
            .to("cpu")
            .eval()
        )
        if (
            self.model.config.num_labels != 1
            or self.model.config.max_position_embeddings < PAIR_LIMIT
        ):
            raise RerankError("invalid_model", "Expected a single-score, 512-token cross-encoder.")
        self.identity = dict(
            self.identity,
            runtime=dict(
                torch=torch.__version__,
                transformers=transformers.__version__,
                device="cpu",
                dtype="float32",
                threads=4,
                batch_size=BATCH,
                pair_limit=PAIR_LIMIT,
                query_limit=QUERY_LIMIT,
                overlap=OVERLAP,
                aggregation="max",
            ),
        )
        self.load_seconds = time.perf_counter() - started

    def score_pairs(self, pairs):
        import torch

        batch = self.tokenizer.pad(pairs, padding=True, return_tensors="pt")
        with torch.inference_mode():
            return self.model(**batch).logits[:, 0].tolist()

    def rank(self, query, candidates):
        return score_candidates(query, candidates, self.tokenizer, self.score_pairs)
