# Ballet Studio AI Copilot

An independent portfolio project for teacher-reviewed ballet studio administration. Initial students, locations, and messages are synthetic; no real studio adoption or endorsement is claimed.

## Current scope

The MVP prepares drafts for teacher review. It will load student context, consult editable policies, interpret consecutive emails, and query classes. Approval means a draft has been reviewed; it does not book classes or send email.

The traditional administration backend is implemented with FastAPI, PostgreSQL, SQLAlchemy, and Alembic. It manages students, timetables, enrolments/history, and manually recorded conversations through a staff API. The eight-table schema is unchanged. The agent, review UI, and automatic memory updates are not implemented yet.

Students have an optional `highest_level`, conversational `context`, an `enrolment_history` relationship, and a read-only `current_enrolments` field derived from that history. Classes belong to terms; dated sessions expose their regular student roster through enrolments.

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

## Run the administration API

From `backend/`, optionally add the synthetic walkthrough data, then start the server:

```sh
uv run --env-file .env.example python -m studio_copilot.demo
uv run --env-file .env.example uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
```

Open [interactive API documentation](http://127.0.0.1:8000/docs). Use **Authorize** with the local example token `local-demo-admin-token`. All `/api/v1` endpoints require the configured `ADMIN_API_TOKEN` as a bearer token; `/health` and documentation are public. This is one local staff credential, not a user-account or role-management system.

The seed command prints useful IDs. It creates fictional February–March 2027 data once and preserves edits on subsequent runs. Use `on_date=2027-02-08` when inspecting the seeded student's current-enrolment view; the normal default is today's Melbourne date. Seeded drafts and context are predefined examples, not AI-generated results.

See the [API guide and walkthrough](docs/07-api.md) for endpoints, filters, enrolment operations, and current limitations.

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

Integration tests require `TEST_DATABASE_URL` with a database name ending in `_test`. Each test creates and removes its own temporary schema there. Without that variable, PostgreSQL tests are explicitly skipped. Test downgrade/re-upgrade operations affect those temporary schemas, not the application database. Tests cover persistence and constraints; they do not establish agent understanding or booking reliability.

## Design documents

- [PRD and configurable policies](docs/01-prd.md)
- [Domain, database schema, and ER diagram](docs/02-domain-and-schema.md)
- [Draft-and-review workflow](docs/03-makeup-workflow.md)
- [Architecture and repository](docs/04-architecture.md)
- [Incremental backlog](docs/05-backlog.md)
- [Accepted direction and open decisions](docs/06-decisions.md)
- [Administration API guide](docs/07-api.md)

The original detailed booking design is superseded by this simpler direction. Policies remain external resources; financial rules, credit ledgers, booking execution, and production infrastructure will be designed when those capabilities are introduced.
