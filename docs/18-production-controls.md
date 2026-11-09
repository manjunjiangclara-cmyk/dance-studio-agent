# Production foundations for offline document operations

These controls apply to the existing v1 CLI and document API. They do not publish documents, connect RAG to student answers, add tenants/roles or background workers, or certify generation quality. The Generation prompt and optional-verifier default remain unchanged.

## Trust and authorization

The application remains a single studio. Owner sessions and admin bearer credentials guard every document route; owner writes require the configured browser origin and CSRF token. Revision UUIDs, embedding run IDs, hashes and cached vectors are references, not credentials. CLI operators are trusted holders of database credentials; there is no browser-session ACL inside an offline CLI. Restrict database credentials and local artifact directories accordingly.

Multipart uploads share a **30 requests per rolling 60 seconds** admission limit per application process/studio, covering both creation and replacement. Authorization and CSRF checks happen before admission, and admission before request body reads or temporary-file allocation. Rejected admissions return 429 with `Retry-After`. Requests reaching admission count even if their upload later fails. The limit is process-local, resets on restart, and is not a distributed deployment limit; IP or proxy headers cannot create additional buckets.

## Query cache

One task owns a 128-entry LRU query-vector cache with a 300-second monotonic TTL. Batch operations share it, including copied worker contexts. Independent invocations do not share cached data. Keys comprise opaque task scope, the full embedding profile identity, and SHA-256 of exact query UTF-8 bytes. No normalization or raw-query storage occurs. Successful values are validated unit vectors and callers receive defensive copies. Concurrent identical requests share one computation; failed computations are not cached.

Cache lookup follows explicit API permission, source/run/profile checks and applicable-date checks. Subsequent database reads still validate source eligibility; deleting a source or failing a run cannot be bypassed by a hit. Query vectors do not encode source authorization. Cached queries still require `--allow-api` where that command already requires it. Document vectors continue using the existing PostgreSQL input/profile identity cache. Retrieval results, evidence and final replies are not cached.

## Task budgets

Paid CLI entrypoints accept:

| Option | Default |
| --- | ---: |
| `--max-api-requests` | 1,000 |
| `--max-estimated-input-tokens` | 10,000,000 |
| `--max-output-tokens-total` | 4,000,000 |
| `--events-file` | no additional event file |

Budgets are nonnegative integers; zero permits no corresponding paid work. Existing smaller batch, per-request and worker bounds still apply. Generation preserves `store=False`, a 4,000-token output cap and zero transport retries. Embedding keeps at most three attempts, reserving each separately. Plans disclose minimum requests and retry upper bounds where known. Known minimum budget violations fail before paid execution; retries may exhaust an otherwise valid plan.

Input reservations use a conservative UTF-8-byte upper bound for text, with generation schema and framing allowance. Existing tokenizer-based estimates remain useful diagnostics. This local estimate is not an exact provider token count or invoice guarantee. Generation/verifier output reserves the configured per-request maximum, not just predicted answer length. Paired preflight includes both writer input and the known verifier minimum (instructions, evidence and schema). Plans report `estimated_verification_input_tokens_min` and `estimated_total_input_tokens_min`; the generated candidate adds input reserved at verification time. Impossible known-minimum budgets fail before generation.

Reservations are atomic across task threads and are never refunded after an attempted call, even for timeouts, malformed results or unknown usage. Ownership checks remain before SDK execution. A denied reservation does not invoke the ownership/attempt callback. If that ownership check fails, only its unsent reservation is cancelled; sent attempts can never be refunded. Actual reported usage is separate. CLI stderr retains a content-free final budget ledger for attempted/exhausted tasks, including failures; embedding stdout also records configuration/accounting. Once an attempted reservation exhausts a budget, subsequent attempts stop; bounded in-flight calls finish. Generation and corpus-comparison artifacts retain completed results and technical failures, including completed keyword cases and paid vector cases, with original denominators and an incomplete comparison status. A budget failure is not a business abstention or embedding-outage keyword fallback. This does not implement global daily quotas or coordinate separate processes.

Example (explicit local artifact directories; no command below runs implicitly):

