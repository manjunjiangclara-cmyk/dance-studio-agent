"""Independent invariants for source coverage, final budgets and offline exports."""

import hashlib
import json
import os
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from studio_copilot.documents.chunking import Chunker, Source, Tokenizer, load_file
from studio_copilot.documents.chunking import engine as chunking_engine
from studio_copilot.documents.chunking.__main__ import main
from studio_copilot.documents.chunking.export import export
from studio_copilot.documents.chunking.tokenizer import default_cache


@pytest.fixture(scope="module")
def tokenizer_cache():
    return Path(os.environ.get("STUDIO_TOKENIZER_CACHE", default_cache()))


@pytest.fixture(scope="module")
def tokenizer(tokenizer_cache):
    return Tokenizer(tokenizer_cache)


def source(value, filename="handbook.md", **metadata):
    raw = value.encode("utf-8")
    return Source(
        value, "Studio handbook", filename, hashlib.sha256(raw).hexdigest(), len(raw), **metadata
    )


def assert_invariants(chunker, tokenizer):
    records = list(chunker.records())
    original = chunker.source.text
    parents = {record["id"]: record for record in records if record["kind"] == "parent"}
    ids = [record["id"] for record in records]
    assert len(ids) == len(set(ids))
    for kind, limit in (("parent", 2400), ("passage", 900)):
        owned = []
        for record in (item for item in records if item["kind"] == kind):
            assert record["token_count"] == tokenizer.count(record["text"]) <= limit
            assert hashlib.sha256(record["text"].encode()).hexdigest() == record["text_sha256"]
            assert tokenizer.count(record["prefix"]) <= 128
            spans = record["source_spans"]
            assert all(0 <= span["start"] < span["end"] <= len(original) for span in spans)
            body = next(span for span in spans if span["role"] == "body")
            owned.append(body)
            pieces = [record["prefix"]]
            headers = [span for span in spans if span["role"] == "table_header"]
            for span in headers:
                value = original[span["start"] : span["end"]]
                assert tokenizer.count(value) <= 128
                pieces.append(value)
            pieces.append(
                "".join(
                    original[span["start"] : span["end"]]
                    for span in spans
                    if span["role"] != "table_header"
                )
            )
            assert "\n\n".join(pieces) == record["text"]
            if kind == "passage":
                parent = parents[record["parent_id"]]
                parent_body = next(s for s in parent["source_spans"] if s["role"] == "body")
                assert parent_body["start"] <= body["start"] < body["end"] <= parent_body["end"]
                assert record["section_id"] == parent["section_id"]
                for span in (s for s in spans if s["role"] == "overlap"):
                    assert parent_body["start"] <= span["start"] < span["end"] == body["start"]
                    assert tokenizer.count(original[span["start"] : span["end"]]) <= 80
                for key in ("previous_id", "next_id"):
                    if record[key]:
                        neighbour = next(item for item in records if item["id"] == record[key])
                        assert neighbour["parent_id"] == record["parent_id"]
        assert owned[0]["start"] == 0 and owned[-1]["end"] == len(original)
        assert all(left["end"] == right["start"] for left, right in zip(owned, owned[1:]))
        assert "".join(original[s["start"] : s["end"]] for s in owned) == original
    return records


@pytest.mark.parametrize("filename", ["handbook.md", "handbook.txt"])
def test_lossless_unicode_and_final_budgets(tokenizer, filename):
    value = (
        "\ufeff# Clothes\r\n\r\n"
        + ("Café e\u0301 👩🏽‍🦰 舞蹈课。 Bring water! <|endoftext|>\r\n" * 400)
        + "\r# Clothes\r\nThe ending must remain."
    )
    chunker = Chunker(source(value, filename), tokenizer)
    records = assert_invariants(chunker, tokenizer)
    assert any(s["role"] == "overlap" for r in records for s in r["source_spans"])
    assert chunker.records() is not chunker.records()
    if filename.endswith(".md"):
        assert len(chunker.sections) == 2
        assert chunker.sections[0].heading_ids != chunker.sections[1].heading_ids


