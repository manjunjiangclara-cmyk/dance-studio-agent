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

The evaluator verifies source hash, revision dates, label text/offsets, and split identities. It reports keyword/vector and fused candidate Recall@20, final passage Recall@6 and MRR@6, all-required-evidence coverage, and expanded-context coverage. A required evidence item must be fully covered by returned source ranges; a one-character overlap is insufficient. Adjoining passages can jointly cover an item. Unanswerable questions are excluded from recall/MRR denominators and their returned-result counts are reported separately; date-exclusion cases must be empty. Degraded hybrid runs are rejected for evaluation rather than mislabelled as hybrid quality.

The initial held-out Recall@6 target is 90%. Report shortfalls honestly, and do not tune on held-out questions. Fake vectors test correctness and orchestration, not semantic relevance. A separate live OpenAI evaluation was completed on 2026-11-07; see the measured comparison below. Normal automated tests still use fake providers.

## Automated tests and measurements

Normal CI uses real PostgreSQL and fake providers, including actual subprocess CLI/SDK requests against a loopback HTTP service. It covers filtering, exact distances, duplicate mapping, RRF, source provenance, context budgets, read-only transactions, concurrent deletion/replacement, input limits, configuration failures, and safe degradation. The 40-question keyword evaluation is exercised without paid calls.

The benchmark script uses seven exact-10-MB fixtures and a multi-document corpus, isolated test schemas, real stored chunks/vectors and deterministic fake embeddings. It records query-embedding and database-search timings separately, cold/warm query samples, peak memory, and SQL execution plans. Repetitive fixtures exercise large-source preparation and cache reuse, not high-uniqueness vector throughput. Results and limitations are recorded with the completed measurements below.

### Measured keyword baseline

On 2026-11-06, real PostgreSQL keyword search over the labelled fictional handbook produced:

| Split | Answerable questions | Recall@20 | Recall@6 | MRR@6 |
| --- | ---: | ---: | ---: | ---: |
| Tuning | 18 | 55.56% | 55.56% | 0.5556 |
| Held out | 18 | 27.78% | 27.78% | 0.2500 |

All date-exclusion checks passed. The two in-period questions with no source answer returned no keyword results. These four questions are reported separately from the answerable-question denominators. Parent expansion did not improve coverage for this fixture.

**The keyword-only held-out result misses the initial 90% Recall@6 target.** Long questions can contain terms absent from the relevant policy; AND matching then returns nothing. This is a recorded baseline, not a quality acceptance claim. Held-out labels were not used to tune the query parser. This keyword-only measurement did not establish hybrid quality; the separate 2026-11-07 live comparison below now measures all three paths.

The [full keyword evaluation report](measurements/retrieval-keyword-2026-11-06.json) records every case and marks the unexecuted vector route as unmeasured. Document vectors were deterministic fixtures for this run and were not used by keyword search. No paid API calls were made.

### Measured retrieval performance

Reproduce from `backend/` using a dedicated database ending in `_test`:

```bash
TEST_DATABASE_URL=postgresql+psycopg://.../studio_copilot_test \
  uv run python scripts/benchmark_retrieval.py \
  --output-dir /tmp/retrieval-benchmark --tokenizer-cache /tmp/studio-chunking-tokenizer

TEST_DATABASE_URL=postgresql+psycopg://.../studio_copilot_test \
  uv run python scripts/benchmark_retrieval.py --evaluate-keyword \
  --output-dir /tmp/retrieval-keyword-evaluation --tokenizer-cache /tmp/studio-chunking-tokenizer
```

Measured on 2026-11-06, macOS 26.5.2 arm64, Python 3.12.13, PostgreSQL 18.6 / pgvector 0.8.7. Each corpus totals exactly 10,000,000 bytes. Search runs in a fresh Python process; RSS includes its tokenizer and client state, excludes PostgreSQL server memory, and does not imply cold PostgreSQL buffers. Each mode has nine observations (three query shapes, repeated three times); these local percentiles are not production latency estimates. Preparation time includes actual chunking and persistence with fake embeddings, separate from search. A dash means the distinct-vector count was not recorded in that measurement.