```bash
python -m studio_copilot.documents.generation plan \
  --evidence-dir PATH --tokenizer-cache PATH \
  --max-api-requests 200 --max-estimated-input-tokens 5000000

python -m studio_copilot.documents.retrieval search \
  --run-id UUID --query 'What notice is required?' --as-of 2027-02-01 \
  --allow-api --tokenizer-cache PATH --max-api-requests 3 \
  --events-file operations-results/search-events.jsonl
```

## Operational telemetry and summaries

Explicit stage events cover ingestion, embedding, retrieval, local reranking and generation. An opaque operation UUID correlates one task. Allowed stage names are `operation`, `api`, `budget`, `cache`, and `context`. Events contain only fixed operation/stage/status/error categories, finite nonnegative durations, and nonnegative counts: attempts, retries, tokens/unknown usage, cache hits/misses/waits, candidates, evidence tokens, truncations and items. Unused counters are not fabricated. Budget configuration/actual accounting also accompany execution artifacts.

Neither log/trace events nor aggregate summaries include questions, document text, filenames, student identities, prompts, answers, cache keys/vectors, tool payloads, source IDs or exception text. Existing evidence and evaluation exports intentionally contain source material for controlled local inspection: they are not operational logs. Keep sensitive exports private and avoid shell history for sensitive CLI query arguments.

Ordinary event logging uses the application logger. `--events-file` optionally creates a new JSONL file with mode 0600; it never overwrites an existing file. Create its private parent directory first. Export/open/write failures emit a generic warning and do not alter the document operation. LangSmith remains opt-in through existing `STUDIO_LANGSMITH_TRACING=true`, credentials and optional project. Asynchronous LangSmith SDK logs are sanitized, including exception/stack text and custom logging extras. Automatic SDK content tracing is suppressed; explicit content-free spans correlate through the operation UUID. Do not enable raw SDK debug logging.

```bash
python -m studio_copilot.documents.operations summarize \
  --events-file operations-results/search-events.jsonl \
  --output-dir operations-results/search-summary
```

The summarizer emits `summary.json` and `summary.md` in a new directory. Metrics are grouped by operation/stage: event/failure/degraded counts, nearest-rank p50/p95 and duration sample counts, cache hit rate, retries, truncation and token/request counters. Fewer than 20 duration samples are flagged. Nested stage durations are not additive end-to-end latency. These are operational observations, not a measured SLA or semantic-faithfulness score. Invalid event envelopes fail with a generic error; unrecognized fields never enter summaries.

## Verification and measurements

Normal tests use fake providers. Independent regression tests cover ACL/body-read ordering, retry/concurrent budgets, cache identity/expiry/single-flight, failure privacy, export isolation and real PostgreSQL source revalidation after cache hits. The full backend run passed 1,041 tests (including real PostgreSQL, no skips); all 90 desktop/mobile browser tests and frontend build passed. Ruff, lock consistency, Alembic parity and whitespace checks passed. The [consolidated testing guide](16-testing-and-evaluations.md#production-foundations--2026-11-08) records scope and limitations.

The fixed [synthetic measurement](measurements/operations-2026-11-08.json) uses 100 distinct fictional queries in three passes with an explicitly simulated 1 ms provider delay. It makes 100 fake calls instead of 300 uncached calls; both warm passes make zero calls. Whole-process peak RSS is recorded, including Python/import overhead. This verifies cache mechanics only and predicts neither real provider latency nor answer quality. Reproduce with `python scripts/benchmark_operations.py` from `backend/`.

## Operations checklist and deferred controls

Investigate budget exhaustion, unknown usage, provider failures, repeated degradation and context truncation separately. A legitimate lack of document evidence or teacher handoff is not automatically an incident. Inspect controlled evidence only through its authorized/private workflow. Never add original content to telemetry to debug a production failure.

Process restarts clear query caches and upload admission state. Protect private artifacts with filesystem access and local retention policy. Revalidate current source state on each operation; retained evidence has a distinct audit lifetime. Publication-based invalidation, distributed limits, daily billing ledgers, dashboards, metrics scraping, worker queues/heartbeats, backup automation and multi-tenant ACLs remain future work.
