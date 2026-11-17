# Integrated document-answer evaluation

This evaluation exercises the authenticated start-run API, agent routing and interpretation, explicitly activated document revisions, real OpenAI embeddings, PostgreSQL hybrid retrieval, local L6 reranking, document answer generation, email composition, and teacher-review draft persistence. It uses fictional documents in a generated schema of the dedicated `_test` database. It does not approve a draft, book a class, send email, or change the owner library.

The original `backend/tests/fixtures/integrated_rag_cases.json` is a reviewed regression set. The fresh `backend/tests/fixtures/integrated_rag_validation_v2/` family has a separate 2028 fictional studio corpus, five smoke cases, and thirty validation cases. Its source dates, bytes, question text, expected statuses, and exact fact spans are pinned and checked before paid calls. The fresh set includes single and cross-document facts, exceptions, conflicts, missing details, live-record requests, mixed business actions, an archived source, and a prompt injection.

Run from `backend/` with the configured `.env`, prepared tokenizer and L6 cache, and a PostgreSQL `TEST_DATABASE_URL` ending in `_test`:

```bash
uv run --env-file .env python -m integrated_rag_evaluation --suite fresh --phase smoke \
  --allow-api --max-requests 80 --max-input-tokens 500000 \
  --max-output-tokens 100000
uv run --env-file .env python -m integrated_rag_evaluation --suite fresh --phase evaluation \
  --allow-api --max-requests 250 --max-input-tokens 2000000 \
  --max-output-tokens 500000
```

The paid gate is mandatory. All model and embedding requests share the run cap; a failed or unknown-usage request retains its reservation. SDK retries are disabled for routing and composition in this evaluation, and embedding attempts are counted individually. Reports are saved after every case and on exit. An existing report path is rejected. Source preparation uses the real pipeline, then the owner API explicitly enables each completed revision. Each dated fictional message is started through the authenticated agent API. All schema objects are removed at the end, including after a failure.

Run the complete five-case fresh smoke and inspect its technical summary before starting the unchanged 30-case set. Use `--suite regression` only for development diagnosis; its previously reviewed results do not count as fresh validation.

The raw report retains per-case draft and document evidence, citations, expected facts, latency, usage, technical error types and a SHA-256 of the exact draft/evidence pair. Apply independent judgments with:

```bash
uv run python -m integrated_rag_evaluation.review RAW.json REVIEW.json \
  --output REVIEWED.json
```

The merger rejects missing cases and mismatched output hashes. Its metrics use explicit denominators. A pilot candidate requires zero critical unsupported or omitted conditions, support at least 95%, completeness at least 90%, correct refusal at least 95%, false refusal at most 10%, teacher-ready drafts at least 80%, and teacher adjudication of every case. Independent AI review is diagnostic; its verdict and exact citation validity do not establish semantic correctness. Until teacher adjudication is recorded against each output hash, the decision remains hold.

The 2026-11-11 local smoke and evaluation reports are under `backend/evaluations/results/`; those working files are ignored by Git. The fictional 30-case [execution artifact](measurements/integrated-rag-live-2026-11-11.json), [independent case review](measurements/integrated-rag-review-2026-11-11.json), and [decision summary](measurements/integrated-rag-2026-11-11.md) are retained with the repository.

The latest [15 November `origin/master` rerun report](measurements/integrated-rag-master-rerun-2026-11-15.md) links the five-case smoke and 30-case raw, case-review, and merged artifacts for **both** the `fresh` and original `regression` suites. Both were previously reviewed datasets, so those reruns measure regressions rather than new blind validation. Their historical 11 and 14 November reports remain unchanged apart from links to the later run.

For the subsequent repair, both reviewed 30-case sets are development regressions. An independent evaluator froze `backend/tests/fixtures/integrated_rag_validation_v3/` before implementation changed. Its case file SHA-256 is `98c61d83facedd362b7c013da75ebfab2ba9e9279966ace2a7c08d2bf1f6d096`, source-manifest SHA-256 is `6e4079f04d4db8f208c24e2e145cb295484ea55da2cf1d7e76150ae432b702f1`, and combined dataset fingerprint is `ae7d736dc1007390f7db98c808a16af3d7bf0727d99c640331e15fdabc6b2fe0`. After code and the [v3 review rubric](measurements/rag-v3-review-rubric.md) are frozen, run `--suite blind --phase smoke` under the same caps, then `--suite blind --phase evaluation` once. Do not tune against the blind answers. Its final report must link each independent judgment and teacher adjudication to the exact output hash; an incomplete teacher review keeps the pilot on hold.

The [16 November blind v3 decision report](measurements/rag-v3-decision-2026-11-16.md) links the one five-case smoke, one 30-case formal run, independent hash-checked case review, and pending teacher adjudication queue. The pilot decision is **hold**. The v3 cases are now regression data; a later pilot decision needs a newly frozen unseen set.