| Corpus | Passages | Distinct vectors | Prepare s | Hybrid median ms | Hybrid p95 ms | Search peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| single-line | 3662 | — | 129.574 | 73.550 | 82.380 | 155.73 |
| short-blocks | 12210 | — | 59.188 | 52.987 | 53.747 | 159.61 |
| many-headings | 4885 | 6 | 28.396 | 24.485 | 25.963 | 155.76 |
| unicode | 9302 | 8 | 19.056 | 51.529 | 53.074 | 159.18 |
| table | 4883 | 5 | 17.500 | 34.495 | 727.033 | 160.50 |
| code | 4914 | 6 | 18.112 | 31.127 | 32.829 | 155.94 |
| giant-row | 2446 | 5 | 10.461 | 54.516 | 177.372 | 152.14 |
| multi-document | 4908 | 4908 | 154.936 | 805.877 | 816.988 | 158.85 |

The seven stress fixtures are deliberately repetitive. The additional four-document corpus uses distinct numbered paragraphs, producing 4,908 distinct vectors. Its hybrid keyword stage median was 722.106 ms and exact-vector stage median was 19.820 ms; broad keyword terms match most paragraphs and dominate ranking work. Search remains exact; these measurements do not establish a need for HNSW or a semantic-recall result.

All eight cases passed result-count, distinct-candidate, context-budget, API-call-boundary, and GIN-index checks. Every case saved actual SQL EXPLAIN plans; the [versioned measurement summary](measurements/retrieval-2026-11-06.json) includes plan structures and separate stage timings. Rerunning the script retains full plans and individual observations in its output directory. All fixture schemas were removed afterward. Fake embedding-call timing in these performance fixtures is not OpenAI latency; the separate live comparison below measures real model relevance and records API usage.

## Paired keyword/vector/hybrid evaluation

Use the dedicated experiment entrypoint to prepare the frozen fictional corpus and
compare all three modes with identical document revision, chunker, model and questions.
The existing single-mode `evaluate` command remains available. Neither workflow
uses a reranker or answer-generation model.

From `backend/`, begin with the local-only plan:

```bash
uv run --env-file .env python -m studio_copilot.documents.retrieval.experiment plan \
  --cases tests/fixtures/retrieval_cases.json \
  --tokenizer-cache /tmp/studio-chunking-tokenizer
```

This command requires no database, API key or network. The frozen v1 fixture has
40 questions (20 tuning / 20 held-out), 38 in-period questions, and 19 distinct
passage inputs. A fresh preparation estimates 1,343 document tokens in at least
one request; paired evaluation estimates 371 question tokens in 38 requests.
These are tokenizer counts, not a price quotation. Existing document vector
cache entries can reduce preparation requests; retries can increase requests.

The following commands are **explicitly paid operations** and are never run by
normal automated tests:

```bash
# Writes only the named fictional evaluation document and its preparation data.
# A repeated call resumes the same immutable revision; it does not overwrite it.
uv run --env-file .env python -m studio_copilot.documents.retrieval.experiment prepare \
  --cases tests/fixtures/retrieval_cases.json --allow-api \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

# Use run_id from prepare's JSON output. Without provenance attestation, scores
# are inspection results and semantic_quality_measured remains false.
uv run --env-file .env python -m studio_copilot.documents.retrieval.experiment compare \
  --run-id UUID --cases tests/fixtures/retrieval_cases.json --allow-api \
  --document-vectors-verified --tokenizer-cache /tmp/studio-chunking-tokenizer \
  > /tmp/retrieval-comparison.json
```

`prepare` validates the frozen fixture and preflights the provider before creating
its deterministic evaluation document. A failed embedding preparation can leave
that fictional document and a failed resumable run; retry the command rather than
editing the revision. Existing mismatched documents are rejected, never replaced.
The experiment intentionally adds no migration, background job or publication.

`--document-vectors-verified` is an explicit operator attestation, not automatic
proof: model and endpoint labels cannot establish whether an existing shared
vector cache contains fake test vectors. Use a database/schema prepared only with
the real provider, or verify its preparation history, before attesting. Injected
fake providers always produce `semantic_quality_measured: false` even with this
flag. A compatible configured provider may be OpenAI or an alternative endpoint;
its endpoint and profile hash are recorded, and it is not silently relabelled OpenAI.

Comparison validates source hash, dates, title, filename and chunker configuration
before provider calls. Question vectors exist only in memory for one invocation:
vector mode obtains each eligible question vector, and hybrid mode reuses that
same vector. Normally this costs 38 question requests total, rather than 76.
Keyword mode and the two date-exclusion questions make no embedding requests.
No persistent query cache, search history or query tracing is added.

The JSON includes fixed dataset/source/config hashes, pinned revision/run,
provider provenance, actual request attempts, reported usage tokens, provider
elapsed time, per-mode database/context timings, and per-question results.
Compare DB-stage timings rather than treating cached hybrid embedding latency
as a speed improvement. Usage is provider-reported, not exactly-once billing.

