# Explicit document retrieval

This milestone searches explicitly selected immutable document revisions and returns evidence for inspection. It does not publish documents, expose them to the agent, generate answers, or authorize business actions. No API routes, UI, workers, reranker models, or HNSW indexes are added. The CLI has local operator access to unpublished content; it is not a future agent permission boundary.

## Setup and usage

From `backend/`, use the existing PostgreSQL/pgvector environment and checksum-verified tokenizer cache:

```bash
uv sync --locked
uv run --env-file .env alembic upgrade head
uv run python -m studio_copilot.documents.chunking --prepare-tokenizer

# Completely local keyword search: no API key or embedding request.
uv run --env-file .env python -m studio_copilot.documents.retrieval search \
  --run-id UUID --query 'cancellation notice' --as-of 2027-02-01 \
  --mode keyword --format text

# Paid question embedding, followed by local keyword/vector search.
uv run --env-file .env python -m studio_copilot.documents.retrieval search \
  --run-id UUID --run-id UUID --query 'Can I make up a missed class?' \
  --as-of 2027-02-01 --mode hybrid --allow-api --format json
```

The default mode is `hybrid`; the default format is `text`. Repeat `--run-id` for a multi-document corpus (maximum 100 distinct runs). Every selected run must exist and be complete, with a valid source revision and mutually compatible embedding profiles. Only one run/revision per document is allowed. Duplicate run IDs are collapsed. Selection never follows a document's mutable current-revision pointer.

`--as-of` is mandatory. Effective dates are inclusive and absent boundaries are open-ended; a period or relative date is not inferred. The question must be nonblank, contain no NUL, and fit both 4,096 Unicode characters and 512 `cl100k_base` tokens. Oversized input is rejected, not truncated. Tokenizer preparation is explicit; search does not download resources.

For vector/hybrid mode, `--allow-api` explicitly permits sending the question to the embedding provider and incurring usage. Configure `OPENAI_API_KEY` and the same `OPENAI_EMBEDDING_BASE_URL`/model profile used by selected runs. A configuration mismatch fails before the request. Chunk vectors already exist in PostgreSQL and are not sent to the provider again. Keyword mode does not require a matching current provider configuration or an API key.

## What the engine does

1. Validate the selected source/configuration identities in a short read-only transaction. If all selected sources are outside the requested date, do not call the provider.
2. For vector/hybrid searches, embed only the question using the existing provider, outside database transactions. Its vector validation, retry policy, and network timeouts also apply here.
3. Start one repeatable-read, read-only snapshot. Revalidate selected runs, then perform both search routes, duplicate-source resolution, and parent-context reads within that snapshot.
4. Keyword search uses `to_tsvector('english', passage_text)`, `websearch_to_tsquery`, and `ts_rank_cd`, backed by a partial GIN expression index on passages. It normalizes English word forms, not meaning. Ordinary query terms are AND-connected: long conversational queries can be restrictive. There is no LLM keyword extraction, synonym expansion, spelling correction, `pg_trgm`, or BM25 implementation.
5. Vector search computes exact cosine distance against the distinct eligible cached vectors. Run, completion, revision validity, and effective-date restrictions apply before candidate selection. Orphan/shared cache vectors cannot enter a search without an eligible passage link.
6. Each route returns at most 20 distinct input-text hashes. RRF sums `1/(60 + rank)` across the routes; ties use the input hash. This combines existing search ranks; no cross-encoder or LLM reranker evaluates candidates.
7. Return at most six distinct passage texts. The representative source is deterministic by document ID, revision, ordinal, and chunk ID. Retain up to three additional source references and report the total eligible occurrence count, so repeated boilerplate does not exhaust the candidate limit.
8. Preserve all selected passage evidence before attempting parent expansion. Replace passages sharing a parent with that parent once if it fits. Count the final texts joined with two newlines against a 12,000-token budget; retain original passages and warn when a parent cannot fit.

The expression index covers existing and future passage text automatically; migration does not change chunks or generate embeddings. Exact vector search establishes a correctness and latency baseline. HNSW requires a separate measured decision, including filtered-search recall and shared-cache index design.

