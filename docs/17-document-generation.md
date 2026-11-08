# Offline generation, citations and optional verification

This CLI answers document questions from saved evidence. It does not connect documents to the application agent, email or teacher review, introduce tables, or authorize business actions. Normal tests use fake providers; hosted inference requires `--allow-api`. Configuration uses `OPENAI_MODEL` and `OPENAI_API_KEY` from the invoking environment. The measured configuration is `gpt-6-luna`; embedding configuration is separate.

## Evidence and calls

`prepare-evidence` validates the existing capture, selected L6 rankings and frozen question/source manifests. It replays the top six candidates with existing parent expansion and a 12,000-token evidence budget. It does not access PostgreSQL, recompute embeddings or run the reranker. Each self-contained artifact includes raw source snapshots, document/revision/date identity, actual supplied blocks, original half-open Unicode character ranges, question/date/variant identity and SHA-256 checksums. These checks detect accidental changes; they are not signatures establishing document authenticity.

Only supplied blocks are sent to the model. Full snapshots, standard facts, evaluation expectations and review labels are excluded. Quotes must match a supplied original fragment exactly, preserving Unicode and line endings. Generated title/path prefixes cannot be cited. Copied table headers and parent text retain their actual source positions. A quote matching multiple positions resolves to the first matching supplied fragment.

The writer returns structured `status`, atomic `claims`, `missing_information` and `reason_code`. Status is `answered`, `partial`, `needs_clarification` or `abstained`. Citation resolution fills real document/revision/hash/ranges in code; invalid citations remove the whole associated claim and downgrade a formerly complete answer. The final answer is rendered from retained claims and fixed status messages. Free-form missing-information metadata is not inserted as unchecked answer prose.

Prompts require evidence-only answers, conditions/exceptions, honest conflicts and appropriate missing-detail/live-data outcomes. Documents and questions remain untrusted data. The writer has no tools and cannot confirm accounts, seats, bookings, payments or completed actions. These prompts reduce risk; a valid quote alone does not prove that its paraphrase follows it.

Default: one writer request followed by local citation checks. `--verify` adds one separate verifier request with evidence and the checked candidate only. It can remove claims, lower completeness or request clarification. Missing/duplicate/unknown claim verdicts and status upgrades fail closed. Failures never silently return an unverified answer marked verified. No applicable evidence takes the zero-request abstention path. There are no hidden retries or rewrites; SDK retries are disabled, storage is disabled with `store=False`, timeout is 30 seconds, and output is capped at 4,000 tokens. Local request estimates use pinned `cl100k_base`, not the hosted model's billing tokenizer.

## Commands

Run from `backend/`, using an explicitly prepared tokenizer cache (see the chunking guide). Existing result directories are rejected. Keep evidence and answer exports private: they intentionally contain document/answer text; routine command output omits it.

```bash
uv run python -m studio_copilot.documents.generation prepare-evidence \
  --capture-dir PATH/TO/SAVED/CAPTURE \
  --rankings-file ../docs/measurements/reranking-live-2026-11-08.json \
  --output-dir evaluations/results/generation-evidence \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

uv run python -m studio_copilot.documents.generation plan \
  --evidence-dir evaluations/results/generation-evidence \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

uv run --env-file .env python -m studio_copilot.documents.generation answer \
  --evidence-file evaluations/results/generation-evidence/gen-tuning-01-actual.json \
  --output-dir evaluations/results/generation-answer --allow-api \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

uv run --env-file .env python -m studio_copilot.documents.generation evaluate \
  --evidence-dir evaluations/results/generation-evidence \
  --output-dir evaluations/results/generation-tuning --split tuning \
  --allow-api --compare-verification --workers 4 \
  --tokenizer-cache /tmp/studio-chunking-tokenizer
```

Add `--verify` to `answer` for semantic checking. For evaluation, freeze prompt/schema/rules before running `--split held_out` into a separate directory. Paired evaluation uses exactly the same writer output for both branches. JSONL, readable Markdown and manifests retain model/prompt versions, source identities, usage, latency and failures. Result-linked independent review is a separate local step, not another API judge counted as faithfulness.