def test_small_structure_is_kept_and_large_parents_are_bounded(tokenizer):
    small_list = "- Trial fee: $20.\n- Approval required.\n\n"
    small_table = "| Term | Fee |\n| --- | --- |\n| One | $192 |\n\n"
    small_example = "```text\nAn example with <script>alert(1)</script>.\n```\n\n"
    value = "# Policy\n\n" + ("A paragraph about refunds and exceptions. " * 35 + "\n\n") * 20
    value += small_list + small_table + small_example
    chunker = Chunker(source(value), tokenizer)
    records = assert_invariants(chunker, tokenizer)
    passages = [record for record in records if record["kind"] == "passage"]
    assert len([r for r in records if r["kind"] == "parent"]) > 1
    for block in (small_list, small_table, small_example):
        assert any(block in record["text"] for record in passages)


def test_long_table_rows_and_oversized_headers_have_separate_provenance(tokenizer):
    header = "| Term | " + "Very long heading " * 500 + "|\r\n| --- | --- |\r\n"
    value = "# Terms\r\n\r\n" + header
    value += "| Term One | " + "Conditions and exceptions. " * 800 + "|\r\n"
    value += "".join(f"| Term {i} | Approval is required. |\r\n" for i in range(100))
    chunker = Chunker(source(value), tokenizer)
    records = assert_invariants(chunker, tokenizer)
    assert "table_header_context_truncated" in chunker.warnings
    copied = [
        span
        for record in records
        for span in record["source_spans"]
        if span["role"] == "table_header"
    ]
    assert copied and all(value[s["start"] : s["end"]].startswith("| Term |") for s in copied)


def test_giant_heading_sentence_and_code_cannot_bypass_limits(tokenizer):
    value = "# " + "Huge heading " * 700 + "\n\n"
    value += "z" * 40_000 + "\n\n```md\n# Not a real heading\n" + "code " * 10_000 + "\n```\n"
    chunker = Chunker(source(value), tokenizer)
    assert len(chunker.sections) == 1
    assert "heading_prefix_truncated" in chunker.warnings
    assert_invariants(chunker, tokenizer)


def test_repeated_runs_positions_and_revision_identity(tokenizer):
    value = "# Same\nIdentical words.\n\n# Same\nIdentical words.\n"
    original = source(value, document_id="d", revision=1)
    first = list(Chunker(original, tokenizer).records())
    assert first == list(Chunker(original, tokenizer).records())
    assert len({r["id"] for r in first}) == len(first)
    changed = list(Chunker(replace(original, revision=2), tokenizer).records())
    assert {r["id"] for r in first}.isdisjoint(r["id"] for r in changed)


def test_metadata_and_configuration_changes_have_distinct_identities(tokenizer, monkeypatch):
    original = source("# Policy\nTeacher approval is required.")
    first = list(Chunker(original, tokenizer).records())
    first_ids = {record["id"] for record in first}
    retitled = list(Chunker(replace(original, title="New title"), tokenizer).records())
    assert first_ids.isdisjoint(record["id"] for record in retitled)
    assert first[0]["text_sha256"] != retitled[0]["text_sha256"]
    dated = list(Chunker(replace(original, effective_from="2027-01-01"), tokenizer).records())
    assert first_ids.isdisjoint(record["id"] for record in dated)
    assert first[0]["text_sha256"] == dated[0]["text_sha256"]
    changed_config = replace(chunking_engine.Config(), chunker_version="next-version")
    monkeypatch.setattr(chunking_engine, "Config", lambda: changed_config)
    changed = list(Chunker(original, tokenizer).records())
    assert first_ids.isdisjoint(record["id"] for record in changed)
    assert first[0]["config_hash"] != changed[0]["config_hash"]


@pytest.mark.parametrize("raw", [b"\xff", b"\x00text", b" \r\n", b"\xef\xbb\xbf"])
def test_invalid_file_inputs_are_rejected(tmp_path, raw):
    path = tmp_path / "input.md"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        load_file(path)


