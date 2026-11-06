# Revision-pinned document embeddings

This milestone adds an explicitly invoked CLI that saves chunks and passage vectors in PostgreSQL. Completing a run does not publish the document or make it available to the agent. There are no new UI/API routes, workers, retrieval indexes, search, or generation calls. The internal embedding tables are excluded from the existing database browser.

## Setup and commands

Use the backend environment and an existing immutable document revision. Local files and chunk exports are not embedding inputs; upload them first. Run commands from `backend/`:

```bash
uv sync --locked
# Start the configured PostgreSQL container after reviewing the backup guidance below.
docker compose -f ../compose.yaml up -d --wait db
uv run --env-file .env alembic upgrade head
# Explicit tokenizer preparation; subsequent chunking does not download resources.
uv run python -m studio_copilot.documents.chunking --prepare-tokenizer

uv run --env-file .env python -m studio_copilot.documents.embedding plan \
  --document-id UUID --revision 1
uv run --env-file .env python -m studio_copilot.documents.embedding run \
  --document-id UUID --revision 1
uv run --env-file .env python -m studio_copilot.documents.embedding status \
  --run-id UUID
```

Check `python -m studio_copilot.documents.chunking --help` for tokenizer cache configuration. `plan` reads the requested revision and existing cache, counts chunks and estimated uncached tokens, and performs no database writes or API calls. Estimates depend on cache state and are not a price quote. `status` reads persisted progress without loading passage texts/vectors. Neither command requires an API key.

**`run` sends the exact search-passage text to the configured embedding provider and incurs API usage.** Set `OPENAI_API_KEY` privately. The default is OpenAI `text-embedding-3-small`, 1,536 dimensions. `OPENAI_EMBEDDING_MODEL` is separate from the agent generation model and currently accepts only this model. `OPENAI_EMBEDDING_BASE_URL`, falling back to `OPENAI_BASE_URL`, selects the actual endpoint. Endpoint credentials, queries, and fragments are rejected; do not put secrets in endpoint paths. Use the same endpoint configuration when inspecting/reusing a run.

An optional, explicitly paid connectivity check sends two fixed fictional sentences and makes no database writes:

```bash
uv run --env-file .env python -m studio_copilot.documents.embedding smoke
```

This check is separate from normal tests; no paid API call is needed to validate the implementation.

## What is saved

- `embedding_runs`: immutable source/configuration identity, source metadata, heading map, warnings, progress, token usage, and execution lease.
- `document_chunks`: exact parent and search-passage text, source ranges, heading/parent/neighbour metadata, token count, input SHA-256, and optional vector link. Parent text is saved but never embedded.
- `embedding_vectors`: shared project-local `vector(1536)` cache with profile/input hashes and no original text.

The existing chunker supplies the final passage input, including its bounded title/section prefix, overlap, and copied table header. It retains the 600 target / 900 maximum passage budget and 2,400-token parent maximum. No keyword extraction, instruction prompt, Unicode normalization, newline conversion, or manual vector normalization is added. The source revision is read completely and its transaction closed before chunking or provider work.

The cache identity includes the actual endpoint, model, dimensions, input-format version, and SHA-256 of exact input text. Changing a title can change passage inputs. Identical text at different source locations keeps distinct chunk IDs but can share a vector. The first committed vector is retained when concurrent runs obtain the same key; cached vectors are not overwritten. This is a single-project cache, not a tenant authorization boundary.

## Recovery, limits, and concurrency

Runs are unique per document/revision/chunker/profile. Repeating a completed run is a no-op. Repeating an interrupted run regenerates and verifies any partial chunk checkpoint, then embeds only missing committed inputs. Chunk records are written in batches of at most 64; provider batches contain at most 64 unique passages, processed serially. Whole source text, parser state, heading maps, and deduplication metadata may still be materialized: this is bounded by the 10,000,000-byte ingestion limit, not constant memory.

Every execution owns a random token and a 300-second database-clock lease. Claims lock the run row; renewal, checkpoints, failure, and completion check both token and unexpired lease. An expired owner cannot renew itself even before takeover. Provider requests occur outside database transactions. A response arriving after deletion, expiry, or takeover cannot insert cache entries or attach vectors. Normal interruption records failure when possible; a killed process or disconnected database recovers after lease expiry.

