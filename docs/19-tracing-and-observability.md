# Tracing and observability

This guide describes the instrumentation implemented in this repository: what is recorded, how to collect it, and what the results can tell us. For cache, authorization and budget limits, see [Production controls](18-production-controls.md). For semantic-quality measurements, see [Testing and evaluations](16-testing-and-evaluations.md).

## Logs, traces and metrics

| Signal | Purpose | Current implementation |
| --- | --- | --- |
| Logs/events | Record that an operation, request, cache lookup or failure occurred | Allowlisted document events; generic export warnings; content-free CLI budget accounting |
| Traces | Correlate work and inspect individual execution stages | Optional explicit LangSmith agent spans and document event traces |
| Metrics | Summarize repeated observations | Local JSON/Markdown aggregation of document events |

For example, a slow search can have an embedding request, a cache miss and database work. Correlated operational events help locate the expensive stage. They do not establish whether the returned policy is correct. There is no hosted metrics dashboard, alert scheduler or Prometheus endpoint in this implementation.

## Two instrumentation paths

The business agent and the offline document tools have separate execution paths. Document ingestion or an offline experiment does not enable RAG in student replies.

| Path | Correlation | What appears in LangSmith |
| --- | --- | --- |
| Business agent | Application `run_id` and execution `phase` | An `agent_workflow` root with nested graph-node, model-call and tool-call spans |
| Document tools | Opaque, task-generated `operation_id` | Separate event traces named `documents_<operation>_<stage>`, correlated by metadata |

Agent phases are `start`, `review`, `revision` and `retry`. They are separate executions linked by the same run ID. A teacher-review interrupt can produce `paused`; a successful model request does not mean a draft was approved or a booking completed.

A document task shares its operation ID, query cache and resource ledger across nested calls and copied worker contexts. The operation ID is not a document, student or conversation ID. Independent CLI invocations receive new IDs.

Document event traces are exported when the event is emitted; they are not a reconstructed parent-child timeline of the entire RAG pipeline. Use the event's `seconds` metadata for its measured duration, rather than treating the displayed LangSmith event-span duration as provider latency. Agent spans, by contrast, wrap their actual execution and have start/end timing.

## What document events contain

Required envelope fields:

| Field | Meaning |
| --- | --- |
| `version` | `document-operations-v1` |
| `operation_id` | Opaque UUID for the current task |
| `operation` | `ingestion`, `embedding`, `retrieval`, `reranking` or `generation` |
| `stage` | `operation`, `api`, `budget`, `cache` or `context` |
| `status` | `success`, `failure` or `degraded` |

Optional numeric fields are nonnegative integers; `seconds` must be finite and nonnegative. Unsupported fields are discarded.

| Fields | Interpretation |
| --- | --- |
| `seconds` | Measured duration of the emitting stage |
| `attempts`, `retries` | Request reservations and retries at the instrumented boundary |
| `input_tokens`, `output_tokens` | Provider-reported usage, when known |
| `unknown_usage_calls` | Calls whose usage could not be established |
| `cache_hits`, `cache_misses`, `cache_waits` | Supported cache counters; individual emitters may populate only a subset |
| `candidates`, `evidence_tokens`, `truncations` | Reported retrieval/context observations |
| `items` | Emitter-specific progress observation; embedding progress can be cumulative |

Allowed `error_code` values are `budget_exceeded`, `provider_error`, `invalid_vectors`, `invalid_input`, `source_missing`, `source_incomplete`, `permission_denied`, `rate_limited` and `operation_failed`. Not every failure supplies a recognized error code, and not every supported field is emitted on every path. This is not an audit log of all HTTP permission decisions or every SQL statement.

An illustrative successful API event looks like this; the numbers are examples, not measured results:

```json
{
  "version": "document-operations-v1",
  "operation_id": "92b09366-d1ba-4bef-86f8-57e6f0567749",
  "operation": "embedding",
  "stage": "api",
  "status": "success",
  "seconds": 0.42,
  "input_tokens": 120,
  "output_tokens": 0
}
```

