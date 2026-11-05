"""Structure-aware recursive splitting with bounded parent-child context."""

import hashlib
import json
import re
from bisect import bisect_right
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

from .sources import Source
from .structure import Span, parse
from .tokenizer import ASSET_HASH, NAME, VERSION, WORK_WINDOW, Tokenizer


@dataclass(frozen=True)
class Config:
    chunker_version: str = "1"
    passage_target: int = 600
    passage_max: int = 900
    parent_max: int = 2400
    overlap_max: int = 80
    prefix_max: int = 128
    table_header_max: int = 128
    tokenizer: str = NAME
    tokenizer_version: str = VERSION
    tokenizer_asset_sha256: str = ASSET_HASH
    parser_version: str = "4.0.0"
    structure_max_lines: int = 100_000
    structure_max_pipes: int = 100_000
    fallback_block_characters: int = 4096
    token_work_window_characters: int = WORK_WINDOW


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def neighbors(items):
    """One-item lookahead, without collecting an entire document's records."""
    previous = None
    iterator = iter(items)
    current = next(iterator, None)
    while current is not None:
        following = next(iterator, None)
        yield previous, current, following
        previous, current = current, following


class Chunker:
    def __init__(self, source: Source, tokenizer: Tokenizer):
        self.source, self.tokenizer = source.validate(), tokenizer
        self.config = Config()
        if version("tiktoken") != VERSION or version("markdown-it-py") != "4.0.0":
            raise ValueError("Tokenizer/parser versions changed; sync the pinned dependency lock.")
        self.config_hash = digest(asdict(self.config))
        self.source_id = digest(source.metadata())
        self.sections, self.headings, self.warnings = parse(
            source.text,
            Path(source.filename).suffix.lower() == ".md",
            self.config.structure_max_lines,
            self.config.structure_max_pipes,
            self.config.fallback_block_characters,
        )
        self.prefixes = {}
        self.block_starts = {}
        self.headers = {}
        for section in self.sections:
            # The heading registry retains full text; only bounded excerpts are repeated.
            path = " / ".join(self.headings[index]["text"][:1024] for index in section.heading_ids)
            raw_prefix = f"{source.title}\nSection: {path}\n" if path else f"{source.title}\n"
            prefix = tokenizer.prefix(raw_prefix, self.config.prefix_max)
            if prefix != raw_prefix or any(
                len(self.headings[index]["text"]) > 1024 for index in section.heading_ids
            ):
                self.warnings.add("heading_prefix_truncated")
            self.prefixes[section.ordinal] = prefix
            self.block_starts[section.ordinal] = [block.start for block in section.blocks]
            for block in section.blocks:
                if block.header:
                    full = source.text[block.header.start : block.header.end]
                    # Never encode a whole oversized header just to truncate it.
                    clipped = tokenizer.prefix(full, self.config.table_header_max)
                    if len(clipped) < len(full):
                        self.warnings.add("table_header_context_truncated")
                    self.headers[block.start] = Span(
                        block.header.start, block.header.start + len(clipped)
                    )

    def _header(self, section, start):
        index = bisect_right(self.block_starts[section.ordinal], start) - 1
        block = section.blocks[max(index, 0)]
        if block.header and start >= block.header.end:
            return self.headers[block.start]
        return None

    def _render(self, section, start, end, overlap_start=None):
        parts = [self.prefixes[section.ordinal]]
        header = self._header(section, overlap_start if overlap_start is not None else start)
        if header:
            parts.append(self.source.text[header.start : header.end])
        parts.append(self.source.text[overlap_start if overlap_start is not None else start : end])
        return "\n\n".join(parts)

    def _fits(self, section, start, end, budget):
        if end - start > min(WORK_WINDOW, budget * 8):
            return False
        return self.tokenizer.count(self._render(section, start, end)) <= budget

    def _boundary(self, start, end):
        """Prefer lines (list items/table rows), then sentences, then characters."""
        value = self.source.text[start:end]
        minimum = len(value) // 2
        line = max(value.rfind("\n"), value.rfind("\r")) + 1
        if line > minimum:
            return start + line
        stops = re.finditer(r"[.!?。！？](?:[ \t]+|$)", value)
        boundary = max((match.end() for match in stops), default=0)
        return start + boundary if boundary > minimum else end

    def _ranges(self, section, start, end, budget, target):
        group_start, group_end = start, start
        # Child splitting visits only this parent's blocks, not the entire large section.
        first = max(0, bisect_right(self.block_starts[section.ordinal], start) - 1)
        for index in range(first, len(section.blocks)):
            block = section.blocks[index]
            if block.start >= end:
                break
            position, stop = max(start, block.start), min(end, block.end)
            while position < stop:
                fits = self._fits(section, group_start, stop, budget)
                if fits and (
                    group_start == group_end
                    or self.tokenizer.count(self._render(section, group_start, stop)) <= target
                ):
                    group_end = stop
                    position = stop
                elif group_end > group_start:
                    yield Span(group_start, group_end)
                    group_start = group_end
                else:
                    cut = self.tokenizer.fit_end(
                        self.source.text,
                        position,
                        stop,
                        target,
                        lambda candidate: self._render(section, position, candidate),
                    )
                    cut = self._boundary(position, cut)
                    # Removing a suffix can change BPE merges, so verify after boundary selection.
                    if not self._fits(section, position, cut, budget):
                        cut = self.tokenizer.fit_end(
                            self.source.text,
                            position,
                            cut,
                            budget,
                            lambda candidate: self._render(section, position, candidate),
                        )
                    yield Span(position, cut)
                    position = group_start = group_end = cut
        if group_end > group_start:
            yield Span(group_start, group_end)

    def _id(self, kind, section, span):
        return f"{kind}:" + digest(
            [self.source_id, self.config_hash, kind, section.ordinal, span.start, span.end]
        )

    def _parent_ranges(self):
        for section in self.sections:
            for span in self._ranges(
                section, section.start, section.end, self.config.parent_max, self.config.parent_max
            ):
                yield section, span

    def _record(self, kind, section, span, previous, following, parent_id=None):
        overlap_start = None
        if kind == "passage" and previous is not None:
            # At most 80 source tokens; a final combined measurement may shrink it further.
            low, high = max(previous.start, span.start - self.config.overlap_max * 8), span.start
            while low < high:
                middle = (low + high) // 2
                value = self.source.text[middle : span.start]
                if (
                    self.tokenizer.count(value) <= self.config.overlap_max
                    and self.tokenizer.count(self._render(section, span.start, span.end, middle))
                    <= self.config.passage_max
                ):
                    high = middle
                else:
                    low = middle + 1
            if low < span.start:
                overlap_start = low
        rendered = self._render(section, span.start, span.end, overlap_start)
        spans = []
        header = self._header(section, overlap_start if overlap_start is not None else span.start)
        if header:
            spans.append(header.json("table_header"))
        if overlap_start is not None:
            spans.append(Span(overlap_start, span.start).json("overlap"))
        spans.append(span.json())
        count = self.tokenizer.count(rendered)
        limit = self.config.parent_max if kind == "parent" else self.config.passage_max
        if count > limit:
            raise ValueError("Internal chunk token budget violation.")
        return {
            "id": self._id(kind, section, span),
            "kind": kind,
            "source_id": self.source_id,
            "section_id": section.ordinal,
            "heading_ids": section.heading_ids,
            "parent_id": parent_id,
            "previous_id": self._id(kind, section, previous) if previous else None,
            "next_id": self._id(kind, section, following) if following else None,
            "source_spans": spans,
            "prefix": self.prefixes[section.ordinal],
            "text": rendered,
            "token_count": count,
            "text_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "config_hash": self.config_hash,
        }

    def records(self):
        """Yield one parent, then its passages. Only bounded neighbours are buffered."""
        for previous, (section, span), following in neighbors(self._parent_ranges()):
            parent = self._record("parent", section, span, None, None)
            # Parent neighbours may cross sections; passage neighbours never cross parents.
            parent["previous_id"] = self._id("parent", *previous) if previous else None
            parent["next_id"] = self._id("parent", *following) if following else None
            yield parent
            ranges = self._ranges(
                section, span.start, span.end, self.config.passage_max, self.config.passage_target
            )
            for before, passage, after in neighbors(ranges):
                yield self._record("passage", section, passage, before, after, parent["id"])

    def section_records(self):
        for section in self.sections:
            yield {
                "id": section.ordinal,
                "heading_ids": section.heading_ids,
                "source_span": Span(section.start, section.end).json(),
            }
