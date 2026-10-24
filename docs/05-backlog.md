# Incremental engineering backlog

The original production-booking backlog is superseded by the smaller draft-and-review MVP. These are local specifications, not created GitHub issues.

| Step | Outcome and acceptance | Verification |
| --- | --- | --- |
| 1. Database foundation | Eight tables; student highest level/context; dated enrolment history and current view; class-session regular roster; conversations/messages; migration and local setup. | PostgreSQL migration round trip and metadata comparison, FK/uniqueness/check constraints, term/class changes, roster dates, context persistence, ordered emails. |
| 2. Synthetic fixtures and queries | Load a few fictional students, terms, sites, classes, enrolments, and emails. Query one student's current/history records and available timetable. | Repeatable fixture loading and representative queries; no real student data. |
| 3. Policy resource | Load editable YAML settings and explanations. Include the agreed notice-before-start rule; invent no credit limit. Unspecified rules are visible to staff. | A supported setting changes a check without changing code; invalid/unknown settings are reported. |
| 4. Interpretation and conversation memory | Use a typed model adapter to interpret consecutive emails with stored context. Persist source messages and grounded student context. | Thursday-to-Saturday follow-up, missing facts, context correction, no profile/enrolment writes from model output. |
| 5. Draft and review journey | One LangGraph flow and a small API-driven walkthrough; teacher can inspect, edit, approve, or reject a draft. | End-to-end synthetic scenario; approval causes no booking or outgoing email. |
| 6. Evaluation baseline | A small labeled synthetic dataset with measured interpretation, context, evidence, and draft quality. | Reproducible model/prompt/configuration and real reported results. |

Steps 1–2 are implemented, together with the traditional administration API: student/timetable management, explicit enrolment operations, manual conversation records, and API tests. Schema storage and manual context edits do not implement automatic memory or teacher draft review. The next AI-related steps remain 3–6.

After this MVP, select the next capability together: booking execution, richer enquiries/RAG, dashboard, or deployment. Add transaction, concurrency, recovery, and financial designs when those capabilities require them. Avoid building their infrastructure in advance.
