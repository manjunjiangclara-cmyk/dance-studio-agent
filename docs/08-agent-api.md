# Agent setup and API walkthrough

## Setup

From `backend/`:

```sh
uv sync --frozen
uv run --env-file .env.example alembic upgrade head
uv run --env-file .env.example python -m studio_copilot.agent.persistence.checkpoints
```

The second command creates application tables; the third provisions LangGraph's own checkpoint tables and indexes. Run checkpoint setup before accepting agent requests. Alembic schema comparison excludes those framework-managed tables.

Copy `.env.example` to the ignored `.env` and set `OPENAI_API_KEY` and `OPENAI_MODEL` there, or export them in your shell. Choose a Responses API model that supports function calling and structured outputs in your account. No default model is assumed and no real key belongs in the repository. Optional `STUDIO_POLICY_PATH` overrides `policies/studio.yaml`; commands assume the working directory is `backend/`.

```sh
uv run --env-file .env python -m studio_copilot.demo
uv run --env-file .env uvicorn studio_copilot.api.app:app --host 127.0.0.1 --port 8000
```

The ordinary staff API and agent-result GET work without OpenAI credentials. Agent processing returns 503 if model/key configuration is missing. Calls to the real OpenAI API incur usage charges. There is no fake-model production mode; tests explicitly inject their fake adapter.

## Single email entrance

Use authenticated `POST /api/v1/incoming-emails` to submit an email and generate a draft in one request:

```json
{
  "from": "new.enquirer@example.com",
  "body": "I have never done ballet. Which class would suit me?"
}
```

A known sender is matched case-insensitively and their latest conversation is reused (ordered by creation time, then ID). If none exists, a conversation is created. For a known-student example, use `alex.demo@example.com` with the same `from` and `body` fields. An unknown sender gets a minimal profile named `New enquirer`, with unknown level and no enrolments, plus a conversation. Their first run is routed to `new_student_enquiry` / `teacher_handoff`; this routing context is retained for recovery. Later submissions from that sender use ordinary intent routing and the stored history. Staff can update the placeholder profile through existing student APIs.

The server sets receipt time and returns the existing agent-run response synchronously: inspect `status`, `draft_details.body`, `interpretation`, `evidence` and `error`. The response includes IDs needed for review or recovery; callers supply none. A successful draft is `awaiting_review`; a processing failure returns a retained `failed` run that can be retried through `/agent-runs/{id}/retry` without inserting another email. Approval still requires an explicit review request.

Missing model configuration or invalid policy returns 503 before intake writes. A busy student returns 409 without saving the submission. Validation requires a valid `from` address and nonblank `body`; other input fields are rejected. Each POST represents a new received email; repeated bodies are not deduplicated.

Existing future-dated conversation emails also produce 409 without saving the submission, preserving the latest-email rule. In particular, the seeded Alex conversation contains February 2027 emails. Before then, use a fresh fictional address or a student without future-dated history for current-time intake testing. The endpoint does not connect an inbox, enrol students, reserve places or send responses.

## Endpoints

All routes require the existing admin bearer token and have prefix `/api/v1`.

| Route | Request and result |
| --- | --- |
| POST `/incoming-emails` | `{"from":"someone@example.com","body":"Email content"}`. Resolves sender/history, saves the email, and runs the agent. |
| POST `/conversations/{id}/agent-runs` | `{"source_message_id":"UUID"}`. Source must be the latest student email in that conversation. Runs synchronously to review or failure; repeat starts return the existing run. |
| GET `/agent-runs/{id}` | Returns status, revision, interpretation, evidence, policy snapshot, draft details, linked message IDs, and a safe error if processing failed. |
| POST `/agent-runs/{id}/review` | `{"action":"approve","expected_revision":1,"body":"Final teacher response"}`. Body is optional; defaults to the current draft. Stores a teacher response, then updates memory. |
| POST `/agent-runs/{id}/review` | `{"action":"revise","expected_revision":1,"feedback":"Please ask which location they prefer."}`. Feedback is required; generates a new draft revision with a fresh bounded query budget. |
| POST `/agent-runs/{id}/review` | `{"action":"reject","expected_revision":1}`. Closes review without a rejection message/event and removes checkpoints. |
| POST `/agent-runs/{id}/retry` | No body. Resumes failed or interrupted processing from its checkpoint. Cannot restart a closed, approved, or superseded run. |

The run exposes classification at `interpretation.routing` (intents, summary, clarification flag, reason) and the selected branch at `interpretation.flow` (`makeup` or `teacher_handoff`). The router recognizes future request categories without implementing their workflows. Unsupported or mixed independent requests bypass makeup extraction and tools and produce a teacher-handoff draft. There are no makeup date fields on that general interpretation.

Start/review/retry return 200 with the current run. A provider or checkpoint failure is visible as `status=failed`; the HTTP response alone does not establish successful processing. A new message arriving while processing, or a stale review revision, returns 409. Inspect the run after a network interruption before retrying.

`status` is `running`, `awaiting_review`, `finalizing`, `approved`, `closed`, `superseded`, or `failed`. `finalizing` means the teacher response has been stored but memory reconciliation is still running. Retrying failed finalization reuses the same response and remains available after newer emails. Recovery retains the earlier approved outcome without replacing newer request memory or preferences. Repeating the same completed approval returns its existing response; a conflicting edit is rejected.

Use GET `/messages/{draft_message_id}` or `draft_details.body` to display the generated draft. Edit agent drafts through the review body, not the generic message PATCH. The final response is separately available at `/messages/{approved_response_id}` and in conversation history. The linked draft remains the generated version for comparison.

## Walkthrough

1. Seed the demo and authorize in Swagger using the local admin token.
2. Use the printed conversation ID to GET its messages and select the latest `student_email` ID. Start an agent run with that ID.
3. Inspect interpretation, evidence, unanswered questions, and draft. GET the student profile to inspect the first memory update.
4. Request a revision if useful. Submit approval with the returned revision and your final edited response body.
5. Inspect the stored `teacher_response` and student memory. Neither message delivery nor studio records have changed.
6. Add another student email to the same conversation, such as “Actually, Saturday instead,” then start a run for that new message. Older pending drafts become superseded.

## Tests and optional live evaluation

```sh
uv run --env-file .env.example pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --env-file .env.example alembic check
```

The default suite uses a scripted model, real PostgreSQL in isolated test schemas, an actual PostgreSQL checkpoint restart test, and an HTTP mock exercising the installed OpenAI SDK. It does not make paid API requests or establish live model quality.

An optional, paid routing/interpretation smoke evaluation uses three synthetic cases (explicit dates, a consecutive-email correction, and missing details):

```sh
uv run --env-file .env python evaluations/evaluate.py
```

The script lives in `evaluations/` and is not collected by normal pytest runs. It prints the configured model, typed outputs, and measured case results, exiting nonzero for a failed case. It is a small interpretation baseline, not a full draft-quality or booking-reliability benchmark.

Agent logs emit JSON node transitions, run IDs, tool names, latency, token usage, and safe failure types. They omit email bodies, model output text, API keys, and provider exception details. Runtime state and evidence remain inspectable through the staff API; no external tracing service is required.
