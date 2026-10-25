# Incremental engineering backlog

The original production-booking backlog is superseded by the smaller draft-and-review MVP. These are local specifications, not created GitHub issues.

| Step | Outcome and acceptance | Verification |
| --- | --- | --- |
| 1. Database foundation | Studio tables; student highest level/context; dated enrolment history and current view; class-session regular roster; conversations/messages; migration and local setup. Agent fields and runs are included in the consolidated initial schema. | Fresh PostgreSQL schema initialization and metadata comparison, FK/uniqueness/check constraints, term/class changes, roster dates, context persistence, ordered emails. |
| 2. Synthetic fixtures and queries | Load a few fictional students, terms, sites, classes, enrolments, and emails. Query one student's current/history records and available timetable. | Repeatable fixture loading and representative queries; no real student data. |
| 3. Policy resource | Load editable YAML settings and explanations. Include the agreed notice-before-start rule; invent no credit limit. Unspecified rules are visible to staff. | A supported setting changes a check without changing code; invalid/unknown settings are reported. |
| 4. Interpretation and conversation memory | Use a typed model adapter to interpret consecutive emails with stored context. Persist source messages and grounded student context. | Thursday-to-Saturday follow-up, missing facts, context correction, no profile/enrolment writes from model output. |
| 5. Draft and review journey | One LangGraph flow and a small API-driven walkthrough; teacher can inspect, edit, approve, or reject a draft. | End-to-end synthetic scenario; approval causes no booking or outgoing email. |
| 6. Evaluation baseline | A small labeled synthetic dataset with measured interpretation, context, evidence, and draft quality. | Reproducible model/prompt/configuration and real reported results. |

Steps 1–5 are implemented, including the traditional administration API and the OpenAI/LangGraph makeup enquiry graph. The graph updates memory after interpretation and approval, stores final teacher responses, and supports bounded read-only queries and versioned teacher review. Step 6 has an optional three-case live interpretation smoke evaluation; live results and a broader measured quality dataset remain future work. The default automated suite uses a fake model and does not establish live model quality.

After this MVP, select the next capability together: booking execution, richer enquiries/RAG, dashboard, or deployment. Add transaction, concurrency, recovery, and financial designs when those capabilities require them. Avoid building their infrastructure in advance.