The SDK has retries disabled. The wrapper makes at most three total attempts for transient connection/status failures, with jittered backoff or bounded `Retry-After` delays (maximum 60 seconds). Each request uses a 30-second network timeout; this is not a strict total wall-clock deadline. Permanent errors and malformed vectors are not retried. Counts, unique indices, response model, dimensions, finite float32 values, and unit norm are checked before persistence. PostgreSQL also enforces dimensions, norm, and profile/input foreign keys.

Checkpointing does not guarantee exactly-once billing: an API success followed by a lost response or failed commit can require another paid call. Reported token usage includes successfully checkpointed responses, not an authoritative provider billing ledger.

Replacing a document cannot redirect a pinned run to the new revision. Deleting a document cascades its revisions, runs, and chunks. Shared cache vectors remain, including orphan vectors; this milestone has no automatic cache-retention policy. A completed embedding run is preparation only and grants no retrieval permission.

## PostgreSQL upgrade and migration

Compose and CI use `pgvector/pgvector:0.8.7-pg18-trixie` (PostgreSQL 18.6). Before replacing an existing container, verify server major/minor version, data-directory layout, volume, port, and image version. Back up every application/test database and roles, and verify restoration in an isolated container. Keep the existing data volume and environment; do not run `down -v` or initialize a new production volume as an upgrade shortcut.

The migration installs `vector` in `public` and creates three application tables. The migration account needs extension-creation privileges, or an administrator must install it first. Test schemas use `search_path=<isolated schema>,public`. Downgrading drops only these three tables, never the shared extension. No HNSW, full-text index, or publication schema is created.

For the local upgrade on 2026-11-06, both databases and roles were backed up, both database dumps restored successfully into an isolated container, and the existing PostgreSQL 18.6 volume was reused with the same port. Application migration checks and tests verify schema parity and extension-preserving downgrade/upgrade.

## Validation and measurement

Provider tests use fakes. PostgreSQL integration tests exercise resume/checkpoints, concurrent claims, expired-owner fencing, deletion during provider calls, cache/profile isolation, schema constraints, and the actual subprocess CLI/SDK against a local fake HTTP provider. They do not invoke OpenAI or prove semantic retrieval quality.

Run the reproducible large-file benchmark against a dedicated test database:

```bash
TEST_DATABASE_URL=postgresql+psycopg://.../studio_copilot_test \
  uv run python scripts/benchmark_embeddings.py \
  --output-dir /tmp/studio-embedding-benchmark \
  --tokenizer-cache /tmp/studio-chunking-tokenizer
```

Each of seven fixtures is exactly 10,000,000 bytes: a single giant paragraph without line breaks, dense short blocks, repeated headings, Chinese/emoji, a long table, long code, and a giant table row. Each case runs in a fresh subprocess and isolated schema with the real chunker, PostgreSQL, and a deterministic fake embedding provider. It independently checks rendered text/source coverage, token budgets, stored vector dimensions/norm, parent links, and a no-op repeat run. These fixtures are repetitive and exercise deduplication heavily; they do not establish high-uniqueness vector throughput, provider latency/cost, or retrieval recall.

Measured on 2026-11-06, macOS 26.5.2 arm64, Python 3.12.13, PostgreSQL 18.6 / pgvector 0.8.7. Other local validation workloads ran concurrently, so timings are representative observations, not an SLA. Pipeline time includes revision load, chunking, persistence, and fake-provider work; verification is measured separately. Peak RSS includes the child process's verification phase.

| Exact 10 MB case | Pipeline seconds | Verification seconds | Peak RSS MiB | Parents | Passages | New vectors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

The 600/900/2,400 parameters remain versioned starting values; retrieval quality must be evaluated in the retrieval milestone.

| single-line | 156.723 | 22.838 | 218.71 | 1221 | 3662 | 4 |
| short-blocks | 69.424 | 8.201 | 199.54 | 4884 | 12210 | 7 |
| many-headings | 26.09 | 3.752 | 218.78 | 2442 | 4885 | 6 |
| unicode | 19.679 | 2.31 | 277.14 | 2326 | 9302 | 8 |
| table | 14.792 | 2.452 | 220.8 | 1221 | 4883 | 5 |
| code | 15.736 | 2.574 | 224.7 | 1229 | 4914 | 6 |
| giant-row | 10.061 | 1.562 | 234.48 | 1224 | 2446 | 6 |

[Machine-readable measurements](measurements/document-embeddings-2026-11-06.json) include cache reuse and explicit structure-fallback warnings. Every case passed coverage, token, vector/link, complete-state, and replay checks with zero model calls.
