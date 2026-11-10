# Online document answers

The server can now turn interpreted enquiry questions into document-grounded, cited drafts in the existing teacher-review workflow. This is opt-in and single-studio. Uploading or indexing a file alone never enables it. No new public chat endpoint or automatic email delivery is added.

## Request flow

1. The existing authenticated incoming-email or start-run API routes and interprets the message. Makeup booking keeps its deterministic workflow.
2. For an enabled enquiry or teacher handoff, each unresolved question searches the explicitly selected completed embedding runs. Dates use the source message's calendar date in `Australia/Melbourne`, matching existing relative-date interpretation. The query is pseudonymized with the existing student identity filter before embedding/generation; this is not comprehensive PII detection.
3. PostgreSQL lexical search and pgvector cosine search each return up to 20 candidates. RRF merges them; the prepared local `cross-encoder/ms-marco-MiniLM-L6-v2` ranks up to 40. The first six passages receive parent expansion under the existing 12,000-token evidence budget.
4. Original source text, hashes, revisions and character ranges build a checked evidence artifact in memory. Generated heading prefixes cannot serve as citation evidence. No database read transaction spans embedding, reranking or generation; existing workflow orchestration still holds its student advisory-lock connection.
5. Existing **v1** generation runs once per question with applicable evidence; exact-quote citation checks remove invalid claims. There is no verifier, hidden generation retry, automatic rewrite or v2 prompt. Empty evidence makes zero embedding/generation requests when all selected sources are out of date; otherwise a query embedding may be needed to establish no matching evidence.
6. A complete answer with valid citations, no missing information and space in the response/reference limits is composed directly into the draft. A second model does not rewrite these claims. Partial/clarification/abstention results remain visible in supporting evidence but require a structured teacher answer or Confirm later before approval. Exact citation validity does not establish semantic support.
7. Approval rechecks retained document sources against the current server selection, current document revision, complete/ready state, profile/source identity and today's Melbourne effective date. Shared source-row locks last until response commit. A conflict returns 409 and leaves the review and local edits intact. Teacher-supplied answers/deferrals retain their existing question-scoped behavior.

The enabled path is intentionally document-only: it does not use document text to infer account balances, actual seats, enrolment or attendance. These questions require teacher confirmation. The existing database-tool enquiry path is unchanged when the feature is disabled. Free-text change prompts can revise question interpretation; authoritative teacher facts for document answers use the existing per-question answer/deferral controls. Mixed business changes remain teacher handoffs and documents cannot authorize them.

## Explicit activation

In **Studio Knowledge → Documents**, save a document and choose **Enable for answers**. The server prepares its current revision in the background, then enables it only after preparation succeeds. The page shows progress and offers a retry if preparation fails or is interrupted. Preparation may incur embedding API costs; answer generation may also incur API costs. Uploading alone does not enable a document. Choose **Disable for answers** to revoke it.

An administrator must install and prepare the local inference dependencies and assets before teachers can enable documents:

```bash
# backend/
uv sync --locked --group rerank
# Follow the chunking and reranking guides to prepare and verify local assets.
```

Set these in the private server environment and restart the backend:

```dotenv
STUDIO_DOCUMENT_ANSWERS=true
STUDIO_TOKENIZER_CACHE=/absolute/path/to/prepared-tokenizer
STUDIO_RERANKER_CACHE=/absolute/path/to/prepared-reranker-models
```

The server also needs `OPENAI_API_KEY`, `OPENAI_MODEL` and an embedding profile. Request handling never downloads model assets. Run the database migration before using the new controls. The selected runs are stored in PostgreSQL and shared across server processes; `STUDIO_DOCUMENT_RUN_IDS` is no longer used by the online workflow. With no enabled documents, enquiries use the existing non-document workflow. A maximum of 100 compatible documents can be enabled.

Answers remain drafts for teacher review. Effective dates and source identity are checked during retrieval and approval. Disabling a source prevents approval of drafts that still rely on it. If a document changes, its old revision cannot be used; prepare its current revision again. An interrupted preparation can be retried after its lease expires. Explicit CLI preparation remains available for inspection, but does not enable a source.

## Bounds and visibility

Each drafting attempt processes the first eight distinct extracted questions; further questions require teacher confirmation. Applied teacher decisions skip document calls. A shared document-task budget permits at most 32 API attempts, 1,000,000 locally estimated input tokens and 32,000 reserved output tokens. Embedding retains its existing maximum three attempts; generation has one attempt. Failed sent requests retain reservations and unknown usage. Budget or provider failure becomes a technical failure requiring review, never a semantic no-answer result.

These limits cover the **document pipeline only**, not the pre-existing route/interpreter/memory calls. They are not a provider invoice cap or a cross-process quota. Existing 4,000-character per-answer, 20,000-character draft and 40-reference contracts still apply; composition reserves a 16,000-character total answer budget and downgrades overflow questions instead of truncating validated claims.

Local resources are verified and loaded lazily, once per cached path pair; cold initialization and CPU inference are serialized within a process. Missing resources never trigger downloads. The query-vector cache is task-scoped (128 entries, five-minute TTL); it does not cache sources or answers, and source validation still runs on cache hits. No latency or production throughput SLA is claimed.

Existing content-free document events cover retrieval/cache, reranking, generation/API attempts and usage; existing agent spans cover routing and review. See [tracing and observability](19-tracing-and-observability.md). Evidence stores the policy date, model, prompt version, artifact hash, exact provided blocks, source identities, resolved quotes and character ranges. The review UI renders quotes as plain React text, including HTML-looking source content.

## Validation

The online regression suite combines independent unit coverage, real PostgreSQL workflow tests, and desktop/mobile browser checks. It verifies automatic retrieval/citations, unchanged disabled/makeup paths, source revocation/replacement/deletion/expiry, deletion during generation, teacher corrections, shared limits, safe resource initialization, technical failures and escaped source display. All providers are fake. This validates orchestration and safety contracts, **not live semantic quality**; no paid model evaluation was run for this change. See the [unified test summary](16-testing-and-evaluations.md) for the measured results.
