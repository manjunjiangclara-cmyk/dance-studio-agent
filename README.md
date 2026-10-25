# Ballet Studio AI Copilot

An independent portfolio project for teacher-reviewed ballet studio administration. Initial students, locations, and messages are synthetic; no real studio adoption or endorsement is claimed.

## Current scope

The MVP prepares drafts for teacher review. It loads student context, routes enquiries by intent, interprets consecutive makeup emails, and queries classes. Other or unclear request types receive a teacher-handoff draft until their flows are implemented. Approval means a draft has been reviewed; it does not book classes or send email.

The backend implements staff administration and a LangGraph makeup-enquiry workflow using the OpenAI Responses API. It manages studio records, conversation history, bounded read-only tool use, automatic student memory, and teacher review through the API. Approval stores the final teacher response and reconciles memory; it does not send email or execute bookings. A browser review UI is not implemented.

Students have an optional `highest_level`, nullable `ai_summary`, source-linked conversational `context`, an `enrolment_history` relationship, and a read-only `current_enrolments` field derived from that history. Classes belong to terms; dated sessions expose their regular student roster through enrolments.

## Local setup

Start Docker Desktop first. From this project directory:

```sh
docker compose up -d --wait db
cd backend
uv sync --frozen
uv run --env-file .env.example alembic upgrade head
uv run --env-file .env.example alembic check
```

The Compose database is available only on localhost, on port 5433 by default. Its fixed credentials are for this local synthetic demo only. Set `POSTGRES_PORT` for Compose and adjust connection URLs together if that port is occupied. Named Docker storage preserves data when the container stops. `docker compose stop db` stops the database without removing its data.

`.env.example` contains working local development URLs. To customize them, copy it to an ignored `.env` and use `--env-file .env`. Configuration comes from `DATABASE_URL`; models never create or alter tables automatically. The project uses native Python 3.12, selected by `backend/.python-version`, with dependencies pinned in `backend/uv.lock`.

## Run the real app

After local setup, start the actual application server from `backend/`:

```sh
uv run --env-file .env uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
```

This command assumes you have created `.env` as described above. If you are using only the example configuration, replace `--env-file .env` with `--env-file .env.example`. AI draft generation also requires the agent setup below and configured `OPENAI_API_KEY` and `OPENAI_MODEL`; it uses the real model and incurs API usage charges.

