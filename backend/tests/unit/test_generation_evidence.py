"""Independent evidence provenance checks; no database, tokenizer download, or models."""

from copy import deepcopy
from hashlib import sha256

import pytest


class Characters:
    def count(self, text):
        return len(text)


def source(text="\ufeffCafé\r\n中文🙂 policy.\r\nException: no fee."):
    return dict(
        document_id="00000000-0000-0000-0000-000000000001",
        revision=1,
        title="Policy",
        filename="policy.md",
        text=text,
        sha256=sha256(text.encode("utf-8")).hexdigest(),
        effective_from="2027-01-01",
        effective_to="2027-12-31",
    )


def artifact(*, text=None, spans=None, prefix="Policy / Generated heading\n\n", blocks=True):
    from studio_copilot.documents.generation.evidence import make_block, seal_artifact

    original = source() if text is None else source(text)
    if spans is None:
        spans = [dict(start=0, end=len(original["text"]), role="body")]
    return seal_artifact(
        dict(
            version="generation-evidence-v1",
            case_id="case-one",
            question="What is the exception?",
            as_of="2027-06-01",
            variant="actual",
            sources=[original],
            blocks=[make_block(original, "parent-one", "parent", prefix, spans)] if blocks else [],
        )
    )


def test_unicode_crlf_bom_and_original_ranges_are_not_normalized():
    from studio_copilot.documents.generation.evidence import validate_artifact

    value = artifact()
    before = deepcopy(value)
    validate_artifact(value, Characters())
    assert value == before
    assert value["sources"][0]["text"] == "\ufeffCafé\r\n中文🙂 policy.\r\nException: no fee."
    assert value["blocks"][0]["text"].endswith(value["sources"][0]["text"])


@pytest.mark.parametrize("damage", ["question", "as_of", "revision", "text", "range", "prefix"])
def test_altered_artifact_cannot_pass_envelope_checksum(damage):
    from studio_copilot.documents.generation.evidence import validate_artifact

    value = artifact()
    if damage == "question":
        value["question"] = "Different question?"
    elif damage == "as_of":
        value["as_of"] = "2027-07-01"
    elif damage == "revision":
        value["sources"][0]["revision"] = 2
    elif damage == "text":
        value["sources"][0]["text"] += "forged"
    elif damage == "prefix":
        value["blocks"][0]["text"] = "forged generated heading"
    else:
        value["blocks"][0]["fragments"][0]["end"] = 999999
    with pytest.raises(Exception):
        validate_artifact(value, Characters())


@pytest.mark.parametrize("damage", ["source_hash", "block_text", "date"])
def test_resealing_does_not_bypass_source_relationships(damage):
    from studio_copilot.documents.generation.evidence import seal_artifact, validate_artifact

    value = artifact()
    if damage == "source_hash":
        value["sources"][0]["text"] += "forged"
    elif damage == "block_text":
        value["blocks"][0]["text"] += "Invented evidence"
    else:
        value["as_of"] = "2028-01-01"
    # The envelope is an integrity checksum, not a signature. Relationships and
    # original hashes still require separate validation after envelope resealing.
    value = seal_artifact(value)
    with pytest.raises(Exception):
        validate_artifact(value, Characters())


def test_noncontiguous_copied_table_header_retains_original_text_ranges():
    from studio_copilot.documents.generation.evidence import validate_artifact

    text = "| Option | Fee |\r\nOther section\r\n| Adult | 25 |\r\n"
    row = text.index("| Adult")
    value = artifact(
        text=text,
        spans=[
            dict(start=0, end=text.index("Other"), role="table_header"),
            dict(start=row, end=len(text), role="body"),
        ],
    )
    validate_artifact(value, Characters())
    assert "Other section" not in value["blocks"][0]["text"]
    assert "| Option | Fee |" in value["blocks"][0]["text"]
    assert "| Adult | 25 |" in value["blocks"][0]["text"]


def test_final_joined_evidence_budget_is_bounded():
    from studio_copilot.documents.generation.evidence import validate_artifact

    value = artifact(text="x" * 12001, prefix="")
    with pytest.raises(Exception):
        validate_artifact(value, Characters())


def test_empty_evidence_is_valid_for_deterministic_abstention():
    from studio_copilot.documents.generation.evidence import validate_artifact

    validate_artifact(artifact(blocks=False), Characters())


def test_exact_quote_resolves_unicode_offsets_in_original_not_rendered_prefix():
    from studio_copilot.documents.generation.contracts import Citation
    from studio_copilot.documents.generation.evidence import resolve_quote

    value = artifact()
    quote = "中文🙂 policy.\r\nException: no fee."
    resolved = resolve_quote(value, Citation(evidence_id=value["blocks"][0]["id"], quote=quote))
    original = value["sources"][0]["text"]
    assert resolved["start"] == original.index(quote)
    assert resolved["end"] == original.index(quote) + len(quote)
    assert original[resolved["start"] : resolved["end"]] == quote
    assert resolved["revision"] == 1
    assert resolved["sha256"] == value["sources"][0]["sha256"]


def test_disconnected_fragments_cannot_forge_a_quote_crossing_generated_separator():
    from studio_copilot.documents.generation.contracts import Citation
    from studio_copilot.documents.generation.evidence import resolve_quote

    value = artifact(
        text="Rule. HIDDEN CONDITION. Exception.",
        spans=[dict(start=0, end=5, role="body"), dict(start=23, end=33, role="body")],
        prefix="",
    )
    assert (
        resolve_quote(
            value,
            Citation(evidence_id=value["blocks"][0]["id"], quote="Rule.\n\nException."),
        )
        is None
    )


def test_copied_header_quote_resolves_to_original_header_role():
    from studio_copilot.documents.generation.contracts import Citation
    from studio_copilot.documents.generation.evidence import resolve_quote

    value = artifact(
        text="| Fee |\nUnprovided middle\n| 25 |",
        spans=[dict(start=0, end=7, role="table_header")],
    )
    resolved = resolve_quote(value, Citation(evidence_id=value["blocks"][0]["id"], quote="Fee"))
    assert resolved["start"] == 2
    assert resolved["end"] == 5
    assert resolved["role"] == "table_header"


def test_whitespace_only_quote_never_counts_as_support():
    from studio_copilot.documents.generation.contracts import Citation
    from studio_copilot.documents.generation.evidence import resolve_quote

    value = artifact()
    assert (
        resolve_quote(value, Citation(evidence_id=value["blocks"][0]["id"], quote="\r\n")) is None
    )


def test_model_payload_contains_only_provided_fragments_not_entire_snapshot_or_labels():
    from studio_copilot.documents.generation.evidence import model_payload

    value = artifact(
        text="Allowed policy. SECRET UNPROVIDED SOURCE TAIL",
        spans=[dict(start=0, end=15, role="body")],
        prefix="",
    )
    payload = model_payload(value)
    assert payload["question"] == value["question"]
    assert payload["as_of"] == value["as_of"]
    assert payload["evidence"][0]["text"] == "Allowed policy."
    assert "SECRET UNPROVIDED" not in str(payload)
    assert "required_facts" not in payload
    assert "expected_standard_status" not in payload
