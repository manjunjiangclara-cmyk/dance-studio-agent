# Ballet Studio AI Copilot

An independent portfolio project for teacher-reviewed ballet studio administration. Initial students, locations, and messages are synthetic; no real studio adoption or endorsement is claimed.

## Current scope

The app prepares drafts for teacher review and handles makeup requests using a LangGraph workflow. The agent verifies the missed session and notice, checks actual attendance and eligible replacement sessions, and leaves the final decision to a teacher. Approving a draft with a verified booking proposal adds the student to that session atomically; approval never sends email. Information-only requests use an enquiry workflow with a question-by-question review checklist. Other business actions or unclear requests go to teacher handoff. For missing studio facts, teachers provide an answer or explicitly choose to confirm later beside each question, then update the draft before approval. Teacher answers stay scoped to the conversation. The owner can maintain a document library and use explicit CLIs to inspect chunks, prepare revision-pinned PostgreSQL embeddings, and search selected revisions. Teachers can explicitly prepare and enable documents in Studio Knowledge; the opt-in online answer path retrieves enabled revisions, prepares citation-checked answers and composes a teacher-reviewed email. The checker’s concerns appear separately beside the draft for the teacher to review. See [online document answers](docs/20-online-document-answers.md).

Dated sessions have independent student rosters. Staff separately record attendance as attended, absent, or unknown. The studio policy defines the order of class levels from easiest to hardest; makeup candidates cannot exceed the student's highest recorded attended level. Missing attendance or level order requires staff review. Historical runs retain their policy snapshots.

The public record browser and recorded tour use predefined fictional data without model calls. The public Studio Knowledge document library loads the fictional catalog from the public demo API. The guided tour also offers opt-in live AI: visitors click to select supporting evidence from a fixed fictional catalog, then provide responses to missing information before generating a fresh draft. A separate persistent ledger limits the public service to 20 runs per Melbourne day. Booking and database confirmations remain simulated, and studio records are never accessed or changed. Email walkthrough lets visitors write a fictional email as a new enquirer or one of the example students, with editable draft and evidence under the same allowance. See [public live demo](docs/22-public-live-demo.md). The public Review Queue also offers four fictional enquiries with on-demand live drafts, editable responses, supporting evidence and source details; booking confirmation is simulated and results remain local to the page. The owner workspace provides a review queue, Studio knowledge area for documents, attendance controls, and database inspection. The library accepts UTF-8 `.txt` and `.md` files up to 10 MB, retains immutable revisions, and supports effective dates, duplicate-content notices, and paginated previews. Files up to 1 MB can also be edited inline. Ingestion alone does not publish or enable documents for the agent. See [document ingestion](docs/10-document-ingestion.md). See [website setup](docs/09-website.md).

## AWS deployment

The complete application can be packaged for a single EC2 host while retaining its
PostgreSQL/pgvector and LangGraph persistence. See the [EC2 deployment guide](docs/23-ec2-deployment.md)
for Terraform, private configuration, HTTPS, releases and backup verification. The Aurora
Data API work remains an isolated feasibility experiment.

## Local setup

In Codex, use `$run-dance-studio-app` to start the local app with the portal origin matched to the configured Google callback.

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

