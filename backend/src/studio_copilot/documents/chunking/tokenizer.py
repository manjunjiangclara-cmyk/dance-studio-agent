"""Pinned local tokenizer. Only the explicit preparation command accesses a URL."""

import base64
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.request import urlopen

from tiktoken import Encoding

NAME = "cl100k_base"
VERSION = "0.12.0"
WORK_WINDOW = 8192
ASSET_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
ASSET_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
# The cl100k_base expression from tiktoken_ext.openai_public (MIT), pinned above.
PATTERN = (
    r"'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+|"
    r" ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"
)


def default_cache() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "studio-copilot"


def prepare(cache: Path):
    """Download a public BPE vocabulary once; no API key or provider inference."""
    cache.mkdir(parents=True, exist_ok=True)
    with urlopen(ASSET_URL, timeout=30) as response:
        data = response.read(3_000_001)
    if hashlib.sha256(data).hexdigest() != ASSET_HASH:
        raise ValueError("Tokenizer asset SHA-256 verification failed.")
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
            name = Path(stream.name)
            stream.write(data)
        name.replace(cache / f"{NAME}.tiktoken")
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


class Tokenizer:
    def __init__(self, cache: Path | None = None):
        path = (cache if cache is not None else default_cache()) / f"{NAME}.tiktoken"
        try:
            data = path.read_bytes()
        except FileNotFoundError as error:
            raise ValueError(
                "Tokenizer asset is missing. Run --prepare-tokenizer with the same "
                "--tokenizer-cache directory first."
            ) from error
        if hashlib.sha256(data).hexdigest() != ASSET_HASH:
            raise ValueError("Tokenizer asset is corrupt; rerun --prepare-tokenizer.")
        ranks = {
            base64.b64decode(word): int(rank) for word, rank in map(bytes.split, data.splitlines())
        }
        # No tiktoken URL loader or implicit cache/download behavior is used here.
        self.encoding = Encoding(
            name=NAME, pat_str=PATTERN, mergeable_ranks=ranks, special_tokens={}
        )

    def count(self, value: str) -> int:
        # Strings resembling special tokens are ordinary source text.
        return len(self.encoding.encode_ordinary(value))

    def fit_end(self, text: str, start: int, end: int, budget: int, render=None) -> int:
        """Find a fitting Unicode boundary with bounded work on pathological lines.

        BPE lengths are not strictly monotonic, so binary search need not find the
        largest possible prefix. Every returned result is nevertheless measured.
        The character work window may deliberately underfill token-sparse content.
        """
        render = render or (lambda stop: text[start:stop])
        high = min(end, start + min(WORK_WINDOW, max(64, budget * 8)))
        # Encode one bounded window once, then propose a prefix from its token bytes.
        # Repeated binary-search encodings of long unbroken words are needlessly costly.
        tokens = self.encoding.encode_ordinary(text[start:high])
        context_tokens = self.count(render(start))
        take = max(1, min(len(tokens), budget - context_tokens - 2))
        fragment = self.encoding.decode_bytes(tokens[:take]).decode("utf-8", errors="ignore")
        proposed = start + len(fragment)
        if proposed > start and self.count(render(proposed)) <= budget:
            return proposed
        low, best = start + 1, start
        high = max(start + 1, proposed)
        while low <= high:
            mid = (low + high) // 2
            if self.count(render(mid)) <= budget:
                best, low = mid, mid + 1
            else:
                high = mid - 1
        if best == start:
            raise ValueError("The token budget leaves no room for source text.")
        return best

    def prefix(self, text: str, budget: int) -> str:
        if not text:
            return ""
        return text[: self.fit_end(text, 0, len(text), budget)]
