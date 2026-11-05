# Offline document chunking

This milestone prepares and inspects documents locally. It adds no API routes, database tables, background workers, UI, embeddings, keyword index, publication, or agent document access. The search text is ready for a later indexing stage; no keyword list needs to be predicted during splitting.

## Prepare and run

From `backend/`, install the locked dependencies and explicitly prepare the tokenizer:

```sh
uv sync --locked --group dev
uv run python -m studio_copilot.documents.chunking --prepare-tokenizer
```

Preparation downloads the public `cl100k_base` vocabulary and verifies its pinned SHA-256. It needs network access, but no API key or inference call. The default cache is `$XDG_CACHE_HOME/studio-copilot`, or `~/.cache/studio-copilot`. Use `--tokenizer-cache PATH` on both preparation and processing to choose another directory. Missing or corrupt assets cause a clear processing error; processing never starts a tokenizer download.

Run against a local file:

```sh
uv run python -m studio_copilot.documents.chunking \
  --file /absolute/path/handbook.md \
  --title "Studio handbook" \
  --output-dir /tmp/handbook-chunks
```

Or read an explicitly selected saved revision:

```sh
uv run --env-file .env python -m studio_copilot.documents.chunking \
  --document-id DOCUMENT_UUID --revision 1 \
  --output-dir /tmp/revision-1-chunks
```

The local-file title defaults to the filename stem. Revision input uses the stored title and dates; `--title` cannot override them. A read-only PostgreSQL transaction materializes all requested revision fields in one SELECT, then closes before splitting. A concurrent replacement cannot change the selected source. A concurrent deletion yields either the complete selected snapshot or a not-found error. No document locks or writes are performed. Database configuration errors are reported without printing connection credentials.

Sources must be UTF-8 `.md` or `.txt`, at most **10,000,000 bytes**, without NUL or blank/BOM-only content. Legacy blank revisions must be corrected before processing. Raw byte size and SHA-256 are checked; BOM, CRLF, lone CR and Unicode are preserved. Local hashes are marked `file_bytes`; stored revisions retain their ingestion hash provenance. Effective dates come from revision metadata, never from inferred body text.

Output must be a new directory. The exporter reserves it exclusively, writes to a temporary sibling, and atomically replaces the empty reservation only after all files and the manifest succeed. Exceptions, Ctrl+C and normal SIGTERM remove incomplete exports. A hard kill or machine crash can leave temporary files or an empty reservation; no completed manifest is published there. Existing directories, files and symlinks are never overwritten.

## Algorithm and limits

| Item                            | Default                                               |
| ------------------------------- | ----------------------------------------------------- |
| Search passage target / maximum | 600 / 900 tokens                                      |
| Parent maximum                  | 2,400 tokens                                          |
| Copied overlap maximum          | 80 source tokens, within one parent                   |
| Generated title/path prefix     | At most 128 tokens                                    |
| Copied table-header context     | At most 128 tokens                                    |
| Tokenizer / parser              | tiktoken 0.12.0, `cl100k_base` / markdown-it-py 4.0.0 |

CommonMark block parsing, with table support, identifies headings, paragraphs, lists, tables and code. It does not render Markdown, execute HTML or fetch links. Parents do not cross heading sections. Whole blocks are kept when they fit; oversized blocks split at line/paragraph boundaries, then sentence punctuation, and finally Unicode character boundaries. Small sections remain small rather than being padded to 600 tokens. Long tables split between rows when possible, with header context copied into continuations; oversized rows and headers are also split. Full original header text remains covered even if the copied context is truncated.

Each parent has one or more passages. Overlap copies a suffix from the immediately preceding passage's primary content within the same parent; it shrinks or disappears if needed to keep the final passage within 900 tokens. Parent expansion is represented by links only: no drafting model is called.

Final rendered text is retokenized as one input, including prefix, copied headers and overlap. BPE counts are not additive. Arbitrary token slices are converted only to valid Unicode prefix boundaries, and actual bodies are always sliced from the unchanged source. Literal strings such as `<|endoftext|>` remain ordinary document text.

Tokenizer work windows are bounded to 8,192 characters. This can underfill parents or passages on token-sparse sources, and prevents giant lines from being encoded repeatedly as a growing full document. The source and ordinary block structure are still materialized; this is not a constant-memory pipeline.

An additional complexity guard runs before Markdown AST allocation. More than **100,000 logical lines**, or more than **100,000 `|` characters** in Markdown, switches to coarse paragraph/line units of at most 4,096 characters. The manifest/report explicitly warns `structure_complexity_fallback`. Full text coverage and token limits still apply, but there are no inferred headings or copied table headers in this mode. Inspect such exports; fallback is not evidence that policy structure has been understood. All thresholds are included in the versioned configuration hash.

## Inspection files and provenance