## Results, concurrency, and failure

JSON contains selected source identities, passage/chunk and parent IDs, revision, title, heading path, effective dates, half-open original character ranges, preserved text, copied-prefix metadata, alternative references, keyword/vector ranks and scores, RRF score, bounded evidence, warnings, usage, candidate hashes, and stage timings. Text output shows the main evidence and references. The CLI is a plain-text/local JSON interface; document HTML is never executed. Generated prefixes are distinguished from source ranges. Scores are not probabilities of correctness.

Question text is not written into database history or tracing. No query-vector cache is introduced. The only source text printed is the explicit local result; normal errors omit credentials, provider bodies, and document contents. Avoid sharing CLI output containing private documents.

A replacement cannot redirect a selected run to a new revision. A delete before the final snapshot fails the request; a delete after that snapshot starts may leave the old evidence visible to that in-flight local search through PostgreSQL MVCC. New searches cannot access the deleted run. The two search routes and parent context never mix snapshots.

Provider errors or invalid response vectors in hybrid mode return keyword-only results with `degraded=true` and a warning. Vector-only mode fails. Missing keys, invalid configuration, incompatible profiles, missing/incomplete sources, and database failures do not silently degrade. Inherited structure-complexity warnings are surfaced. Empty results do not establish that a question is unanswerable; vector search can return weak matches even for a question absent from the source. Evidence sufficiency and abstention belong to a later generation stage.

## Labelled evaluation

The repository includes a fictional 2027 handbook and 40 manually authored questions in `backend/tests/fixtures/`. Labels point to original Unicode character positions, not chunk IDs, and include exact expected text, effective dates, no-answer cases, and multiple required evidence spans. There are 20 tuning questions and 20 held-out questions; the policies overlap across splits, so this is not an independent-domain generalization test.

Upload that exact handbook, save its optional effective dates as 2027-01-01 through 2027-12-31, and explicitly prepare an embedding run first. Then run:

```bash
uv run --env-file .env python -m studio_copilot.documents.retrieval evaluate \
  --run-id UUID --cases tests/fixtures/retrieval_cases.json --mode keyword

# Explicitly paid query evaluation; never part of normal CI.
uv run --env-file .env python -m studio_copilot.documents.retrieval evaluate \
  --run-id UUID --cases tests/fixtures/retrieval_cases.json \
  --mode hybrid --allow-api
```

The evaluator verifies source hash, revision dates, label text/offsets, and split identities. It reports keyword/vector candidate Recall@20, final passage Recall@6 and MRR@6, all-required-evidence coverage, and expanded-context coverage. A required evidence item must be fully covered by returned source ranges; a one-character overlap is insufficient. Adjoining passages can jointly cover an item. Unanswerable questions are excluded from recall/MRR denominators and their returned-result counts are reported separately; date-exclusion cases must be empty. Degraded hybrid runs are rejected for evaluation rather than mislabelled as hybrid quality.

The initial held-out Recall@6 target is 90%. Report shortfalls honestly, and do not tune on held-out questions. Fake vectors test correctness and orchestration, not semantic relevance. A paid semantic evaluation has not been run in this milestone; vector/hybrid semantic quality remains unmeasured.

## Automated tests and measurements

Normal CI uses real PostgreSQL and fake providers, including actual subprocess CLI/SDK requests against a loopback HTTP service. It covers filtering, exact distances, duplicate mapping, RRF, source provenance, context budgets, read-only transactions, concurrent deletion/replacement, input limits, configuration failures, and safe degradation. The 40-question keyword evaluation is exercised without paid calls.

The benchmark script uses seven exact-10-MB fixtures and a multi-document corpus, isolated test schemas, real stored chunks/vectors and deterministic fake embeddings. It records query-embedding and database-search timings separately, cold/warm query samples, peak memory, and SQL execution plans. Repetitive fixtures exercise large-source preparation and cache reuse, not high-uniqueness vector throughput. Results and limitations are recorded with the completed measurements below.