def test_file_limit_and_exact_raw_bytes(tmp_path):
    path = tmp_path / "input.txt"
    raw = b"\xef\xbb\xbf\r\n" + b"a" * (10_000_000 - 5)
    path.write_bytes(raw)
    result = load_file(path)
    assert result.text.encode() == raw and result.byte_size == 10_000_000
    assert result.sha256 == hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw + b"a")
    with pytest.raises(ValueError, match="10,000,000"):
        load_file(path)


def test_source_hash_extension_and_title_validation(tmp_path):
    with pytest.raises(ValueError, match="SHA-256"):
        replace(source("Good text"), sha256="0" * 64).validate()
    with pytest.raises(ValueError, match="md or .txt"):
        source("Good text", "input.pdf").validate()
    path = tmp_path / "input.md"
    path.write_text("Good text")
    with pytest.raises(ValueError, match="title"):
        load_file(path, "")


def test_export_is_offline_complete_deterministic_and_plain_text(
    tokenizer, tokenizer_cache, tmp_path, monkeypatch
):
    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected network access")

    monkeypatch.setattr(socket, "socket", no_network)
    value = "# Safety\n\n<script>alert(1)</script>\n\n```\n" + "`" * 20 + "\n```\n"
    src = source(value)
    manifests = []
    for name in ("one", "two"):
        chunker = Chunker(src, Tokenizer(tokenizer_cache))
        target = tmp_path / name
        manifests.append(export(chunker, target))
        assert (target / "source.txt").read_bytes() == value.encode()
        assert "<script>alert(1)</script>" in (target / "report.txt").read_text()
        for filename, metadata in manifests[-1]["files"].items():
            raw = (target / filename).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == metadata["sha256"]
            assert len(raw) == metadata["bytes"]
        for filename in ("parents.jsonl", "passages.jsonl", "headings.jsonl", "sections.jsonl"):
            assert all(json.loads(line) for line in (target / filename).read_text().splitlines())
        assert manifests[-1]["complete"] is True
        assert manifests[-1]["coverage_characters"] == {"parent": len(value), "passage": len(value)}
    assert manifests[0]["files"] == manifests[1]["files"]
    with pytest.raises(FileExistsError):
        export(Chunker(src, tokenizer), tmp_path / "one")


def test_failed_export_cleans_staging_and_reservation(tokenizer, tmp_path, monkeypatch):
    chunker = Chunker(source("Good content."), tokenizer)

    def broken():
        yield from ()
        raise RuntimeError("Interrupted")

    monkeypatch.setattr(chunker, "records", broken)
    with pytest.raises(RuntimeError, match="Interrupted"):
        export(chunker, tmp_path / "output")
    assert list(tmp_path.iterdir()) == []


def test_missing_and_corrupt_tokenizer_never_download(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected download")

    monkeypatch.setattr(socket, "socket", no_network)
    with pytest.raises(ValueError, match="prepare-tokenizer"):
        Tokenizer(tmp_path)
    (tmp_path / "cl100k_base.tiktoken").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="corrupt"):
        Tokenizer(tmp_path)


def test_cli_missing_asset_does_not_publish_output(tmp_path):
    input_file = tmp_path / "input.md"
    input_file.write_text("# Policy\nWater is required.")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "studio_copilot.documents.chunking",
            "--file",
            str(input_file),
            "--output-dir",
            str(tmp_path / "out"),
            "--tokenizer-cache",
            str(tmp_path / "missing"),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1 and "--prepare-tokenizer" in result.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--document-id", "f790b148-caa1-41e5-bb29-b63cc6f2fca0", "--output-dir", "unused"],
        ["--file", "input.md", "--revision", "1", "--output-dir", "unused"],
        ["--prepare-tokenizer", "--output-dir", "unused"],
    ],
)
def test_cli_rejects_ambiguous_inputs_before_work(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_cli_complete_export(tokenizer_cache, tmp_path):
    path = tmp_path / "input.md"
    path.write_bytes(b"# Policy\r\n\r\nBring water.")
    args = [
        "--file",
        str(path),
        "--output-dir",
        str(tmp_path / "out"),
        "--tokenizer-cache",
        str(tokenizer_cache),
    ]
    assert main(args) == 0
    assert json.loads((tmp_path / "out" / "manifest.json").read_text())["complete"]
    assert main(args) == 1
