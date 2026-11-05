"""Block boundaries with original-text offsets; Markdown is never rendered."""

import re
from array import array
from dataclasses import dataclass, field

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def json(self, role="body"):
        return {"start": self.start, "end": self.end, "role": role}


@dataclass
class Block:
    start: int
    end: int
    kind: str
    header: Span | None = None


@dataclass
class Section:
    ordinal: int
    start: int
    end: int
    heading_ids: list[int]
    blocks: list[Block] = field(default_factory=list)


def parse(text: str, markdown: bool, max_lines=100_000, max_pipes=100_000, fallback_chars=4096):
    """Return sections and a shared heading registry (avoid duplicating long paths).

    Only block tokens are parsed: inline trees and HTML rendering are unnecessary.
    The parser and line index still materialize the bounded source; not constant memory.
    """
    line_count = text.count("\n") + text.count("\r") - text.count("\r\n") + 1
    if line_count > max_lines or (markdown and text.count("|") > max_pipes):
        # Extremely dense source can expand to millions of Python token objects.
        # Preserve everything with explicit, inspectable degradation to coarse
        # paragraph/line boundaries instead of silently exhausting process memory.
        blocks = []
        start = 0
        while start < len(text):
            end = min(start + fallback_chars, len(text))
            if end < len(text):
                boundary = max(
                    text.rfind("\n", start + fallback_chars // 2, end),
                    text.rfind("\r", start + fallback_chars // 2, end),
                )
                if boundary >= 0:
                    end = boundary + 1
            blocks.append(Block(start, end, "paragraph_fallback"))
            start = end
        return [Section(0, 0, len(text), [], blocks)], [], {"structure_complexity_fallback"}
    starts = array("I", [0])
    starts.extend(match.end() for match in re.finditer(r"\r\n|\r|\n", text))

    def offset(line):
        return starts[line] if line < len(starts) else len(text)

    headings, entries, stack = [], [], []
    if markdown:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        # CommonMark ignores an initial BOM; offsets below continue to reference it.
        if normalized.startswith("\ufeff"):
            normalized = normalized[1:]
        parser = MarkdownIt("commonmark").enable("table")
        tokens = []
        parser.block.parse(normalized, parser, {}, tokens)
        for index, token in enumerate(tokens):
            if token.level != 0 or token.map is None or token.type == "inline":
                continue
            start, end = map(offset, token.map)
            kind = token.type.removesuffix("_open")
            heading = None
            if token.type == "heading_open":
                heading = (int(token.tag[1:]), tokens[index + 1].content)
            header = None
            if token.type == "table_open":
                header = Span(start, offset(min(token.map[0] + 2, token.map[1])))
            entries.append((start, end, kind, heading, header))
        del tokens, normalized
    else:
        # Blank-line groups are paragraphs; preserve all separators in the source spans.
        cursor = 0
        for separator in re.finditer(r"(?>\r\n|\r|\n)[ \t]*(?>\r\n|\r|\n)", text):
            entries.append((cursor, separator.end(), "paragraph", None, None))
            cursor = separator.end()
        if cursor < len(text):
            entries.append((cursor, len(text), "paragraph", None, None))
    if not entries:
        entries = [(0, len(text), "paragraph", None, None)]

    sections = [Section(0, 0, len(text), [])]
    for index, (start, end, kind, heading, header) in enumerate(entries):
        # Own gaps, blank lines and Markdown syntax too; no source characters disappear.
        if index == 0:
            start = 0
        end = entries[index + 1][0] if index + 1 < len(entries) else len(text)
        if heading:
            level, title = heading
            while stack and headings[stack[-1]]["level"] >= level:
                stack.pop()
            heading_id = len(headings)
            headings.append(
                {
                    "id": heading_id,
                    "level": level,
                    "text": title,
                    "parent_id": stack[-1] if stack else None,
                    "source_span": Span(start, end).json(),
                }
            )
            stack.append(heading_id)
            if sections[-1].blocks:
                sections[-1].end = start
                sections.append(Section(len(sections), start, len(text), stack.copy()))
            else:
                sections[-1].heading_ids = stack.copy()
        sections[-1].blocks.append(Block(start, end, kind, header))
    return sections, headings, set()