Each mode reports candidate Recall@20, final Recall@6 and MRR@6, all-required
source-evidence coverage, and expanded-parent coverage. Missing evidence is
classified as absent from the complete candidate union or lost during final
selection, with a flag when parent context recovers it. Provider failures and
hybrid degradation are failed cases, counted as zero for answerable-case metrics;
they do not disappear from denominators. Incomplete comparisons exit nonzero,
retain case failure codes, and cannot claim successful semantic quality or target
achievement. Database errors and later-mode source/preflight failures preserve
completed modes and already-incurred usage in that incomplete JSON, using sanitized
error codes; unknown stage timings remain null rather than fabricated zero values. Date-exclusion checks and in-period unanswerable cases remain separate.

The fixture and splits are frozen; this implementation does not tune retrieval on
the held-out set. The first verified live comparison was run on **2026-11-07** and is recorded below;
its results apply only to this fixed fixture. Offline tests
exercise all paths with fake vectors and real isolated PostgreSQL only.


## Live OpenAI comparison — 2026-11-07

This is a real provider run, separate from automated tests. Both document and question vectors came from OpenAI `text-embedding-3-small` at 1,536 dimensions. Preparation used a fresh isolated schema with no cached vectors; the schema was removed after saving reports. The main document library was not modified. No query parser, fusion parameter, or held-out label was changed for this run.

The corpus is the same fictional handbook (19 distinct passage inputs), with 40 fixed questions split 20/20. Each split contains 18 answerable questions, one in-period question with no source answer, and one out-of-date exclusion. Recall and MRR exclude those latter two cases and are computed over the 18 answerable questions.

| Mode | Tuning Recall@6 | Held-out Recall@6 | Held-out MRR@6 | Held-out all-required evidence coverage |
| --- | ---: | ---: | ---: | ---: |
| Keyword | 55.56% | 27.78% | 0.2500 | 27.78% |
| Vector only | 100% | 100% | 0.9722 | 100% |
| Hybrid / RRF | 100% | 100% | 0.9444 | 100% |

Vector and hybrid found every required evidence span within six passages for all 18 answerable held-out questions, exceeding the initial 90% target on this fixture. Vector-only ranked the first relevant passage slightly better than hybrid. These results do not establish that hybrid is superior, that BM25 is needed, or that retrieval is production-ready: the single handbook is small, and the tuning/held-out questions share policies. Parent expansion did not increase recall in this run.

Both date exclusions returned zero results in all three modes. For each of the two in-period no-answer questions, vector and hybrid returned six candidate passages; keyword returned none. Similarity search does not establish answerability. Evidence-sufficiency checks and abstention remain necessary in a later generation stage.

Actual usage was one document request (1,343 reported input tokens) plus 38 question requests (371 reported tokens): **39 requests / 1,714 input tokens**, with no retries. Hybrid reused all 38 question vectors in memory. The complete comparison took 10.54 seconds after 4.36 seconds of document preparation; the question provider calls totalled 8.23 seconds. Hybrid's cached question-vector timing must not be compared with vector-only's paid embedding latency as an end-to-end speed gain. Usage is provider-reported, not an invoice.

[Full live comparison](measurements/retrieval-live-2026-11-07.json) includes source/config hashes, per-case evidence diagnostics, metrics, and timings. The [execution manifest](measurements/retrieval-live-2026-11-07-manifest.json) records real-provider provenance, request/token totals, completion, and isolation cleanup. Automated tests remain fake-provider tests and make no real OpenAI calls.


## Larger frozen-corpus comparison — 2026-11-07

The second real-provider run keeps retrieval-v1 unchanged: exact cosine search,
20 candidates per route, RRF constant 60, six final passages, and a 12,000-token
context budget. It adds no reranking, BM25, publication, search UI, or agent access.

The frozen `tests/fixtures/retrieval_corpus_v2/corpus.json` describes **16 fictional
sources / 131,248 UTF-8 bytes / 201 unique passage inputs**. Sources cover archived
and current attendance/assessment policies, conflicting active fee/access/costume
instructions, transport, recording consent, and scholarship exceptions. One source
is plain text. There are 100 manually authored questions, split 50/50; each split
has 40 answerable questions, eight in-period unanswered questions, and two dates
outside every document's effective period. Tuning and held-out policy families
are disjoint. Sixteen cases require multiple documents, including ten
condition/exception cases; ten cases deliberately require both conflicting active
sources rather than silently choosing one. The fixture is frozen before model
calls; no retrieval settings or labels were tuned after seeing these results.

