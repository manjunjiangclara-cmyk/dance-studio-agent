# Product requirements — simplified MVP

## Goal

Help teachers understand student emails, find relevant information, and review a personalized response draft. Use synthetic data and keep teachers in control. This is an independent portfolio project, not an adopted studio system.

## Initial capabilities

- Accept a synthetic email associated with a known student and conversation.
- Load official student/enrolment data, conversation history, and student context.
- Understand follow-up messages as part of the discussion: “Actually, Saturday instead” revises an earlier preference.
- Consult editable studio policy resources and query suitable classes at two fictional locations.
- Prepare a response draft and supporting facts for teacher editing, approval, or rejection.
- Retain student messages and approved teacher responses. Update conversational context after interpretation and after approval without changing official enrolments or highest level.

The database foundation and traditional administration API are implemented. Staff can manage students, timetables, enrolments/history, and manually recorded conversations. These explicit staff actions are separate from AI draft approval. The OpenAI/LangGraph enquiry workflow, two-stage memory updates, editable YAML policy, and API-driven teacher review are also implemented. A browser review UI remains subsequent work.

## Policy input

Studio-specific policy is input, not hard-coded application behavior. A YAML resource contains supported structured settings, and each agent run retains its policy snapshot. Backend checks interpret supported settings deterministically. Enabled documents provide policy reference material for answers. New rule types may require code support. Missing or unsupported rules go to teacher review rather than being invented.

Absence notice arriving strictly before session start is the only agreed absence rule so far. There is **no two-credit-per-term limit**. Credit counts, expiry periods, placement rules, seat release after absence, and booking consent are not defined for this MVP. Do not introduce assumed values for them.

## Student information

- `highest_level`: optional staff-maintained profile label. It does not automatically establish prerequisites or permission for every lower-labelled class.
- `current_enrolments`: a current view of dated enrolment records, supporting multiple regular classes.
- Enrolment history: retain previous attendance periods across terms and class changes.
- Conversational context: student-stated preferences, experience, and unresolved requests, grounded in stored messages. Drafts are not communications already sent.

## Acceptance

A teacher can inspect the student's enrolments, conversation, interpretation, supporting policy, and draft. Two consecutive emails preserve relevant context. A supported policy setting can change without editing code. Uncertainty is visible. Review creates no booking, absence record, financial action, or outgoing email.

## Deferred

AI-triggered business actions, absence/makeup booking, credit ledgers, financial workflows, automatic sending, complex multi-intent execution, semantic retrieval, worker queues, production recovery, React, and AWS. Explicit staff enrolment management is available through the traditional API. Add the remaining capabilities incrementally after the draft-and-review journey works.
