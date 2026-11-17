# Whole-agent everyday run: independent review

Frozen fixture manifest SHA-256: `ab7197b2b3f5dd9e2a5d61265e87b85a6d6a6b801b74c2337a6e25e3779b64d1`. Raw run: `/private/tmp/whole-agent-everyday-2026-11-16.json`, SHA-256 `3b76090242ed7f94a8dfbf1cae7408905c7291b824164097b769c3a12eb7d30a`. Model recorded by the runner: `gpt-6-luna`. The technical run completed 100 of 100 cases, all in `awaiting_review`, with no recorded business changes or email delivery. These technical counts are not quality scores. The frozen formal cases were run once; this review made no provider calls and did not rerun them.

The [case-level review](whole-agent-everyday-independent-review-2026-11-16.json) records each raw `output_sha256`, run ID, observed route, document-answer statuses, six rubric dimensions, judgment, and reasons. I checked 105 claim citations against the frozen document hashes and source text; none had an unknown source or a quote absent from its source. I also reviewed the student drafts and the teacher-only interpretation/review fields against each frozen expected fact and review point.

| Category | Pass | Fail | Unscorable | Total |
| --- | ---: | ---: | ---: | ---: |
| Makeup and absence | 3 | 8 | 19 | 30 |
| General enquiry | 29 | 1 | 0 | 30 |
| Document Q&A | 22 | 3 | 0 | 25 |
| Mixed request and handoff | 15 | 0 | 0 | 15 |
| **All everyday** | **69** | **12** | **19** | **100** |

The pass rate is **69/81 (85.2%) among scorable cases**, or 69/100 if unscorable cases remain in the denominator. No critical failure was observed: all 100 runs retained unchanged business snapshots, produced no delivery, and the reviewed drafts did not claim a completed booking or payment or disclose private data. This is an observed count for this run, not a guarantee for other inputs.

## Validity limit in makeup cases

Nineteen makeup cases are unscorable for their intended business outcome. The raw run's `seed_case` creates a student, enrolment, class sessions, roster memberships, conversation, and incoming message. It did **not** seed `credit_balance`, credit provenance or issue/expiry records, reported absence status, `reported_at`, prior credit use, or actual booking/hold records. `WAV1-M22` also lacks an absence key, missed date, and credit record in the frozen case itself. `WAV1-M14` contains a contradiction: its message claims two unused credits while `business.json` gives that student one. The JSON review names the exact missing state for each of the 19 cases.

A later schedule audit found another raw-run seeding gap: 14 makeup cases with a target class received a session on Tuesday 22 April 2031 at 18:00 instead of the frozen class day and time. Thirteen were already unscorable, so this adds **zero** cases to that count. The remaining case, `WAV1-M20`, tests absence from a class without enrolment; the enrolment mismatch is independent of session time, so its scored failure stands. Capacity on a wrongly timed synthetic session cannot validate the requested makeup place. A failure to verify a makeup in the 19 unscorable cases cannot fairly be attributed to the model. The one-time held-out boundary means a repaired harness should use these cases as regression or diagnostic material, with a newly frozen independent formal set for another unbiased result.

## Observed failures

Eight scorable makeup cases missed the frozen handoff/review expectation; one also failed to use the seeded enrolment mismatch (`WAV1-M20`). The general enquiry failure (`WAV1-G13`) omitted the time required by the frozen expected fact, although the user question asked only for the day; this is an overconstrained expectation rather than a wrong answer to the user's question. Two document cases (`WAV1-D01`, `WAV1-D17`) produced an abstained document-answer operation despite active source text; `WAV1-D17` also omitted the explicit teacher-review rule. `WAV1-D21` answered the food rule but omitted the quiet-area instruction included in its frozen expected fact. These are reported under the literal frozen rubric, without editing the cases after seeing outputs.

For document Q&A, the product routes an information question through `information_only` and invokes the document-answer operation inside that flow. The review treats an answered, cited document operation as the semantic equivalent of the fixture's `document_answer` route. For mixed requests, `other_action` or `unclear` routing with a teacher handoff and a retained grounded partial answer is treated as equivalent to `teacher_handoff`. The raw route remains recorded per case so these mappings can be audited.