| File             | Contents                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `source.txt`     | Exact UTF-8 source bytes, for offline offset checks                                               |
| `headings.jsonl` | Full heading text once, heading ancestry and original source location                             |
| `sections.jsonl` | Section boundaries and heading references                                                         |
| `parents.jsonl`  | Bounded context records                                                                           |
| `passages.jsonl` | Search records with parent and neighbour links                                                    |
| `report.txt`     | Plain-text sample of the first 12 passages, counts and warnings                                   |
| `manifest.json`  | Completion marker, source metadata, configuration, counts, coverage, file hashes and measurements |

The report uses `.txt` so hostile HTML or closing Markdown fences remain literal text. JSONL is written incrementally; the engine buffers only bounded record lookahead rather than all rendered chunks.

Parent/passage records contain `id`, `kind`, `source_id`, `section_id`, `heading_ids`, `parent_id`, `previous_id`, `next_id`, `source_spans`, `prefix`, `text`, `token_count`, `text_sha256` and `config_hash`. Passage neighbours stay within the parent; parent neighbours follow the whole source. Heading paths are reconstructed from shared registry references, avoiding repeated giant heading strings in every record.

All source spans are **zero-based, end-exclusive Unicode character offsets**, compatible with revision-preview positions. Each record distinguishes:

- `body`: primary content owned by this record; in order these spans reconstruct the complete source independently for each layer.
- `overlap`: a copied suffix from the preceding passage.
- `table_header`: copied context from an earlier location, not falsely presented as contiguous with the body.

`prefix` is generated context. To reconstruct `text`, join prefix, any copied table header, and concatenated overlap/body slices with two newlines. Markdown syntax and blank separators remain in primary spans. Stable IDs hash source identity/metadata, complete versioned configuration, kind, section and primary range. Repeated text at different positions has different IDs. The text hash covers the actual final rendered input; the source hash covers raw source bytes. Timing values do not affect IDs.

## Verification

Prepare the tokenizer before running pytest; CI performs this as an explicit setup step. Tests read the default cache, or the directory in `STUDIO_TOKENIZER_CACHE`:

```sh
uv run python -m studio_copilot.documents.chunking --prepare-tokenizer
uv run --env-file .env.example pytest
uv run ruff check .
uv run ruff format --check .
```

PostgreSQL tests use the repository's isolated migrated test schemas and require `TEST_DATABASE_URL`. Tests cover pinned reads during replacement/deletion, exact source reconstruction, final token budgets, tiny Unicode token cuts, repeated headings, long rows/headers, literal HTML, no-network processing, deterministic exports, output protection, and interrupted/disk-failure cleanup. They do not establish retrieval recall or answer faithfulness.

Run the separate large-file benchmark explicitly:

```sh
uv run python scripts/benchmark_chunking.py \
  --output-dir /tmp/chunking-benchmark
```

Every fixture is exactly 10,000,000 bytes: one huge line, dense short blocks, repeated headings, Unicode-heavy paragraphs, a long table, fenced code, and a giant table row. Each case runs the real CLI in a fresh process, then independently retokenizes every exported parent/passage and checks primary coverage, final source marker and hashes. `results.json` records measured elapsed time, process peak RSS, counts and warnings. CLI timing covers source/tokenizer loading, parsing and export; it excludes Python import startup and independent verification. Peak RSS is the process lifetime high-water mark, not incremental engine allocation. These are reproducible synthetic measurements, not a production SLA.

### Measured results

Measured on macOS 26.5.2 (x86_64), Python 3.12.13, using the benchmark above. All seven cases independently passed exact coverage, source-hash and final token-limit verification. Times are single runs, not averages.

| Exact 10 MB source     | CLI seconds | Process peak MiB | Parents / passages | Structural fallback |
| ---------------------- | ----------: | ---------------: | -----------------: | ------------------- |
| One huge unbroken line |      129.13 |            147.6 |      1,221 / 3,662 | No                  |
| Dense short blocks     |       49.02 |            149.6 |     4,884 / 12,210 | Yes                 |
| Repeated headings      |       21.69 |            149.2 |      2,442 / 4,885 | Yes                 |
| Unicode paragraphs     |       13.45 |            171.9 |      2,326 / 9,302 | Yes                 |
| Long table             |       11.33 |            146.7 |      1,221 / 4,883 | Yes                 |
| Long fenced code       |       12.79 |            145.6 |      1,229 / 4,914 | Yes                 |
| Giant table row        |        7.64 |            149.3 |      1,224 / 2,446 | No                  |

The sample studio handbook, with its actual document title supplied, produced **12 parents and 12 passages**, maximum **493 tokens**, no warnings, in **0.124 seconds** (111.4 MiB process peak). Its policy sections fit whole; forcing each one to reach 600 tokens would add irrelevant context. Manual inspection covered term-table headers/rows, fee conditions, makeup restrictions and examples, withdrawal exceptions, and the final section. Unit fixtures additionally exercise lists, long headers/rows, code and hostile HTML.

The unbroken-line case remains relatively slow: bounded windows prevent unbounded full-document tokenization but do not make BPE on long words inexpensive. The fallback cases preserve evidence text while losing inferred section/table context, which is explicitly visible for inspection. These results establish safe preparation and resource observations; retrieval quality, citations in generated answers and faithfulness remain unmeasured until later milestones.
