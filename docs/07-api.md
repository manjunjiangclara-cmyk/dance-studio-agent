# Traditional administration API

Run commands from `backend/` using the root README's local setup. Start with:

```sh
uv run --env-file .env.example uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
```

[Swagger UI](http://127.0.0.1:8000/docs) and [OpenAPI JSON](http://127.0.0.1:8000/openapi.json) describe the request/response schemas. **Authorize** accepts the configured `ADMIN_API_TOKEN`; the example environment uses `local-demo-admin-token`. Outside Swagger, send `Authorization: Bearer local-demo-admin-token`.

## Endpoints

All paths below have prefix `/api/v1`.

| Resource | Operations |
| --- | --- |
| `/students` | POST create; GET list with optional `q` name/email search. |
| `/students/{id}` | GET profile, current enrolments, and history; optional `on_date` (defaults to today's Melbourne date). PATCH name, email, highest level, or context. |
| `/terms` and `/terms/{id}` | POST/GET list; GET/PATCH individual record. |
| `/locations` and `/locations/{id}` | POST/GET list; GET/PATCH individual record. Timezones are validated IANA names. |
| `/classes` and `/classes/{id}` | POST/GET list; GET individual record; PATCH name, level, prerequisites. List filters: `term_id`, `location_id`, `level`. |
| `/sessions` and `/sessions/{id}` | POST/GET list; GET/PATCH individual record. List filters: `class_id`, `term_id`, `location_id`, `level`, `from_date`, `to_date`. |
| `/sessions/{id}/students` | GET regular student roster for the dated session. |
| `/enrolments` and `/enrolments/{id}` | POST enrol; GET list/individual. List filters: `student_id`, `class_id`, `term_id`, `status`, `on_date`. |
| `/enrolments/{id}/end` | POST `{"ends_on":"2027-02-09"}`; attendance ends on that inclusive date. |
| `/enrolments/{id}/cancel` | POST without a body; staff asserts the registration never took effect. The record remains. |
| `/enrolments/{id}/change` | POST `{"new_class_id":"UUID","effective_on":"2027-02-10"}`; returns `previous` and `replacement` records. |
| `/conversations` and `/conversations/{id}` | POST create; GET list with optional `student_id`; GET individual; PATCH subject. |
| `/conversations/{id}/messages` | POST a manually recorded message; GET chronological messages. |
| `/messages/{id}` | GET message; PATCH body of a draft only. |

List endpoints use `limit` (1–100, default 20) and `offset` (default 0). Responses contain `items`, `total`, `limit`, and `offset`, with deterministic ordering. Session date filters are inclusive local calendar dates in each location's timezone, not the database/server timezone. Both session times and supplied message timestamps must include a UTC offset.

`/health` is public and checks the database. It returns `{"status":"ok"}` or a 503 error.

## Data updates and enrolment history

PATCH changes only supplied fields. `highest_level`, prerequisites, and subject can be cleared with null. Required values cannot be null or blank. Patching `context` replaces the entire JSON object; it does not merge it or infer facts from messages. Highest level is a staff label, not an automatic placement decision.

An enrolment must fit within its class's term. Rejoining the same class is allowed after an earlier period ends, but overlapping attendance periods in that class are rejected. There can be only one active registration per student/class. An end operation cannot extend an existing attendance period. Repeating the same end or cancellation returns the existing outcome.

A class change's `effective_on` is the first day in the new class and must follow the old start date. The old period ends the day before, capped by its existing end/term end. If a target-class check fails, both changes roll back. An unused registration can be cancelled and a new one created. These APIs do not calculate fees, infer prerequisites from level labels, or implement makeup eligibility.

Regular enrolment changes and session capacity changes check the regular roster of existing dated sessions. If a class has no sessions, no global class capacity is inferred; adding its sessions later performs the same check. Absences, makeup seats, holds, and attendance outcomes are outside this API.

Class term/location links are fixed after creation; moving a student uses the enrolment change operation. Term boundaries and location timezone can be edited before classes exist, then remain fixed to preserve interpretation of existing records. Names, addresses, descriptions, and session schedules remain editable through their documented fields. There are no hard-delete endpoints.

## Conversations

Kinds are `student_email`, `assistant_draft`, and `staff_note`. All are entered manually. Incoming emails and notes preserve their original contents; add a new staff note to correct information. Draft bodies can be edited. Messages are ordered by occurrence time, creation time, and ID. There is no send or draft-approval endpoint, and recording messages does not update student context automatically.

## Synthetic walkthrough

1. Run `uv run --env-file .env.example python -m studio_copilot.demo`. It prints stable student, class, term, and conversation IDs. Repeating it preserves edits and creates no duplicates.
2. Open Swagger and authorize. List students; inspect Alex with `on_date=2027-02-08` to see the Monday enrolment.
3. Query `/enrolments?student_id=...` and copy the active enrolment ID. Query sessions by term or location, and inspect the Monday roster.
4. Change Alex to the seeded Thursday class, effective `2027-02-10`. Inspect the profile on February 9 and February 10; history retains both periods.
5. List the seeded conversation's consecutive emails and edit its manually entered draft. No email is sent and no context is generated automatically.

The seed uses fictional February–March 2027 records so it remains reproducible. Its students, locations, policies/descriptions, drafts, and context are examples, not real studio information.

## Errors and verification

Errors use `{"error":{"code":"...","message":"..."}}`; validation errors also include field locations and messages. Expected statuses: 401 missing/invalid token, 404 missing record, 409 conflicting registration/capacity/duplicate data, 422 invalid input, and 503 database unavailable. SQL and connection details are not returned.

Run `uv run --env-file .env.example pytest` against the dedicated test database. Tests exercise complete HTTP journeys with real PostgreSQL, including history, transfer rollback, capacity checks, timezone/date filtering, manual conversations, authentication, validation, and repeatable seed data. Alembic checks continue to verify the unchanged eight-table schema. There is no public deployment, real inbox integration, AI dependency, payment workflow, or staff-account system in this increment.