Budget configuration and reservations also appear in CLI/export accounting. Reserved input estimates are not provider-reported tokens. A timeout can consume a reservation while reporting unknown usage. Only an ownership failure before SDK execution can cancel its unsent reservation; sent attempts are never refunded. Details are in the [budget contract](18-production-controls.md#task-budgets).

## Agent trace fields

Agent trace metadata has a separate allowlist: `run_id`, `phase`, `model`, `input_tokens`, `output_tokens`, `tool` and `status`. Status is `success`, `failure` or `paused`. Model and usage fields can be absent when unavailable.

Allowed read-only tool names are `get_timetable`, `get_enrolments`, `search_sessions`, `get_locations` and `check_absence_notice`. Failed spans use the generic error `operation_failed`. See the [agent tracing reference](../backend/src/studio_copilot/agent/README.md#optional-langsmith-tracing) for the workflow hierarchy.

## Privacy boundary

Operational events and explicit trace inputs/outputs exclude questions, policies, document filenames/text, student identities, emails, conversation history, prompts, answers, tool arguments/results, teacher feedback, provider reasoning, vectors, query hashes/cache keys and raw exception messages. Document telemetry also excludes source document/revision IDs. Explicit trace inputs and outputs are empty objects; allowed metadata carries operational information.

Automatic LangGraph/SDK content tracing is suppressed inside instrumented workflows and document tasks. Do not bypass the explicit instrumentation with raw request tracing or SDK debug logging. Document telemetry additionally sanitizes known asynchronous LangSmith SDK loggers: messages, arguments, exception/stack data and custom logging extras are removed while severity is preserved.

Agent run IDs remain linkable application references. Operational UUIDs and usage/timing can still be sensitive metadata. Restrict LangSmith project access and local file access, and choose retention appropriate to the studio.

Controlled evidence files, readable evaluation answers and the retrieval CLI's inspection output deliberately contain source material. They are separate artifacts, not sanitized telemetry. Do not copy them into ordinary logs or a public PR. Exporter failure handling protects business execution; it does not turn these content-bearing artifacts into safe logs.

## Collect local document events without LangSmith

Run from `backend/`. Create a private parent directory first. `backend/operations-results/` is Git-ignored.

```bash
mkdir -p operations-results
chmod 700 operations-results

STUDIO_LANGSMITH_TRACING=false LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false \
  uv run --env-file .env python -m studio_copilot.documents.generation plan \
  --evidence-dir PATH_TO_EXISTING_EVIDENCE \
  --tokenizer-cache PATH_TO_PREPARED_TOKENIZER \
  --events-file operations-results/generation-plan.jsonl
```

This command reads saved artifacts and prepares a plan; it does not make model calls. Its event file can contain an operation duration, but it will not demonstrate real provider usage or latency. Use real execution events only from an explicitly authorized run when measuring those properties.

`--events-file` creates a new UTF-8 JSONL file with mode `0600`; it will not overwrite an existing path or create missing parents. Open/write/export failures warn generically and do not stop document processing, so check that the file actually exists and is populated. Choose a new filename for each invocation.

Events also use the `studio_copilot.documents.operations.telemetry` logger at INFO level. Their visibility in console logs depends on logging configuration; ordinary CLI execution may filter INFO. An explicit event file is the more reliable local collection method. Attempted or exhausted CLI tasks also write a content-free budget ledger to stderr.

## Optional LangSmith export

Tracing is off by default. To enable the existing exporter, configure these in the ignored backend environment file or your process environment:

```dotenv
STUDIO_LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<configured privately>
LANGSMITH_PROJECT=studio-copilot
```

The project defaults to `studio-copilot` if omitted. `LANGSMITH_TRACING=true` alone does not enable the explicit exporter. Both agent and document exporters require the studio opt-in and a nonempty key. A missing agent key can log `trace_configuration_incomplete`; the document exporter simply stays inactive.

Restart the backend to apply environment changes to its process; start a new CLI invocation for CLI changes. Exported shell variables take precedence over the file when using `uv run --env-file`. Do not print credentials while checking configuration.

In LangSmith, filter document traces by `operation_id` and inspect the metadata on `documents_*` events. For business-agent executions, use `run_id` and `phase`, then inspect nested spans. Event JSONL and LangSmith export are independent destinations; either can be enabled without the other.

Enabling telemetry does not itself invoke an embedding or generation model. Running a real model-backed workflow to produce traces can incur provider usage; no such workflow is needed to read or summarize saved events.

## Build and interpret a local summary

```bash
uv run python -m studio_copilot.documents.operations summarize \
  --events-file operations-results/generation-plan.jsonl \
  --output-dir operations-results/generation-plan-summary
```

The output directory must not already exist. It contains:

- `summary.json`: full grouped counts, rates, duration percentiles and sample counts.
- `summary.md`: a compact table of event counts, failures and timing.

Groups are keyed by `<operation>/<stage>`. Percentiles use the nearest-rank method over events containing `seconds`; fewer than 20 duration samples sets `small_sample=true`. Failure rate is failure events divided by all events in that group; `degraded` is counted separately. Cache hit rate is hits divided by hits plus misses, or null with no observations.

These are event-level metrics. Nested operation timings, stage counts and repeated progress snapshots are not additive end-to-end latency, unique task counts or document throughput. Do not sum all groups into one request/token total: budget and API stages describe different aspects of the same work. Use the task ledger for task-wide accounting. The summary has no built-in time windows, historical storage or cross-process daily billing ledger.

A high cache hit rate indicates reuse, not relevance. A low error rate does not prove a grounded answer. Recall, MRR, faithfulness and teacher judgment belong to the [evaluation workflow](16-testing-and-evaluations.md).

## Troubleshooting

| Observation | First checks |
| --- | --- |
| No local event file | Confirm the parent exists, choose a new filename, check filesystem access and generic warnings. |
| Empty or missing console events | Check the INFO logging level; use an explicit event file. A failure before task setup may emit no event. |
| No LangSmith trace | Check studio opt-in, nonempty key, project, process restart and configuration precedence; verify that an instrumented operation ran. |
| `operations_export_failed`, `trace_export_failed` or `trace_sdk_event` | Check destination connectivity, project access and service quota outside business logs; do not enable raw content logging. Export success is not guaranteed by business success. |
| `budget_exceeded` | Inspect configured limits, reservations, retry attempts and unknown usage. Paired preflight includes the known verifier minimum; generated candidate growth can still exhaust execution budgets. |
| Hybrid search is `degraded` | Inspect provider-failure and cache events. Keyword fallback is not equivalent to a healthy hybrid evaluation. Budget failures remain technical failures. |
| High p95 | Check sample size and the emitting stage. Separate API, operation and context observations; do not add nested durations. |
| Unexpected cache misses | Check exact query bytes, embedding profile, TTL, eviction and task scope. Separate CLI processes do not share query vectors. |
| Missing evidence without an error | Investigate source/date eligibility, retrieval coverage and context truncation using controlled inspection artifacts. A lack of evidence is not automatically an outage. |

Do not retry paid work blindly to recreate a missing trace. Start with existing event files and accounting, then use an explicitly approved fictional smoke run only if necessary.

## Implementation and verification references

- Document events/export/privacy: `backend/src/studio_copilot/documents/operations/telemetry.py`.
- Task correlation and automatic-tracing suppression: `backend/src/studio_copilot/documents/operations/runtime.py`.
- Summary aggregation: `backend/src/studio_copilot/documents/operations/report.py`.
- Business-agent tracing: `backend/src/studio_copilot/agent/tracing.py`.
- Tests: `backend/tests/unit/test_production_controls.py`, `backend/tests/unit/test_langsmith_tracing.py`, and `backend/tests/integration/test_production_controls.py`.

Normal tests use fake exporters and model clients. Privacy regressions cover allowlist filtering, sensitive-data sentinels, automatic-capture suppression, exporter failures and asynchronous SDK log sanitization. This guide documents existing behavior; it does not enable tracing, alter runtime configuration or add a monitoring service.

The opt-in [online document adapter](20-online-document-answers.md) also uses these content-free document events during teacher-reviewed enquiry runs. Its document task has a separate opaque operation ID; the outer agent workflow retains its existing run trace. No raw evidence is added to either trace.
