# Tests and evaluations: consolidated summary

This page indexes implementation checks, performance measurements and real model evaluations. **Passing fake-model tests proves code behavior, not semantic answer quality.** Paid/live evaluations are separate from normal CI. Documents remain unavailable to the agent; reranking and grounded generation are offline experiments.

## Automated checks

| Area | What is checked | Details |
| --- | --- | --- |
| Backend unit tests | Validation, deterministic rules, routing, mocked adapters, token/provenance logic and failure handling | [README test commands](../README.md#verification), [agent guide](08-agent-api.md) |
| PostgreSQL integration | Migrations/model parity, constraints, API access, revisions, concurrent operations, read-only snapshots and owned-schema cleanup | [Schema](02-domain-and-schema.md), [API](07-api.md) |
| Agent/workflow tests | Scripted model responses, teacher review, booking revalidation, recovery, access and tool limits | [Agent guide](08-agent-api.md) |
| Browser tests | Desktop/mobile layout, owner access, document CRUD/large previews, conflicts and preservation of unsaved edits | [Website guide](09-website.md) |
| Ingestion | Exact 10 MB/raw UTF-8 bounds, streaming upload, hashes/dedup, immutable revisions, dates, cleanup, CSRF and safe preview | [Ingestion guide](10-document-ingestion.md) |
| Chunking | Strict token limits, original-source coverage, Unicode/CRLF, tables/code, huge inputs, deterministic export and pinned reads | [Chunking guide](12-document-chunking.md) |
| Embedding | Fake/loopback providers, cache identity, leases, resume/recovery, deletion races and vector linkage | [Embedding guide](13-document-embeddings.md) |
| Retrieval | Exact distances, lexical/RRF behavior, effective dates, duplicate references, evidence budgets, provider failures and source-aware metrics | [Retrieval guide](14-document-retrieval.md) |
| Reranking | Offline windowing/tails, stable scores, cache hashes, source/date/parent attribution, frozen selection, failed-case accounting and paid/download gates | [Reranking guide](15-document-reranking.md) |
| Generation | Sealed evidence identity, exact Unicode quotes, fabricated/prefix/cross-question citations, claim removal/status downgrade, paid gates, single-call default, paired writer reuse and verifier failure handling | [Generation guide](17-document-generation.md) |

Normal pytest does not call OpenAI, download reranker weights, or run real neural inference. PostgreSQL tests require `TEST_DATABASE_URL` ending `_test`; absence explicitly skips them and must not be reported as passing. Browser tests use fixtures/mock API behavior; a healthy local app alone does not establish agent quality or successful Google login.

The reranking milestone passed **903 backend tests**, including **79 new independent reranking tests**. **All 90 desktop/mobile browser tests also passed** against the refreshed app. Static checks include Ruff lint/format, dependency-lock consistency, frontend build, and Alembic schema parity.

```bash
# backend/: real PostgreSQL integration with fake providers; no paid API calls.
STUDIO_TOKENIZER_CACHE=/tmp/studio-chunking-tokenizer \
  uv run --env-file .env pytest -q
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run --env-file .env alembic check

# frontend/: supported Node.js, running app on the intended existing origin.
npm run build
WEBSITE_TEST_URL=http://127.0.0.1:8000 PLAYWRIGHT_CHANNEL=chrome npm test
```

## Performance benchmarks

- **Chunking:** seven exact-10,000,000-byte fixtures cover huge paragraphs, dense blocks/headings, Unicode, tables, code and oversized rows. Real chunking/export is independently verified for coverage and token bounds; elapsed time and process peak RSS are documented in the [chunking guide](12-document-chunking.md).
- **Embedding preparation:** real parsing/persistence with fake vectors measures throughput, cache reuse and replay safety. It is not a semantic embedding evaluation. [Guide and measurements](13-document-embeddings.md), [JSON](measurements/document-embeddings-2026-11-06.json).
- **Retrieval:** seven exact-10-MB stress fixtures plus a four-document, 4,908-distinct-vector corpus measure database stage timing, context budgets, peak RSS and actual SQL plans. Fake vectors make this a performance/correctness benchmark, not a relevance result. [Guide](14-document-retrieval.md#measured-retrieval-performance), [JSON](measurements/retrieval-2026-11-06.json).
- **Local reranking:** real CPU models replay identical captured candidates, recording load/warmup, per-query latency, windows and process memory. No database or OpenAI call is part of that timing. [Guide](15-document-reranking.md).

## Real semantic evaluations

All document/query embeddings below use real OpenAI `text-embedding-3-small` at 1,536 dimensions. Runs use fresh isolated PostgreSQL test schemas and leave the main application library unchanged. Settings and labels are frozen; no reranker is involved in the first two comparisons.

| Run | Corpus / answerable evaluation questions | Mode | Recall@6 | Complete evidence | MRR@6 |
| --- | --- | --- | ---: | ---: | ---: |
| 2026-11-07 | One handbook, 19 passages / 18 held-out | Keyword | 27.78% | 27.78% | 0.2500 |
| 2026-11-07 | Same | Vector | 100% | 100% | 0.9722 |
| 2026-11-07 | Same | Hybrid | 100% | 100% | 0.9444 |
| 2026-11-07 | 16 documents, 201 passages / 40 held-out | Keyword | 7.50% | 7.50% | 0.0750 |
| 2026-11-07 | Same | Vector | 95% | 92.50% | 0.9133 |
| 2026-11-07 | Same | Hybrid | 95% | 92.50% | 0.9258 |
| 2026-11-08 | 24 documents, 279 passages / 40 fresh validation | Hybrid baseline | 93.75% | 90% | 0.9050 |
| 2026-11-08 | Same candidates | Hybrid + local MiniLM-L6-v2 | 97.50% | 95% | 1.0000 |

Recall averages the fraction of required source spans recovered per answerable question. Complete evidence requires every labelled span for that question. MRR measures the first passage fully covering any required span, not completeness of a multi-source answer. Unanswered/date-excluded cases are outside these denominators and reported separately.

The 2026-11-08 selected model improves fresh complete evidence by five percentage points, with warm CPU p95 331 ms. It passes the predeclared experimental adoption gates but remains off in normal search. The already inspected older held-out split is now diagnostic; it was not reused to claim fresh validation.

All date exclusions passed in the retrieval/reranking comparisons. Semantic retrieval/reranking still returns candidates for in-period unanswered questions. Those experiments do not prove answerability, faithfulness, citation correctness of generated answers, or production reliability. Generation is evaluated separately below. Synthetic English policies and correlated question scenarios limit generalization.

Full evidence:

- [Single-handbook report](measurements/retrieval-live-2026-11-07.json) and [execution manifest](measurements/retrieval-live-2026-11-07-manifest.json): 39 requests / 1,714 reported input tokens.
- [Larger retrieval report](measurements/retrieval-corpus-live-2026-11-07.json) and [execution manifest](measurements/retrieval-corpus-live-2026-11-07-manifest.json): 112 requests / 28,362 tokens.
- [Reranking report](measurements/reranking-live-2026-11-08.json), [frozen model selection](measurements/reranking-live-2026-11-08-selection.json), [capture/cleanup manifest](measurements/reranking-live-2026-11-08-capture.json): 168 OpenAI embedding requests / 40,521 tokens; reranking itself runs locally with no API usage.

## Offline document generation — 2026-11-08

Real `gpt-6-luna` evaluated 80 frozen questions (40 tuning / 40 held-out), each with retrieved or explicitly controlled evidence and standard supplemented evidence. Paired paths share one writer candidate. **304 evaluation requests**, 594,925 input tokens and 58,559 output tokens; no technical failures. A separate two-request smoke adds 4,124 tokens. Normal tests still make no paid calls.

Independent AI review checked all 320 final rows / 422 claims against actually supplied sources. It is not human ground truth or verifier agreement. Held-out results:

| Context | Path | Fact support | Complete answer | Correct refusal | False refusal |
| --- | --- | ---: | ---: | ---: | ---: |
| Retrieved / controlled | Default | 59/60 (98.33%) | 22/25 (88%) | 6/6 | 0/25 |
| Same | Verification | 58/59 (98.31%) | 21/25 (84%) | 6/6 | 1/25 |
| Standard | Default | 54/55 (98.18%) | 25/29 (86.21%) | 6/6 | 0/29 |
| Same | Verification | 53/54 (98.15%) | 24/29 (82.76%) | 6/6 | 0/29 |

Both paths miss the ≥90% complete-answer target on standard contexts. Tuning also misses the strict refusal target (5/6, safe policy-only partials rather than abstention). Claim support exceeds 95%, but includes a critical missing-signature condition in one actual-context answer; this is a real gap. Some controlled sentence removals leave equivalent examples, and some gold facts exceed the direct question; independent review notes retain those limitations.

Verification corrected zero reviewed errors, removed two supported claims, and caused one extra false abstention. It adds 152 requests / 305,722 tokens. **Keep verification disabled; the full quality gate is not met.** Final retained citations all resolve, while generated quotes before filtering sometimes do not. Citation validity cannot establish semantic correctness.

The final combined backend run passed **988 tests**, including real PostgreSQL integration and **85 generation-specific fake-model tests**, independently designed/reviewed. Checks cover paid gates, provenance, Unicode, tables/parents, invalid citations, zero-call refusals, exact paired reuse, verifier restrictions, failure exit codes, interruption accounting and safe exports. Ruff lint/format, dependency-lock consistency, migration/model parity (`alembic check`) and patch whitespace checks passed. No API routes, UI, database models or agent behavior change. PR delivery also rebuilt the frontend, passed all 90 desktop/mobile Playwright tests, and restarted the reviewed checkout on the existing portal/backend ports (8010/8000). Portal, frontend-module and built-asset responses, backend health and the same-origin authentication proxy were verified; environment configuration and database data were preserved.

See the [Generation guide and full measurements](17-document-generation.md#measured-experiment--2026-11-08), [frozen experiment contract](measurements/generation-freeze-2026-11-08.json), [held-out independent review](measurements/generation-heldout-2026-11-08-review.json) and [tuning independent review](measurements/generation-tuning-2026-11-08-review.json).

## Production foundations — 2026-11-08

The offline v1 path adds atomic task budgets, a 128-entry/300-second exact-query vector cache, sanitized events/tracing and offline summaries. Owner/admin/CSRF authorization is retained; authenticated multipart creation/replacement is admitted at most 30 times per rolling minute per application process, before body reads. No new database tables, online RAG, generation prompt changes or paid model evaluations are included.

Independent coverage adds **54 unit tests and six real PostgreSQL tests**: cache TTL/LRU, Unicode/profile/scope identity, concurrent single-flight success/failure and defensive vectors; atomic concurrent reservations, per-retry/unknown usage and zero-call gates; shared worker budgets and retained batch outcomes after exhaustion; source deletion/incomplete-state/API-gate checks despite a cache hit; matching provider/preflight reservations; document ACLs, CSRF and admission-before-body; telemetry allowlists, export failure isolation, gold-label exclusion and asynchronous SDK log sanitization (including custom logging extras).

A first compatibility run found older paired-comparison cache-hit counters were bypassed. The paired helper now uses the same bounded exact-input cache while retaining its accounting contract. Budget preflight estimates were aligned with request reservations. Initial tests inherited enabled LangSmith configuration and exported content-free operational traces; final verification explicitly disables external tracing. No embedding or generation model API was invoked.

The [synthetic cache workload](measurements/operations-2026-11-08.json) executes 100 distinct fictional queries three times with a declared 1 ms fake-provider delay: 100 cold calls, zero calls in either warm pass, **200 avoided fake calls out of 300**. Cold elapsed time was 136.31 ms; warm passes were 0.94/1.36 ms. Whole-process peak RSS was 68,075,520 bytes (~64.9 MiB), including interpreter/import overhead. This tests mechanism performance, not real OpenAI latency, retrieval quality or faithfulness.

Frontend build and **90 desktop/mobile Playwright tests passed** against the refreshed checkout on ports 8010/8000. Health, portal, rebuilt assets, same-origin auth proxy and anonymous upload rejection were verified without changing existing environment configuration, migrations or application data. The complete backend suite passed **1,048 tests**, including real PostgreSQL integration, with no skips. Ruff lint/format (240 files), dependency-lock consistency, Alembic model parity and patch whitespace checks passed. Independent PR review found an event-file initialization/log-handler failure edge; its guarded fix and regression passed review. CLI integration tests separately verify stable persisted run fields and per-invocation accounting (one paid attempt on initial preparation, zero on status/resume), retaining the one-request fake HTTP assertion. Live admission verification returned 422 for 30 authenticated invalid-UUID uploads and 429 with Retry-After on the next, without reaching ingestion or modifying documents. Frozen v1 prompt strings were compared directly with `master` and remain identical.

PR review follow-up adds regressions for three boundary cases: paired preflight now includes the known verifier-input minimum; corpus budget exhaustion returns retained keyword/vector results plus explicit technical failures; and denied embedding reservations cannot inflate persisted or paired request/attempt counters. An ownership failure cancels only an unsent reservation; SDK attempts retain their reservations. New coverage validates a writer-only budget fails before any call, actual verifier-candidate growth still retains partial artifacts, corpus CLI emits all 300 case outcomes on a two-request limit, and PostgreSQL run attempts match those two SDK calls. These checks use fake providers and no external tracing. Final follow-up validation passed all 1,048 backend tests (including PostgreSQL, no skips), Ruff lint/format and an additional fresh-context review with 130 focused unit tests.

See [Production controls and operating limits](18-production-controls.md). Cache state, admission and task budgets are process-local; there is no distributed daily quota, publication lifecycle or monitoring service.

## Other paid agent evaluations

Email-drafting and business-workflow evaluations live in `backend/evaluations/` and `backend/workflow_evaluations/`, separately from pytest. The [agent guide](08-agent-api.md) documents opt-in execution and graders. Their model understanding, booking behavior and teacher-review results must be assessed separately from document retrieval. They were not rerun merely to add offline reranking, and this page makes no new claim about their current live quality.