Leave the terminal running and open [interactive API documentation](http://127.0.0.1:8000/docs). This is the current way to interact with the app; a dedicated staff UI is not implemented. Use **Authorize** with your `ADMIN_API_TOKEN` (the example configuration uses `local-demo-admin-token`). All `/api/v1` endpoints require that bearer token; [health](http://127.0.0.1:8000/health) and documentation are public. A healthy database connection returns `{"status":"ok"}`. This is one local staff credential, not a user-account or role-management system.

On subsequent launches, start Docker Desktop, run `docker compose up -d --wait db` from the project directory, and run the server command above from `backend/`. Stop the server with Ctrl+C.

## Test an email through one API call

After agent setup and starting the server, open [Swagger](http://127.0.0.1:8000/docs), authorize with your admin token, and use **POST `/api/v1/incoming-emails`**. Supply only the sender and email content:

```json
{
  "from": "new.enquirer@example.com",
  "body": "I have never done ballet. Which class would suit me?"
}
```

The server finds the student, selects their latest conversation (or creates one), records receipt time, saves the email and generates a draft. An unknown sender gets a minimal `New enquirer` profile with no level or enrolments, and their first email enters the new-student teacher-handoff flow. Later emails reuse their history and use normal intent routing.

For a known student, send the same two fields with their registered email address, for example `alex.demo@example.com`. Check `status` for `awaiting_review` and read `draft_details.body`, `interpretation` and `evidence`. HTTP 200 can also contain a `failed` run: inspect `error` and retry that run using `/api/v1/agent-runs/{id}/retry`. Review, edit or approve using the existing run review endpoint. Approval stores a response without sending it or booking a class.

No conversation, message or run IDs are needed as input. Each POST is a new email, even if its content repeats. A busy student returns 409 without saving the submission. Model configuration or policy errors return 503 before records are created.

The existing demo conversation contains February 2027 emails. Before those dates, submitting a current-time email to that conversation returns 409 because a future-dated email is already the latest. To test intake now, use a fresh fictional address such as the example above, or a registered student whose conversation has no future-dated emails. Retrying a failed run uses its ID rather than submitting the email again.

## Optional: load sample data

To populate an empty database for a walkthrough, run this once from `backend/` using the same environment file as the server:

```sh
uv run --env-file .env python -m studio_copilot.demo
```

`demo.py` only inserts fictional students, classes, enrolments, and conversation messages into the database. It does not start a server or run a separate demo application. The real app uses these records when you inspect them or start an AI run through the API. You can instead create records through the administration API.

The seed command prints useful IDs. It creates fictional February–March 2027 data once and preserves edits on subsequent runs. `"created": false` means the demo records already exist and were left untouched; it is not an error. You do not need to rerun it when starting the app. Use `on_date=2027-02-08` when inspecting the seeded student's current-enrolment view; the normal default is today's Melbourne date. Seeded drafts and context are predefined examples, not AI-generated results.

See the [API guide and walkthrough](docs/07-api.md) for endpoints, filters, enrolment operations, and current limitations.

## Agent setup

After applying the application migration, provision LangGraph checkpoints from `backend/`:

```sh
uv run --env-file .env.example python -m studio_copilot.agent.persistence.checkpoints
```

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in an ignored `.env` or your shell, then start the server using that environment. Studio policy is editable in `backend/policies/studio.yaml`. See the [agent API walkthrough](docs/08-agent-api.md) for starting runs, teacher review, memory updates, retries, and optional live evaluation. The normal test suite uses a fake model and makes no OpenAI requests.

The checkpoint setup command prepares database tables that save workflow progress for teacher review and recovery. “LangGraph checkpoint tables are ready” confirms that setup completed; it does not start the app or generate a draft. Use the same environment file for checkpoint setup and the server so they connect to the same database.

## Verification

Create the separate test database once, from the project directory:

```sh
docker compose exec db createdb -U copilot studio_copilot_test
```

Then, from `backend/`:

```sh
uv run --env-file .env.example pytest
uv run ruff check .
uv run ruff format --check .
```

Tests are grouped by execution requirements and behavior:

- `backend/tests/unit/`: enrolment rules and the OpenAI SDK adapter with mocked HTTP; no database or live OpenAI calls.
- `backend/tests/integration/persistence/`: fresh schema/model parity, database constraints, enrolment history, and student memory.
- `backend/tests/integration/api/`: students, enrolments, timetable, conversations, validation, access, and demo seeding.
- `backend/tests/integration/agent/`: routing, review, memory, recovery, access, policy, tools, and tool limits, using scripted model responses.
- `backend/evaluations/`: optional paid live-model checks, outside normal pytest discovery.

Run an individual group from `backend/`, for example:

```sh
uv run pytest tests/unit
uv run --env-file .env.example pytest tests/integration/agent
```

Integration tests require `TEST_DATABASE_URL` with a database name ending in `_test`. Each test creates and removes its own temporary schema there. Without that variable, PostgreSQL tests are explicitly skipped. The schema check verifies that a fresh installation matches the models. Fake-model tests do not establish live model understanding or booking reliability.

The pre-release migration history is consolidated into one initial migration containing the current nine-table application schema. Existing disposable development databases stamped with an earlier revision need to be recreated before applying this baseline; the consolidated revision is for fresh installations and does not upgrade the old revisions. LangGraph checkpoint setup remains separate.

## Design documents

- [PRD and configurable policies](docs/01-prd.md)
- [Domain, database schema, and ER diagram](docs/02-domain-and-schema.md)
- [Draft-and-review workflow](docs/03-makeup-workflow.md)
- [Architecture and repository](docs/04-architecture.md)
- [Incremental backlog](docs/05-backlog.md)
- [Accepted direction and open decisions](docs/06-decisions.md)
- [Administration API guide](docs/07-api.md)
- [Agent setup, APIs, and evaluation](docs/08-agent-api.md)

The original detailed booking design is superseded by this simpler direction. Policies remain external resources; financial rules, credit ledgers, booking execution, and production infrastructure will be designed when those capabilities are introduced.
