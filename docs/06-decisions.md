# Accepted direction and open decisions

## Agreed direction

- Begin with a draft-and-review MVP; do not execute business changes or send email.
- Make studio policies editable input resources. Keep notice-before-start; remove the invented two-credit limit. Defer detailed policy definition.
- Give the agent student conversation memory across follow-up emails.
- Keep the initial data model small; do not generate regular-session booking records or duplicate student arrays.
- Implement studio data and conversation storage in the first database migration.
- Include highest level and a current-enrolment view on the student; preserve enrolment history as its own entity.

## Database implementation choices

- Eight tables: students, terms, locations, classes, class sessions, enrolments, conversations, and messages.
- `highest_level` is an optional staff-maintained label, separate from conversational context.
- `Enrolment` is the history entity. `Student.current_enrolments` is a read-only field derived from its dated records; it supports multiple regular classes.
- Changing classes should end an old attendance period and add a new one. Cancelled registrations are distinguished from periods that actually occurred. This is history of attendance periods, not a separate event-sourcing system.
- `ClassSession.students` derives the regular roster on the session date. Makeup participation and capacity decisions are not implemented yet.
- Use PostgreSQL, SQLAlchemy, Alembic, and native Python 3.12 with uv. No database connection occurs on module import.

## Open for later discussion

Policy resource shape and additional rules; memory extraction/update behavior; model/provider choice; AI interpretation/review APIs; graph persistence; class suitability rules; makeup booking writes; production reliability; frontend and hosting.

## Traditional backend increment

The owner selected core administration before AI: students, terms/locations/classes/sessions, explicit enrolment changes/history, and manual conversations. These staff commands can write official records; the earlier rule that AI draft approval does not execute business actions still applies. The API uses one local admin token, retains historical records, and provides no hard-delete endpoints. All existing database tables remain unchanged.

These are deferred decisions, not assumed requirements of the database foundation. The previous credit ledger, conditional-offer protocol, and production job infrastructure are not part of this implementation.
