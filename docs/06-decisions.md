# Accepted direction and open decisions

## Agreed direction

- The initial increment was draft-and-review only. The teacher-approved booking increment below supersedes its booking restriction; sending email remains separate.
- Make studio policies editable input resources. Keep notice-before-start; remove the invented two-credit limit. Defer detailed policy definition.
- Give the agent student conversation memory across follow-up emails.
- Keep the initial data model small; do not generate regular-session booking records or duplicate student arrays.
- Implement studio data and conversation storage in the first database migration.
- Include highest level and a current-enrolment view on the student; preserve enrolment history as its own entity.

## Database implementation choices

- Initial foundation - eight tables: students, terms, locations, classes, class sessions, enrolments, conversations, and messages.
- `highest_level` is an optional staff-maintained label, separate from conversational context.
- `Enrolment` is the history entity. `Student.current_enrolments` is a read-only field derived from its dated records; it supports multiple regular classes.
- Changing classes should end an old attendance period and add a new one. Cancelled registrations are distinguished from periods that actually occurred. This is history of attendance periods, not a separate event-sourcing system.
- `ClassSession.students` derives the regular roster on the session date. Makeup participation and capacity decisions are not implemented yet.
- Use PostgreSQL, SQLAlchemy, Alembic, and native Python 3.12 with uv. No database connection occurs on module import.

## Open for later discussion

Additional policy rule types; class suitability rules; makeup booking writes; production reliability; and hosting. The agent increment selects the OpenAI Responses API, configurable model, one LangGraph workflow, PostgreSQL checkpoints, YAML policy input, source-linked memory, and API-driven teacher review.

## Website increment

Public visitors browse versioned fictional examples without signing in. The React website is served by FastAPI and never queries workspace records in public mode. The owner workspace uses a verified Google account matching the configured owner email, with session authentication and CSRF protection. It permits record inspection, incoming-email simulation, and agent review actions; direct studio administration writes remain outside the browser workspace. Approval can book the proposed session and save reviewed text without sending email or changing regular enrolments. Hosting selection and provisioning remain deferred. See [website setup](09-website.md).

## Traditional backend increment

The owner selected core administration before AI: students, terms/locations/classes/sessions, explicit enrolment changes/history, and manual conversations. These staff commands can write official records; the later increment permits dated-session booking only after teacher approval. The API uses one local admin token, retains historical records, and provides no hard-delete endpoints. All existing database tables remain unchanged.

These are deferred decisions, not assumed requirements of the database foundation. The previous credit ledger, conditional-offer protocol, and production job infrastructure are not part of this implementation.

## Agent increment

Student memory updates immediately after interpretation, before queries, then reconciles again after teacher approval. Final edited teacher responses are stored separately from generated drafts; approval does not establish delivery. Read-only tools have fixed call/round limits and terminate on missing data. Rejection closes the run without a rejection message or audit event and deletes its graph checkpoints. See [workflow](03-makeup-workflow.md) and [agent API](08-agent-api.md).

Intent routing precedes flow-specific extraction. Makeup retains its own `MakeupInterpretation`; future enquiry types receive separate interpreters when implemented. Unclear, unsupported, or independently mixed requests use teacher handoff rather than being forced into the makeup schema.

## Teacher-approved booking increment

The owner explicitly selected actual booking execution after teacher approval. Draft generation alone never reserves a place. The student UUID is added directly to the session’s independent `students` list; no separate booking entity is stored. The approved run retains its proposal and response. Approval uses fresh capacity and proposal checks and commits the reservation with the teacher response. Recovery must not duplicate either. Enrolment history is separate and does not change session membership; sending email, booking cancellation, and additional eligibility policies remain separate capabilities.
