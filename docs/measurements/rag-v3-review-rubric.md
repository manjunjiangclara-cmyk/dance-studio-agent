# Frozen v3 document draft review rubric

Freeze this rubric before the first paid v3 smoke case. Review each final email against the exact evidence blocks supplied to that run, its question-level answers, the source date and the frozen expected facts. A valid citation identifier or matching quote is insufficient when the cited passage concerns a different subject or action. Record every judgment with the case's `output_sha256`.

For each completed case, record:

- `supported`: every factual statement in the final email is supported by supplied evidence or an explicitly recorded teacher decision. A personal booking, payment, balance, attendance or eligibility statement needs authoritative live data; a policy document alone cannot support it.
- `complete`: the email covers all material frozen expected facts, including conditions, exceptions, dates and conflicting values. A documented unresolved issue may remain open only if the email gives the supported portion and the teacher checklist identifies the decision.
- `citation_relevant`: each document citation used for an answer supports that specific subquestion, subject, action and date. Check the supplied passage, not only the quote string.
- `correct_refusal`: set true for an expected refusal or handoff when the email withholds the unsupported decision and states any supported general facts; set false for an inappropriate assertion. Use null when the expected facts do not call for refusal.
- `false_refusal`: set true when a document-supported answerable fact is withheld or described as unconfirmed; set false when supported facts are given or genuinely absent. Use null when the case does not test this.
- `teacher_ready`: a teacher could approve the email without correcting its facts, scope, condition attachment, unsupported certainty, inappropriate refusal, invented promises, or signature. A required teacher decision may still prevent approval; record that in `issues` and mark teacher ready false until resolved.

Mark `critical` for an unsupported personal state or completed action, a wrong authority choice in a source conflict, a materially wrong amount/date/deadline/condition, or omission of a condition that changes the answer. Identify the failure stage in each issue: retrieval (evidence absent), answer (evidence supplied but claim wrong/missing), or composition (answer correct but email wrong/missing). Separate technical failures and budget exhaustion from semantic judgments.

An independent AI reviewer provides case-level diagnostics; a teacher adjudicates critical or disputed conclusions against the same output hash. This evaluation cannot recommend a pilot while any required adjudication is missing. The thresholds are zero critical issues, support at least 95%, completeness at least 90%, correct refusal at least 95%, false refusal at most 10%, and teacher-ready drafts at least 80%. If any gate fails, the decision is **hold**. The five-case smoke checks only technical readiness; the frozen 30-case set runs once after code freeze.
