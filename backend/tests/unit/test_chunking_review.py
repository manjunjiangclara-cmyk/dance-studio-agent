"""Additional independent provenance and interrupted-export regressions."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from studio_copilot.documents.chunking import Chunker, Source, Tokenizer
from studio_copilot.documents.chunking.export import export
from studio_copilot.documents.chunking.structure import parse
from studio_copilot.documents.chunking.tokenizer import WORK_WINDOW, default_cache


@pytest.fixture(scope="module")
def tokenizer():
    return Tokenizer(Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache())))


def chunker(value, tokenizer):
    raw = value.encode()
    return Chunker(
        Source(value, "Independent review", "source.md", hashlib.sha256(raw).hexdigest(), len(raw)),
        tokenizer,
    )


def test_neighbours_are_reciprocal_ordered_and_resolve_in_export(tokenizer):
    value = "\ufeff# Repeated\r\n\r\n" + "An exception requires teacher approval. " * 550
    value += "\r\n\r\n# Repeated\r\n" + "A different exception needs review. " * 550
    records = list(chunker(value, tokenizer).records())
    by_id = {record["id"]: record for record in records}
    assert len(by_id) == len(records)
    assert sum(record["kind"] == "parent" for record in records) > 2
    for record in records:
        body = next(span for span in record["source_spans"] if span["role"] == "body")
        for key, reverse in (("previous_id", "next_id"), ("next_id", "previous_id")):
            if record[key] is None:
                continue
            neighbour = by_id[record[key]]
            assert neighbour[reverse] == record["id"]
            assert neighbour["kind"] == record["kind"]
            neighbour_body = next(s for s in neighbour["source_spans"] if s["role"] == "body")
            if key == "previous_id":
                assert neighbour_body["end"] == body["start"]
            else:
                assert body["end"] == neighbour_body["start"]
            if record["kind"] == "passage":
                assert neighbour["section_id"] == record["section_id"]
                assert neighbour["parent_id"] == record["parent_id"]


def test_interrupted_export_after_writing_records_removes_partial_output(
    tokenizer, tmp_path, monkeypatch
):
    subject = chunker("# Content\n\n" + "Approval matters. " * 500, tokenizer)
    original_records = subject.records

    def interrupted():
        iterator = original_records()
        yield next(iterator)
        yield next(iterator)
        raise KeyboardInterrupt("Interrupted after writing real records")

    monkeypatch.setattr(subject, "records", interrupted)
    with pytest.raises(KeyboardInterrupt):
        export(subject, tmp_path / "output")
    assert list(tmp_path.iterdir()) == []


def test_export_copy_failure_does_not_leave_a_manifest(tokenizer, tmp_path, monkeypatch):
    subject = chunker("# Content\n\nOriginal text.", tokenizer)
    original_write = Path.write_bytes

    def failed_copy(path, data):
        if path.name == "source.txt":
            raise OSError("Simulated disk-full failure")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", failed_copy)
    with pytest.raises(OSError, match="disk-full"):
        export(subject, tmp_path / "output")
    assert list(tmp_path.iterdir()) == []


def test_existing_output_symlink_is_never_followed_or_modified(tokenizer, tmp_path):
    subject = chunker("# Content\n\nOriginal text.", tokenizer)
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "manifest.json"
    sentinel.write_text(json.dumps({"belongs_to": "another run"}))
    link = tmp_path / "output"
    link.symlink_to(existing, target_is_directory=True)
    with pytest.raises(FileExistsError):
        export(subject, link)
    assert link.is_symlink()
    assert json.loads(sentinel.read_text()) == {"belongs_to": "another run"}
    assert set(tmp_path.iterdir()) == {link, existing}


@pytest.mark.parametrize(
    "value",
    [
        "\ufeff# Actual heading\r\n" + "x\r\n" * 100_001 + "Final marker.",
        "# Actual heading\n\n| Col | Value |\n| --- | --- |\n" + "|" * 100_001,
    ],
)
def test_complex_source_falls_back_before_allocating_a_markdown_ast(value, monkeypatch):
    def forbidden_parser(*args, **kwargs):
        raise AssertionError("Dense source must not instantiate the full Markdown parser")

    monkeypatch.setattr("studio_copilot.documents.chunking.structure.MarkdownIt", forbidden_parser)
    sections, headings, warnings = parse(value, True)
    assert warnings == {"structure_complexity_fallback"}
    assert len(sections) == 1 and sections[0].heading_ids == []
    assert headings == []  # Fallback must not claim heading/table interpretation.
    blocks = sections[0].blocks
    assert len(blocks) <= len(value) // 2048 + 1
    assert all(0 < block.end - block.start <= 4096 for block in blocks)
    assert all(block.header is None and block.kind == "paragraph_fallback" for block in blocks)
    assert blocks[0].start == 0 and blocks[-1].end == len(value)
    assert all(left.end == right.start for left, right in zip(blocks, blocks[1:]))
    assert "".join(value[block.start : block.end] for block in blocks) == value


def test_fallback_warning_and_absent_structure_are_exported(tokenizer, tmp_path):
    value = "\ufeff# Not interpreted\r\n" + "\r\n" * 100_001 + "The end survives."
    subject = chunker(value, tokenizer)
    manifest = export(subject, tmp_path / "output")
    assert "structure_complexity_fallback" in manifest["warnings"]
    assert manifest["coverage_characters"] == {"parent": len(value), "passage": len(value)}
    assert (tmp_path / "output" / "source.txt").read_bytes() == value.encode()
    assert (tmp_path / "output" / "headings.jsonl").read_text() == ""
    assert "structure_complexity_fallback" in (tmp_path / "output" / "report.txt").read_text()
    for filename in ("parents.jsonl", "passages.jsonl"):
        for line in (tmp_path / "output" / filename).read_text().splitlines():
            record = json.loads(line)
            assert record["heading_ids"] == [] and record["section_id"] == 0
            assert not any(span["role"] == "table_header" for span in record["source_spans"])
            assert tokenizer.count(record["text"]) <= (900 if record["kind"] == "passage" else 2400)


@pytest.mark.parametrize("budget", [1, 2, 3, 4, 7, 128])
@pytest.mark.parametrize(
    "value",
    [
        "a" * 12_000,
        "👩🏽‍🦰é舞蹈\r\n" * 80,
        "\U0010ffff" * 20,
        "<|endoftext|> <|fim_prefix|> literal. " * 80,
    ],
)
def test_fit_end_tiny_budgets_only_return_measured_unicode_prefixes(tokenizer, budget, value):
    original = "untouched prefix: " + value + " outside range"
    start, end = len("untouched prefix: "), len("untouched prefix: ") + len(value)
    try:
        stop = tokenizer.fit_end(original, start, end, budget)
    except ValueError as error:
        assert "no room for source text" in str(error)
        # A tiny budget can legitimately be unable to hold even one Unicode character.
        assert tokenizer.count(value[:1]) > budget
    else:
        fragment = original[start:stop]
        assert start < stop <= min(end, start + WORK_WINDOW)
        assert fragment == value[: stop - start]
        assert fragment.encode().decode() == fragment
        assert tokenizer.count(fragment) <= budget


def test_fit_end_repeated_tiny_unicode_slices_preserve_every_character(tokenizer):
    value = "\ufeff\U0010ffff👩🏽‍🦰é舞蹈\r\n<|endoftext|>" * 4
    parts, start = [], 0
    while start < len(value):
        stop = tokenizer.fit_end(value, start, len(value), 4)
        assert start < stop <= len(value)
        parts.append(value[start:stop])
        assert tokenizer.count(parts[-1]) <= 4
        start = stop
    assert "".join(parts) == value
    assert "".join(parts).encode() == value.encode()


def test_fit_end_measures_combined_context_including_suffix(tokenizer):
    value = "👩🏽‍🦰 Café dancers need approval. " * 100
    prefix = "Document\nSection: Terms\n\n| Class | Exceptions |\n| --- | --- |\n"
    suffix = "\n\nContinuation."
    budget = tokenizer.count(prefix + suffix) + 12

    def render(stop):
        return prefix + value[:stop] + suffix

    stop = tokenizer.fit_end(value, 0, len(value), budget, render)
    assert stop > 0
    assert tokenizer.count(render(stop)) <= budget
    with pytest.raises(ValueError, match="no room"):
        tokenizer.fit_end(value, 0, len(value), 1, render)


@pytest.mark.parametrize(
    "value",
    ["# " + "Huge title " * 500, "舞蹈👩🏽‍🦰é" * 500, "<|endoftext|>" * 500],
)
def test_heading_prefix_cap_preserves_original_unicode_and_literal_tokens(tokenizer, value):
    prefix = tokenizer.prefix(value, 128)
    assert prefix and value.startswith(prefix)
    assert tokenizer.count(prefix) <= 128
    assert prefix.encode().decode() == prefix