## Frozen evaluation and interpretation

The fixture has 80 questions, 40 tuning and 40 held-out, with disjoint policy families. Each gets two contexts: actual captured retrieval (or an explicitly marked controlled alteration) and standard context supplemented with required original paragraphs. Standard contexts keep retrieved distractors. Missing-evidence, conflicting-authority and injection variants are labelled; they are not new natural retrieval measurements. This reuses existing documents/questions and does not establish generalization to a new domain.

Controlled drops delete the labelled sentence, including its repeated appearances in supplied parent fragments. Other paragraphs can still express the same rule through worked examples. Therefore their expected `partial` status is a diagnostic label, not proof that semantic evidence is absent. Independent review must judge the evidence actually provided and explain these cases. Do not count disagreement with that label as an established hallucination.

At most 160 writer and 160 verifier requests are scheduled across the complete paired experiment, fewer for empty evidence. A separate exploratory smoke request must be disclosed separately. Technical failures remain visible and never count as correct refusal. Request/token/latency counts measure actual incremental verification cost; no dollar estimate is inferred from an assumed price.

Coverage regexes are lexical diagnostics. Final fact support requires independently reviewing final claims against supplied sources and frozen facts, with decisions tied to the output hash. The writer's or verifier's own confidence/pass rate is not faithfulness. Report actual/standard and tuning/held-out separately, including numerator/denominator for small abstention categories. Initial targets are fact support ≥95%, standard-context complete answers ≥90%, correct abstention ≥95%, and false abstention ≤10% for fully answerable cases. A miss stays documented; verification never becomes the default automatically.

## Implementation map

| File | Responsibility |
| --- | --- |
| `contracts.py` | Strict writer/verifier schemas and typed errors |
| `evidence.py` | Artifact checksums, ranges, prompt payload and quote resolution |
| `prepare.py` | Capture/rank replay, controlled variants and standard evidence |
| `provider.py` | Frozen prompts and explicitly paid Responses adapter |
| `engine.py` | Single generation, deterministic checking, optional paired verification |
| `evaluation.py` | Frozen-set preflight, streaming exports, diagnostic metrics and review |
| `__main__.py` | Offline command-line interface and paid gate |

Source-retirement validation during future approval, live business facts, publication/ACL policy and UI integration remain future work. This offline artifact experiment does not establish production safety.

## Measured experiment — 2026-11-08

The writer and verifier both used real `gpt-6-luna`. The [frozen contract](measurements/generation-freeze-2026-11-08.json) records prompts, schema/case/evidence hashes, denominators and targets before held-out execution. The two contexts each contain 40 questions per split. Four empty-evidence instances per split bypass both model calls. Independent Codex agents reviewed all 320 final result rows / 422 claims against supplied source blocks and frozen facts. This is **independent AI review, not human ground truth**; disputed translations, conditional answers and overinclusive gold facts remain annotated.

| Split / context | Path | Supported final claims | Complete answers | Correct abstentions | False abstentions | Required-fact coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Tuning / retrieved or controlled | Default | 45/46 (97.83%) | 23/25 (92%) | 5/6 | 0/25 | 36/42 |
| Same | Verification | 45/46 (97.83%) | 23/25 (92%) | 5/6 | 0/25 | 36/42 |
| Tuning / standard | Default | 51/51 (100%) | 26/29 (89.66%) | 5/6 | 0/29 | 41/42 |
| Same | Verification | 51/51 (100%) | 26/29 (89.66%) | 5/6 | 0/29 | 41/42 |
| Held-out / retrieved or controlled | Default | 59/60 (98.33%) | 22/25 (88%) | 6/6 | 0/25 | 39/48 |
| Same | Verification | 58/59 (98.31%) | 21/25 (84%) | 6/6 | 1/25 (4%) | 38/48 |
| Held-out / standard | Default | 54/55 (98.18%) | 25/29 (86.21%) | 6/6 | 0/29 | 44/48 |
| Same | Verification | 53/54 (98.15%) | 24/29 (82.76%) | 6/6 | 0/29 | 43/48 |

