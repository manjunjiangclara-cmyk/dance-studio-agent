# Fresh integrated RAG validation — 14 November 2026

**Later rerun:** The same 30 cases and the original v1 regression cases were rerun on `origin/master` on 15 November. See the [dated rerun report](integrated-rag-master-rerun-2026-11-15.md). The results below remain the historical 14 November measurement.

**Decision: hold the teacher-reviewed pilot.** The fresh, fictional 30-case run completed without a technical failure, but independent AI review found three critical omitted or changed conditions. Support, completeness, false refusal, and teacher readiness missed the agreed gates. No teacher has adjudicated the material or disputed judgments, so this is diagnostic evidence rather than a pilot authorization.

## Frozen scope and execution

The new Harbour Lantern Dance Studio document family and five smoke plus 30 validation questions were frozen before paid execution. The case manifest SHA-256 is `83b53d65325d62d69728b54257bea1664ec1530a3942ae5b99a715533665681f`; the source manifest SHA-256 is `e20b48877bb530cbdff0ee343e24f8d76995af4c88ac50465d688092a43534d0`; the combined dataset fingerprint is `23a21438429cf096b4c04a71830a4632218f4b734b408adb127832e15939cb0c`. These documents and questions are separate from the previously reviewed 30 regression cases.

The final five-case smoke completed 5/5 within an 80-request, 500,000-input-token, 100,000-output-token cap. An earlier smoke attempt failed because the worktree Python environment lacked local reranking dependencies; the unchanged smoke was rerun with an existing complete reranking environment and a separately verified L6 cache. A final smoke followed the deterministic handoff wording change. Its quality results were not included in the 30-case denominators.

The single fresh validation run used the authenticated API, explicitly activated revisions in a disposable `_test` schema, real embeddings, PostgreSQL hybrid retrieval, local L6 reranking, real answer generation, and email composition. All 30 runs reached `awaiting_review`; 30/30 preserved business tables and 30/30 had no email delivery. The schema was removed after execution. The run used **216/300 requests**, **210,155/2,000,000 input tokens**, and **25,874/500,000 output tokens**, with no unknown usage. Median latency was **13.7 seconds per case**, observed range **8.5–34.3 seconds** (95th observed value **29.7 seconds**). Technical failure counts were **retrieval 0, answer 0, composition 0, agent 0**.

## Independent case review

The [case-level review](integrated-rag-fresh-review-2026-11-14.json) is tied to each output SHA-256. The [reviewed report](integrated-rag-fresh-reviewed-2026-11-14.json) contains the exact draft, question-level answers, supplied passages, citations, concerns, status, latency, and usage. The reviewer checked the final email against the evidence actually supplied and the frozen expected facts; exact citation validity and the application's own checker verdict were not treated as proof of semantic support.

| Measure | Result | Pilot gate |
| --- | ---: | ---: |
| Fully supported final draft | 25/30 (83.3%) | ≥95% |
| Complete response | 25/30 (83.3%) | ≥90% |
| Correct refusal | 6/6 (100%) | ≥95% |
| False refusal | 3/26 (11.5%) | ≤10% |
| Question-level citation relevance | 30/30 (100%) | Reported |
| Teacher-ready without correction | 20/30 (66.7%) | ≥80% |
| Critical unsupported or omitted conditions | 3 cases | 0 |

**Critical cases requiring teacher adjudication:**

- `fresh-16`: The cited answer established arrival at 15:30 for a 16:00 rehearsal, but the composed email said the arrival time was unconfirmed. The fact reached the answer stage and was lost in composition.
- `fresh-18`: The source gave a 20 July photography-consent deadline; the email made filing conditional on choosing to provide consent. Whether this changes the policy obligation needs a teacher's ruling.
- `fresh-28`: Both conflicting absence-notice values reached the email, but the 24-hour rule lost its “before class” condition. The question about which source controls correctly stayed unresolved.

Other correction cases are `fresh-01` (unresolved joinability), `fresh-13` (payment verification promise and omitted receipt guidance), `fresh-19` (unresolved return time), `fresh-25` (unsupported office-arrangement invitation), `fresh-27` (supplied booking-process facts omitted at the answer stage), `fresh-29` (student-reported archived price repeated as a sourced fact), and `fresh-30` (live refund state correctly withheld, with an unresolved teacher task). The case-level JSON records the exact judgment and issue for each.

The retrieved passages contained the frozen expected facts in the material misses; no reviewed citation was judged off-topic. The measurable quality failures here were **answer-stage omissions** (`fresh-13`, `fresh-27`) and **composition-stage omissions, changed conditions, or unsupported claims** (`fresh-13`, `fresh-16`, `fresh-18`, `fresh-25`, `fresh-28`, `fresh-29`). Technical stage counts of zero therefore do not imply semantic success. The small refusal denominators, fictional sources, and independent AI review limit generalization. Teacher adjudication remains pending, and teacher approval of every application draft remains mandatory.

After this measured run, regressions revealed that a pure live booking/payment question was not always routed through the deterministic handoff unless the interpreter also extracted a requested action; an unapproved follow-up promise could remain in the draft; a teacher resolution could be paired with stale document facts in the writer context; and conflicting claims could be passed with their question's combined citations. The handoff now checks personal live-status questions in code even if the generator labels them answered, unapproved promise sentences are removed, teacher resolutions no longer carry stale document facts, each claim retains its own citations, and an unsigned generic sign-off is stripped. Focused fake-provider and PostgreSQL regressions pass, but these post-run safeguards were **not measured by the fresh 30-case run**. The pilot remains on hold, and any later pilot decision needs new frozen validation of the final code plus teacher adjudication.

## Existing agent evaluation suite

The separate 35-scenario synthetic agent suite was also run with real `gpt-6-luna` calls in disposable `_test` schemas and its explicit `--live` flag. It passed **26/35** automated checks; human draft review remains pending. The nine failed scenarios were `missing_dates`, `first_contact`, `late_absence_notice`, `typos_and_informal`, `quoted_email_correction`, `nonexistent_named_makeup_class`, `unrelated_student_email`, `enquiry_three_information_states`, and `enquiry_unknown_class`. The [full agent evaluation report](agent-evaluations-2026-11-14.json) retains each expected/actual comparison. These failures are in the general or makeup agent paths, not the enabled document-answer path; they are reported separately and were not counted in the fresh RAG denominators.