Build the frontend from `frontend/` with a supported Node.js version using `npm ci` and `npm run build`. Leave the server running and open [the public demo](http://127.0.0.1:8000/demo) or [interactive API documentation](http://127.0.0.1:8000/docs). Use **Authorize** with your `ADMIN_API_TOKEN` (the example configuration uses `local-demo-admin-token`). The staff API requires that bearer token or an authorized owner session for its permitted operations; [health](http://127.0.0.1:8000/health) and documentation are public. A healthy database connection returns `{"status":"ok"}`. This is one local staff credential, not a user-account or role-management system.

On subsequent launches, start Docker Desktop, run `docker compose up -d --wait db` from the project directory, and run the server command above from `backend/`. Stop the server with Ctrl+C.

## Test an email through one API call

After agent setup and starting the server, open [Swagger](http://127.0.0.1:8000/docs), authorize with your admin token, and use **POST `/api/v1/incoming-emails`**. For a standalone email, supply the sender and email content:

```json
{
  "from": "new.enquirer@example.com",
  "body": "I have never done ballet. Which class would suit me?"
}
```

To group replies, send the same optional `thread_id` on every intake request. An optional `subject` labels the thread. The server reads the full student email history for that thread. Requests without a thread ID reuse the sender’s latest unthreaded conversation or create one. An unknown sender gets a minimal `New enquirer` profile with no level or enrolments, and their first email uses the same action-based routing as existing students. Later emails reuse their history.

For a known student, send the same two fields with their registered email address, for example `alex@example.com`. Check `status` for `awaiting_review` and read `draft_details.body`, `interpretation` and `evidence`. HTTP 200 can also contain a `failed` run: inspect `error` and retry that run using `/api/v1/agent-runs/{id}/retry`. Review, edit or approve using the existing run review endpoint. Approval stores a response and, when a validated booking proposal is present, adds the student to that session. It does not send email.

No conversation, message or run IDs are needed as input. Each POST is a new email, even if its content repeats. A busy student returns 409 without saving the submission. Model configuration or policy errors return 503 before records are created.

Retrying a failed run uses its ID rather than submitting the email again. Future-dated existing messages still prevent earlier incoming emails from superseding them.

## Optional: load sample data

To populate an empty database for a walkthrough, run this once from `backend/` using the same environment file as the server:

```sh
uv run --env-file .env python -m studio_copilot.demo
```

`demo.py` only inserts fictional students, classes, enrolments, and conversation messages into the database. It does not start a server or run a separate demo application. The real app uses these records when you inspect them or start an AI run through the API. You can instead create records through the administration API.

The fictional Merri Ballet demo uses Brunswick and Carlton rooms, adult Level 2 ballet classes, and Term 1 · Summer 2027. Names and addresses are invented; student emails use the reserved `example.com` domain. Existing seeded records keep their original values because rerunning the seed never overwrites staff edits. If an earlier demo seed used `alex@example.test` or `sam@example.test`, update those student emails through the administration API to `alex@example.com` and `sam@example.com` before using email intake; `.test` addresses are rejected by the intake validator.

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
uv run python -m studio_copilot.documents.chunking --prepare-tokenizer
uv run --env-file .env.example pytest
uv run ruff check .
uv run ruff format --check .
```

The default `uv sync --frozen` installs the development group, including the AWS
validation test dependencies (`boto3`/`botocore`). No extra AWS group flag is needed
for the documented test commands; these tests use mocked AWS clients.

Tests are grouped by execution requirements and behavior:

- `backend/tests/unit/`: enrolment rules and the OpenAI SDK adapter with mocked HTTP; no database or live OpenAI calls.
- `backend/tests/integration/persistence/`: fresh schema/model parity, database constraints, enrolment history, and student memory.
- `backend/tests/integration/api/`: students, enrolments, timetable, conversations, validation, access, and demo seeding.
- `backend/tests/integration/agent/`: routing, review, memory, recovery, access, policy, tools, and tool limits, using scripted model responses.
- `backend/evaluations/`: optional paid email-drafting evaluations, outside normal pytest discovery.
- `backend/workflow_evaluations/`: optional paid scenarios covering attendance, booking proposals, teacher review, and idempotency.

Run an individual group from `backend/`, for example:

```sh
uv run pytest tests/unit
uv run --env-file .env.example pytest tests/integration/agent
```

Integration tests require `TEST_DATABASE_URL` with a database name ending in `_test`. Each test creates and removes its own temporary schema there. Without that variable, PostgreSQL tests are explicitly skipped. The schema check verifies that a fresh installation matches the models. Fake-model tests do not establish live model understanding or booking reliability.

Alembic upgrades the consolidated initial schema through the independent-session roster and attendance migrations. The roster migration snapshots historical participants and has no automatic downgrade because that would lose data. LangGraph checkpoint setup remains separate.

### Multi-turn email evaluations

The workflow suite covers consecutive makeup corrections, withdrawal of an
absence after a correction, interleaved threads from the same sender, and a date
change after teacher approval. It checks which messages reach the model,
whether stale drafts can be approved, and what changes in the booking records.

Run the three transition cases from `backend/` using synthetic fixtures in the
configured PostgreSQL test database:

```sh
uv run --env-file .env python -m workflow_evaluations.evaluate --live \
  --case withdraw_absence_after_correction \
  --case interleaved_threads_keep_context \
  --case reschedule_after_approval
```

Live runs call the configured model and incur usage costs. The JSON report
includes structured checks and draft text for manual review. See the
[workflow evaluation guide](backend/workflow_evaluations/README.md) for the
scenario format and test database requirements.

## Design documents

- [PRD and configurable policies](docs/01-prd.md)
- [Domain, database schema, and ER diagram](docs/02-domain-and-schema.md)
- [Draft-and-review workflow](docs/03-makeup-workflow.md)
- [Architecture and repository](docs/04-architecture.md)
- [Incremental backlog](docs/05-backlog.md)
- [Accepted direction and open decisions](docs/06-decisions.md)
- [Administration API guide](docs/07-api.md)
- [Agent setup, APIs, and evaluation](docs/08-agent-api.md)
- [Website and owner workspace](docs/09-website.md)
- [Isolated Aurora Data API feasibility validation](docs/22-aurora-data-api-validation.md)
- [Document ingestion and revision APIs](docs/10-document-ingestion.md)
- [Document RAG design and roadmap](docs/11-rag-design.md)
- [Revision-pinned embedding CLI and recovery](docs/13-document-embeddings.md)
- [Retrieval CLI, source references, and paired keyword/vector/hybrid evaluation](docs/14-document-retrieval.md)
- [Offline local reranking and measured adoption gates](docs/15-document-reranking.md)
- [Consolidated tests, benchmarks, and real model evaluations](docs/16-testing-and-evaluations.md)
- [Offline generation, exact citations and optional verification](docs/17-document-generation.md)
- [Production foundations: ACL, query cache, task budgets and private telemetry](docs/18-production-controls.md)
- [Online document answers and source activation](docs/20-online-document-answers.md)
- [Integrated RAG quality evaluation](docs/21-integrated-rag-evaluation.md)
- [Whole-agent simulated-use evaluation and results](docs/measurements/whole-agent-portfolio-evaluation-2026-11-16.md)
- [Tracing and observability](docs/19-tracing-and-observability.md)
- [Offline chunking and inspection CLI](docs/12-document-chunking.md)

Policies remain external resources. Financial rules, credit ledgers, email delivery, and production infrastructure remain outside the implemented workflow.