Complete answers require `answered`, independent factual completeness, appropriate status, supported claims and all reviewed required facts. The denominator uses the frozen fully answerable labels. Actual controlled-drop cases with expected `partial` are excluded from that denominator. Some compound gold facts exceed the question's direct request; the conservative coverage/completeness figures retain them, with limitations in review notes. Correct refusal uses six frozen abstention cases per group; clarification is separate. One tuning live-availability question produced safe policy-only partial answers rather than the prescribed abstention, yielding 5/6 (83.33%). This is a status-contract miss, not evidence of a confirmed reservation.

Both paths meet the ≥95% claim-support and ≤10% false-abstention targets. Both **miss the ≥90% standard-context complete-answer target** on tuning and held-out; both miss tuning's ≥95% strict refusal target. Held-out refusal is 6/6 on both paths, a small denominator. The full acceptance gate is therefore **not met**. A claim-support average also does not override a critical-condition failure: the actual-context inhaler answer omits required plan signatures while asserting permission. Do not enable application use based on these averages.

Generated quote validity before filtering was 49/50 retrieved and 54/55 standard on tuning; 66/66 retrieved and 58/60 standard held-out. Every retained citation resolves exactly after filtering. That 100% final citation validity is a deterministic provenance property, not 100% semantic faithfulness. The two paths reuse identical generated quotes; these are not independent trials.

Verification removed **zero unsupported claims**, removed **two supported claims**, corrected **zero status errors**, and caused **two unnecessary downgrades**, including one new false abstention. Both deletions concern the clearly supported 18-calendar-day workshop lead time. It also missed the table-column attribution error on tuning, a missing signature condition on actual held-out evidence, and a recipient-role mistranslation in a Spanish answer. Some outputs unexpectedly changed language; language adherence is a further gap, not covered by the four numerical targets.

| Paid operation | Requests | Input tokens | Output tokens | Sum of request durations |
| --- | ---: | ---: | ---: | ---: |
| Writer, both splits | 152 | 304,219 | 43,543 | 545.45 s |
| Optional verifier, both splits | 152 | 290,706 | 15,016 | 286.02 s |

All 304 evaluation requests completed; unknown-usage calls and technical failures were zero. Four-worker scheduling means summed request durations are not wall-clock duration. Held-out request p95 was 7.56 s for the writer and 3.25 s for the verifier. Verification doubles request count and adds 305,722 reported tokens (87.9% of writer token usage), with no observed semantic correction. A separate disclosed tuning smoke used two requests / 4,124 tokens and showed an unnecessary status-only downgrade; it is excluded from the table and quality metrics. Overall paid execution including smoke: 306 requests / 657,608 reported tokens. No price assumption is used to turn these into dollars.

**Recommendation:** keep verification off. The next iteration should improve condition preservation, conflict/completeness decisions, table interpretation and language adherence on tuning examples, then use a fresh validation set. The inspected held-out set cannot support a fresh unseen-quality claim after tuning to these failures. No automatic prompt rewrite, verifier enablement or application integration was performed.

Audit files (fictional content only): [tuning execution](measurements/generation-tuning-2026-11-08-manifest.json), [tuning review](measurements/generation-tuning-2026-11-08-review.json), [held-out execution](measurements/generation-heldout-2026-11-08-manifest.json), [held-out review](measurements/generation-heldout-2026-11-08-review.json), [tuning final answers](measurements/generation-tuning-2026-11-08-results.jsonl), [held-out final answers](measurements/generation-heldout-2026-11-08-results.jsonl). Matching `*-reports.jsonl` preserve the shared writer candidates and per-request accounting; matching `*-adjudication.json` preserve every independent judgment and its result hash. Execution manifests retain the original unreviewed diagnostics; the separate review files contain the independently reviewed metrics.