This is a hand-authored challenge corpus, with shared administrative language and
repeated scaffolding. It is larger and more varied than the first handbook, but
it is not a representative production sample or a statistical reliability claim.

| Mode | Tuning Recall@6 | Held-out Recall@20 | Held-out Recall@6 | Held-out MRR@6 | Held-out all-required evidence | Held-out expanded coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Keyword | 10.00% | 7.50% | 7.50% | 0.0750 | 7.50% | 7.50% |
| Vector only | 97.92% | 100% | 95.00% | 0.9133 | 92.50% | 97.50% |
| Hybrid / RRF | 97.92% | 100% | 95.00% | 0.9258 | 92.50% | 97.50% |

Recall averages the fraction of required source spans recovered per answerable
question; all-required evidence is the fraction of questions with every labelled
span recovered. MRR counts the rank of the first passage fully covering any
required span. It does not measure whether a multi-source answer is complete.
Candidate Recall@20 for the table means the active route for keyword/vector and
the first 20 fused candidates for hybrid.

Three held-out questions lose evidence from the final six, despite it appearing
in the candidates: one side of a conflicting costume-deposit policy, a scholarship
late-evidence condition, and the scholarship private-submission instruction.
Parent context recovers the last item, raising all-required coverage to 95%.
The first two still lack complete supplied evidence after expansion. Tuning also
contains one candidate-search miss and one final-selection miss. These are
recorded diagnostics, not a parameter-tuning pass. Hybrid improves MRR slightly
on this corpus but does not improve final recall over vector-only.

All four date exclusions passed in all modes. Both vector and hybrid returned
candidates for all 16 in-period questions without source answers (eight per
split); keyword returned none. Future sufficiency/abstention must address this.
No answers were generated in this evaluation.

Scoring is document-aware: an identical integer range in another document cannot
satisfy a label. Candidate scoring uses only date-eligible selected source links.
Final scoring counts the representative and actually returned alternative source
references, not invisible occurrences beyond the engine's reference cap. Expanded
coverage uses only the evidence actually packed into the context budget.

Both document and query embeddings came from real OpenAI
`text-embedding-3-small`, 1,536 dimensions, with no existing/fake vectors in a
fresh test schema. Actual usage: **16 document requests / 26,948 tokens**, plus
**96 question requests / 1,414 tokens**, for **112 requests / 28,362 reported input
tokens**, no retries. Hybrid reused all 96 query vectors in memory. Preparation
took 7.55 seconds; comparison took 25.03 seconds, including 17.54 seconds in query
provider calls. These local timings are not production latency estimates. The
isolated schema was removed after saving results; the main library was unchanged.

Reproduce the exact corpus with a new isolated schema (from `backend/`):

```bash
# Local-only, no database/key/network required.
uv run python -m studio_copilot.documents.retrieval.corpus plan \
  --cases tests/fixtures/retrieval_corpus_v2/corpus.json \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

# Explicitly paid. TEST_DATABASE_URL must name a dedicated database ending _test.
# Creates/migrates/removes only a fresh randomly named schema in that database.
uv run --env-file .env python scripts/evaluate_retrieval_corpus.py --allow-api \
  --output-dir evaluations/results/my-corpus-comparison \
  --tokenizer-cache /tmp/studio-chunking-tokenizer
```

Existing output directories are refused. The runner requires the official OpenAI
endpoint, leaves the frozen questions/settings unchanged, saves plan/preparation/
comparison/summary/cleanup manifest files, and never supplies a fake provider.
For manually managed evaluation environments, the `corpus` module also exposes
`prepare --allow-api` and `compare --run-id UUID ... --allow-api
--document-vectors-verified`; pass all sixteen pinned run IDs explicitly.

[Full larger-corpus report](measurements/retrieval-corpus-live-2026-11-07.json)
and [execution manifest](measurements/retrieval-corpus-live-2026-11-07-manifest.json)
record actual case scores, misses, source identities, usage and cleanup. Independent
automated tests cover document/date attribution, visible references, packed
context, pairing, read-only comparison, immutable preparation and failure accounting
with real PostgreSQL and fake providers only. They make no paid API calls.


## Offline reranking follow-up

The [local reranking experiment](15-document-reranking.md) captures the same full hybrid candidate union and compares real local cross-encoders before final selection. It changes no default search behavior. The [consolidated test/evaluation summary](16-testing-and-evaluations.md) links all implementation tests, performance benchmarks, and real relevance measurements.
