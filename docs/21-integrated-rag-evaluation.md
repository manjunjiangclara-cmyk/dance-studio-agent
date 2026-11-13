# Integrated document-answer evaluation

This evaluation exercises the authenticated start-run API, agent routing and interpretation, explicitly activated document revisions, real OpenAI embeddings, PostgreSQL hybrid retrieval, local L6 reranking, document answer generation, email composition, and teacher-review draft persistence. It uses fictional documents in a generated schema of the dedicated `_test` database. It does not approve a draft, book a class, send email, or change the owner library.

The frozen `backend/tests/fixtures/integrated_rag_cases.json` has five smoke and thirty evaluation cases. Source files, labels, dates and expected facts are versioned; the CLI pins the case-manifest SHA-256 and validates source spans against the immutable corpus. Cases include ordinary and cross-document answers, exceptions, conflicts, no-answer and expired-source questions, live-record questions, an injected source, and a mixed information plus booking-change request. Some questions and source families appeared in earlier offline experiments, so this is an integrated-workflow evaluation, not unseen-domain validation.

Run from `backend/` with the configured `.env`, prepared tokenizer and L6 cache, and a PostgreSQL `TEST_DATABASE_URL` ending in `_test`:

```bash
uv run --env-file .env python -m integrated_rag_evaluation --phase smoke \
  --allow-api --max-requests 80 --max-input-tokens 500000 \
  --max-output-tokens 100000
uv run --env-file .env python -m integrated_rag_evaluation --phase evaluation \
  --allow-api --max-requests 250 --max-input-tokens 2000000 \
  --max-output-tokens 500000
```

The paid gate is mandatory. All model and embedding requests share the run cap; a failed or unknown-usage request retains its reservation. SDK retries are disabled for routing and composition in this evaluation, and embedding attempts are counted individually. Reports are saved after every case and on exit. An existing report path is rejected. Source preparation uses the real pipeline, then the owner API explicitly enables each completed revision. Each dated fictional message is started through the authenticated agent API. All schema objects are removed at the end, including after a failure.

The raw report retains per-case draft and document evidence, citations, expected facts, latency, usage, technical error types and a SHA-256 of the exact draft/evidence pair. Apply independent judgments with:

```bash
uv run python -m integrated_rag_evaluation.review RAW.json REVIEW.json \
  --output REVIEWED.json
```

The merger rejects missing cases and mismatched output hashes. Its metrics use explicit denominators, and its decision compares fact support, answer completeness and refusal behavior with the existing [generation targets](17-document-generation.md). Independent AI review is a diagnostic judgment, not human ground truth; a teacher or domain expert should inspect material policy conditions before a deployment decision. Exact citation quotes establish provenance only.

The 2026-11-11 local smoke and evaluation reports are under `backend/evaluations/results/`; those working files are ignored by Git. The fictional 30-case [execution artifact](measurements/integrated-rag-live-2026-11-11.json), [independent case review](measurements/integrated-rag-review-2026-11-11.json), and [decision summary](measurements/integrated-rag-2026-11-11.md) are retained with the repository.
