# Integrated RAG evaluation — 11 November 2026

**Decision: hold for routine use.** The opt-in, teacher-reviewed flow completed all 30 fictional cases without a technical failure, but the independent AI review found materially wrong or missing policy conditions and one unsupported live booking-status claim. This is not human ground truth or evidence of production reliability.

The runner used a disposable `_test` PostgreSQL schema, 25 explicitly activated fictional document revisions, real `text-embedding-3-small` vectors, local `cross-encoder/ms-marco-MiniLM-L6-v2`, and real `gpt-6-luna` routing, interpretation, answer generation and email composition. No approval or email send was attempted. The 30-case run made 227 provider requests, with 227,612 reported input and 27,016 output tokens, below the 250-request, 2,000,000-input and 500,000-output caps. All 30 reached `awaiting_review`; no technical error types or unknown usage were recorded. The preceding corrected five-case smoke also completed within its cap. The first smoke and a diagnostic rerun found and fixed an evaluation-only PostgreSQL search-path defect before the frozen 30-case run; their quality results are excluded here.

| Independent AI judgment | Result |
| --- | ---: |
| Fully supported final email | 27/30 (90%) |
| Complete response | 26/30 (86.7%) |
| Correct refusal | 6/6 |
| False refusal | 3/24 (12.5%) |
| Question-level citation relevance | 29/30 (96.7%) |
| Teacher ready without correction | 16/30 (53.3%) |

Support misses the existing 95% target; completeness misses 90%; false refusal exceeds 10%. Small refusal denominators and related fictional source families limit interpretation. The case-level [raw execution report](integrated-rag-live-2026-11-11.json) retains exact drafts, supplied evidence, citations, source identities, usage, latency and output hashes. The [independent review](integrated-rag-review-2026-11-11.json) records all 30 judgments against those hashes and the actual supplied evidence.

## Actionable cases

| Case | Review finding |
| --- | --- |
| `rag-held_out-03` | Refund timing was available in one answer's evidence, but question splitting led a second retrieval to unrelated passages; the email withheld the timing. |
| `rag-held_out-06` | The exact fresh-confirmation rule was retrieved, but the answer was downgraded for an unasked nuance and the email withheld it. |
| `rag-held_out-09` | **Critical:** the email attached a ten-business-day deadline to offering cancellation options; the source attaches it to the refund. |
| `rag-held_out-29` | A second subquestion cited costume deposits instead of guest-workshop deposits; the email avoided the wrong amounts but its question-level evidence was irrelevant. |
| `rag-held_out-31` | Both conflicting 10- and 15-minute intervals were supplied, but the email omitted them. |
| `rag-mixed-business-01` | **Critical:** the email asserted that a live booking remained unchanged without authoritative booking evidence and left the requested cancellation unresolved. |

Several otherwise supported answers had a missing sign-off or `[Teacher]`/`[Your Name]` placeholder. The smoke also produced an unsolicited follow-up promise after a partial answer. These defects raise teacher correction burden even when factual claims are sound. The full review JSON lists all affected cases, including nuanced cases where a checker concern was judged a false positive.

## Limits and next decision

The saved run compared counts of booking-related rows before and after each case, and the application API has no email-delivery action in this path. The harness now compares full roster, enrolment, attendance and teacher-response snapshots for future runs; the saved run cannot retroactively prove that stronger check. The application still requires teacher approval, with unresolved questions needing a teacher answer or deferral.

Fix question splitting/evidence reuse, condition attachment, unsupported live-state wording, and email composition/sign-off on tuning cases. Then freeze a **new** validation set before another paid run; these 30 reviewed cases are now diagnostic, not a fresh holdout. A teacher or domain expert should adjudicate material claims before enabling routine use.
