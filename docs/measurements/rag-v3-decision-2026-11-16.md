# Blind integrated RAG validation — 16 November 2026

## Decision

**Hold the teacher-reviewed pilot.** The independent review found two critical semantic errors, fact support below 95%, and teacher-ready drafts below 80%. No automatic reply or business action was enabled. A teacher has not adjudicated the material and disputed outputs.

The [frozen review rubric](rag-v3-review-rubric.md) and repaired code were committed at `c87694e` before the blind run. The independent evaluator had frozen the fictional v3 corpus and cases earlier at `665d06b`. The combined dataset fingerprint was `ae7d736dc1007390f7db98c808a16af3d7bf0727d99c640331e15fdabc6b2fe0`; the case manifest SHA-256 was `98c61d83facedd362b7c013da75ebfab2ba9e9279966ace2a7c08d2bf1f6d096`. The model and retrieval path used `gpt-6-luna`, `grounded-generation-v1.2`, `text-embedding-3-small` at 1536 dimensions, and local `cross-encoder/ms-marco-MiniLM-L6-v2`. No production behavior was changed after the formal cases were inspected.

## Results

| Measure | Blind 30-case result | Pilot gate |
| --- | ---: | ---: |
| Technical completion | 30/30 | Complete run |
| Fact support | 28/30 (93.3%) | ≥95% — **miss** |
| Completeness | 27/30 (90.0%) | ≥90% — met |
| Correct refusal or handoff | 5/5 (100%) | ≥95% — met |
| False refusal | 1/30 (3.3%) | ≤10% — met |
| Citation relevance | 29/30 (96.7%) | Diagnostic |
| Teacher-ready email | 23/30 (76.7%) | ≥80% — **miss** |
| Critical unsupported or omitted condition | 2 cases | Zero — **miss** |

The independent AI review covered all 30 exact output hashes and was merged with the [raw formal run](rag-v3-evaluation-2026-11-16.json) into the [case-level reviewed report](rag-v3-reviewed-2026-11-16.json). The [separate review judgments](rag-v3-independent-review-2026-11-16.json) document each issue. A citation string or exact quote was never treated as proof that a passage supported the subquestion. The teacher adjudication flags remain false; this is an AI diagnostic and a **hold** decision, not a teacher-approved quality claim.

The formal run had 0/30 technical failures: retrieval 0, answer 0, composition 0, and agent 0. All frozen required fact spans appeared in the evidence actually supplied to the answer step (0/30 retrieval misses for those spans). Semantic review found answer-stage issues in 4 cases and composition-stage issues in 5 cases; two cases have issues in both stages. These semantic counts are separate from technical failure counts. The [five-case smoke run](rag-v3-smoke-2026-11-16.json) completed 5/5 with 0 technical failures before the formal run.

Both runs used disposable schemas in the dedicated `_test` database. The recorded invariants were 5/5 and 30/30 with no booking or other business change and no email delivery. Smoke used 36/80 requests, 32,190 input tokens and 3,219 output tokens. Formal used 206/250 requests, 219,508 input tokens and 23,530 output tokens; neither token cap (2,000,000 input, 500,000 output) was reached. Formal per-case latency was 12.27 seconds median, 20.99 seconds at nearest-rank p95, and 22.67 seconds maximum. The raw smoke SHA-256 is `0ec72b7cb3d652c621a32644781d702205fcccd88244faf7f237188a520bd8bf`; the raw formal SHA-256 is `99ac9560ad54af7040977799be05399b5cf5989f82117a41a54cb1599bc393ef`.

## Cases requiring attention

- **v3-09, critical answer omission:** the source limits the 12% tuition reduction to the *second sibling*; the email states a general sibling reduction. This changes who qualifies. Output hash `7271ea45b39cf21ee2fb231f12041bd54dd93b0606e253d9de004f584c768085`.
- **v3-11, critical answer/composition error:** a returned kit arrived six days after the show, while the documented bond condition says *only* within five calendar days, clean and undamaged. The answer unnecessarily required teacher confirmation; the email then suggested a late return might still qualify. Output hash `de390340da6e3328f127cde227d14023e0346d2c66a12a3ed070d24041aed6b8`.
- **v3-30, material wrong-topic citation and incomplete email:** the personal refund-approval subquestion cited general Term Three refund rules. The email did not clearly say approval cannot be verified or dismiss the visitor-submitted approval sentence as non-policy. The current $31 trial price was correct. Output hash `189cf4dfa25ac2513a8398a6696ef054108ee6d52bd429d9db05e9f6a290274c`.
- **v3-29, unresolved authority:** the email correctly gives both 17-hour and 27-hour ordinary-absence notice values and chooses neither. A teacher must decide which governs before making a definitive policy statement. Output hash `84c6a5b01ea5f74c5715d3835c7d36ad3e7a5739fa6a6c34f3eca2bfbc3c7e07`.
- **v3-13, v3-20, v3-28:** supported dates or process facts were included, but the individual payment, return time, or booking state remains unresolved. Their draft checklist requires teacher or authoritative-record handling before approval.

The [teacher adjudication sheet](rag-v3-teacher-adjudication-2026-11-16.md) keeps these findings tied to the exact output hashes. The two critical cases and the source-authority dispute require explicit teacher decisions; v3-30 needs a material answer review. No teacher decision has been inferred from an AI verdict.

## Regression boundary and next work

The previously reviewed [v1 30-case diagnostic](rag-v1-regression-diagnostic-2026-11-16.json) and [fresh/v2 30-case diagnostic](rag-v2-regression-diagnostic-2026-11-16.json) each completed 30/30 without technical failures; their scores are **not** pilot evidence. In those development runs, v1-29/30/31 retained both sides of document conflicts without choosing authority, fresh-16 retained the 15:30 arrival, fresh-27 kept the absence-form process while withholding live booking state, and fresh-29 used the current $24 trial price. Targeted [v1-09](rag-v1-09-targeted-2026-11-16.json) and [fresh-13](rag-v2-13-targeted-2026-11-16.json) diagnostics checked the ambiguous deadline handoff and receipt-process extraction before the final code freeze. These diagnostic outputs precede the final receipt deduplication test and are not part of the blind result.

For the next code iteration, keep the full subject and eligibility scope in each atomic claim (v3-09), treat an explicit “only when” condition as a decisive negative for a case outside it (v3-11), and reject a general refund-policy citation as evidence of a person's approval state (v3-30). Make the unresolved live state explicit in the email and reduce unnecessary checker concerns for supported partial facts. Use this v3 set only as regression data; an independently frozen new corpus and cases are required for the next pilot decision.
