# Integrated RAG reruns on `origin/master` — 15 November 2026

**Decision: hold the teacher-reviewed pilot.** Both previously inspected 30-case sets were rerun on `ae20e4c48f4138c29c0b513d251c85657d156617`, the freshly fetched `origin/master` commit containing PR #39. The `fresh` corpus is the 2028 fictional document family first measured on 14 November; `v1` is the original reviewed regression set first measured on 11 November. Neither is a new blind validation set. The runs and the separate assistant semantic judgments are diagnostic; no teacher has adjudicated these outputs.

## Execution

Each suite ran through authenticated API start-run requests, explicit activation of fictional revisions in a disposable PostgreSQL `_test` schema, real embeddings, hybrid retrieval, local `cross-encoder/ms-marco-MiniLM-L6-v2` reranking, document answer generation, and email composition with `gpt-6-luna`. Five-case smoke completed successfully before each 30-case run. No booking or other business-table change occurred in any of the 60 cases, no email was sent, and the test database had zero remaining `rag_eval_%` schemas after the runs.

| Suite and phase | Completed | Technical failures | Requests / cap | Input tokens / cap | Output tokens / cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fresh` smoke | 5/5 | 0 | 36/80 | 29,253/500,000 | 3,664/100,000 |
| `fresh` evaluation | 30/30 | 0 | 210/250 | 204,038/2,000,000 | 25,203/500,000 |
| `v1` smoke | 5/5 | 0 | 55/80 | 66,811/500,000 | 4,464/100,000 |
| `v1` evaluation | 30/30 | 0 | 215/250 | 235,904/2,000,000 | 27,541/500,000 |

There were no unknown-usage calls or exhausted budgets. Technical failure stages were retrieval 0, answer 0, composition 0, and agent 0 in both evaluations. `fresh` case latency had a 13.6-second median, 9.7–24.3-second range, and 23.8-second observed 95th value. `v1` had a 12.5-second median, 9.5–33.4-second range, and 31.7-second observed 95th value. The frozen dataset fingerprints were `23a21438429cf096b4c04a71830a4632218f4b734b408adb127832e15939cb0c` (`fresh`) and `2cd7fe5dbe8682a4ec98682b56e289370ffdcb4db1c719b70e988a0af16b0658` (`v1`).

An initial `fresh` smoke attempt failed all five document answers because the selected Python environment lacked `torch` and `transformers`. The attempt is retained as an [environment-failure artifact](integrated-rag-fresh-smoke-env-failure-2026-11-15.json). After loading and verifying the existing local L6 cache in a complete environment, the unchanged smoke set passed 5/5. The failed attempt is excluded from the quality denominators.

## Semantic review

The separate assistant review checked each final email and question-level citation against the evidence actually supplied and the frozen expected facts. It read each current draft; prior reviews supplied the metric rubric, not a verdict for a new output. Judgments are tied to current output SHA-256 hashes and were accepted by the report merger only after all 30 hashes matched. Exact citation validity and application checker warnings were not treated as proof of semantic correctness. A teacher must adjudicate material or disputed judgments before any pilot decision.

| Measure | `fresh` 14 Nov | `fresh` rerun | `v1` 11 Nov | `v1` rerun | Pilot gate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fully supported final email | 25/30 | **28/30 (93.3%)** | 27/30 | **23/30 (76.7%)** | ≥95% |
| Complete response | 25/30 | **27/30 (90.0%)** | 26/30 | **26/30 (86.7%)** | ≥90% |
| Correct refusal | 6/6 | **6/6 (100%)** | 6/6 | **6/6 (100%)** | ≥95% |
| False refusal | 3/26 | **3/26 (11.5%)** | 3/24 | **3/24 (12.5%)** | ≤10% |
| Question-level citation relevance | 30/30 | **30/30 (100%)** | 29/30 | **28/30 (93.3%)** | reported |
| Teacher-ready without correction | 20/30 | **20/30 (66.7%)** | 16/30 | **19/30 (63.3%)** | ≥80% |
| Critical unsupported or omitted conditions | 3 cases | **1 case** | 2 cases | **2 cases** | 0 |

The prior and current runs are single stochastic model samples. Differences are observed case outcomes, not a causal estimate of the code changes. Both datasets were previously reviewed and cannot establish fresh pilot readiness.

### `fresh` findings

- `fresh-16` remains critical: the cited answer gives 15:30 arrival for a 16:00 rehearsal, but the final email says arrival is unconfirmed. This is a composition failure after the fact reached the answer stage.
- `fresh-13` and `fresh-27` still omit supplied, answerable facts alongside appropriate live-state handoffs: office receipt guidance in the first case, and the absence-form/teacher-confirmation rule in the second. These are semantic answer omissions, despite zero technical answer errors.
- `fresh-29` still repeats a student's claim about an archived $19 price source as verified fact; that source was not supplied to the answer.
- `fresh-18`, `fresh-25`, and `fresh-28` now preserve their material conditions or avoid the prior unsupported invitation. `fresh-05` and `fresh-12` answer their generic questions but leave unnecessary required teacher checklist items. `fresh-09` has a contradictory question-level “Yes” while the final email correctly excludes costumes and transport.

### `v1` findings

- `rag-held_out-09` remains critical: the email moves the ten-business-day timing from the full workshop-fee refund to offering both cancellation options.
- `rag-held_out-29` is a new critical wrong-topic contamination in this run: the email gives both guest-workshop deposit amounts but adds costume deposits and applies a costume-charge escalation rule to the guest-workshop authority question. Its second subquestion cites unrelated costume sources. `rag-held_out-30` similarly adds unrelated deposit types to a hand-drum question; both hand-drum amounts and unresolved precedence remain present.
- `rag-held_out-31` has no document-answer evidence or question-level answers. The agent treated a document-conflict question as a live-state/change request and omitted both 10- and 15-minute values from the frozen source documents. This is routing/answer handling before retrieval, not a retrieval miss.
- `rag-held_out-03` still changes or obscures the ten-business-day deadline scope; `rag-held_out-06` states the documented fresh-confirmation rule and then incorrectly says the rule itself remains unconfirmed. `rag-held_out-16` changes the source actor from the repair desk to “I can offer”; `rag-held_out-32` adds an unapproved “I’ll need to verify” promise. The mixed booking-cancellation request correctly avoids changing records but receives only a vague handoff.
- Placeholder signatures in `rag-held_out-04`, `07`, and `17` are gone. `rag-held_out-08` is now teacher-ready; its “at least seven full days” wording preserves the minimum notice requirement despite a checker warning.

## Artifacts and next decision

- `fresh`: [smoke](integrated-rag-fresh-smoke-2026-11-15.json), [raw 30-case output](integrated-rag-fresh-live-2026-11-15.json), [case-level review](integrated-rag-fresh-review-2026-11-15.json), [merged reviewed report](integrated-rag-fresh-reviewed-2026-11-15.json).
- `v1`: [smoke](integrated-rag-v1-smoke-2026-11-15.json), [raw 30-case output](integrated-rag-v1-live-2026-11-15.json), [case-level review](integrated-rag-v1-review-2026-11-15.json), [merged reviewed report](integrated-rag-v1-reviewed-2026-11-15.json).

Both reviewed reports return `hold: critical unsupported or omitted condition`. Neither clears the support, false-refusal, teacher-readiness, and zero-critical gates. Teacher approval remains mandatory for every application draft. Any later pilot decision needs repaired behavior, a new frozen blind validation set, and teacher adjudication.
