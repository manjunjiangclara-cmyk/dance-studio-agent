# Email workflow evaluations

Thirty-eight synthetic scenarios exercise email intake through the real FastAPI app,
LangGraph workflow, read-only tools, PostgreSQL persistence/checkpoints, and teacher
review. The runner uses the existing OpenAI adapter and configured `OPENAI_MODEL`.
It does not access a mailbox, send email, or exercise browser UI.

## Run

From `backend/`, with dependencies installed:

```sh
# Inspect the dataset without a database or API key.
uv run python -m workflow_evaluations.evaluate --list

# Load your ignored .env, including TEST_DATABASE_URL, OPENAI_API_KEY, OPENAI_MODEL.
# This makes paid live calls. Start with one case.
uv run --env-file .env python -m workflow_evaluations.evaluate --live --case makeup_approval

# Repeat selected conversations independently to inspect variability.
uv run --env-file .env python -m workflow_evaluations.evaluate --live \
  --case followup_correction --case prompt_injection --repeat 3

# Evaluate a teacher answer fed back into an enquiry redraft.
uv run --env-file .env python -m workflow_evaluations.evaluate --live \
  --case enquiry_checklist_answer_redraft

# Run all scenarios.
uv run --env-file .env python -m workflow_evaluations.evaluate --live
```

Use `UV_CACHE_DIR=/private/tmp/dance-studio-uv-cache` if the default uv cache is
unavailable in the local sandbox. The original `python workflow_evaluations/evaluate.py`
entry point also works, with the same flags.

`TEST_DATABASE_URL` must use `postgresql+psycopg`, name an existing database ending
in `_test`, and contain no URL query options. The database user needs schema-create
permission. Each scenario/repeat gets a fresh randomly named schema, migrated to
head and provisioned with LangGraph checkpoints. That schema is dropped afterward,
including when a scenario fails. The runner never falls back to `DATABASE_URL`.
Each fixture also has unique sender addresses because sender advisory locks are
shared across schemas in a database.
An abruptly killed process may leave its `eval_*` schema behind.

The fixture resolves explicit email dates relative to the run's Melbourne date:
next week's Monday absence, Thursday/Saturday candidates, or a previous Monday for
late notice. All booking candidates remain in the future without changing the
application clock. Resolved dates and the reference timestamp are saved in the report.
These initial cases do not evaluate ambiguous relative-date phrases.

## Scenarios and scoring

`emails[].thread` names the email thread within a scenario. The default is `main`.
Different names use the same sender and subject with different thread IDs. The
runner checks model-visible message IDs and conversation-memory keys, and checks
that intake on one thread preserves pending runs on the other. Set
`emails[].approve_after` on a non-final email to test replies after a real teacher
approval. Each intake and review is checked against its immediately preceding
database state. The top-level `review` still applies to the final email.
`expect.existing_makeup` checks the previously booked session and its evidence
reference. Omit `flow` or `intents` when the outcome can be valid under multiple routes.

Edit `scenarios.json` to add inputs, fixtures, expected fields, and review actions.
`{absence_date}`, `{thursday_date}`, and `{saturday_date}` expand to fixture dates.
Unknown fields, duplicate IDs, and invalid structured expectations fail validation.

Each scenario declares its starting student level, regular enrolments, and dated
session rosters explicitly. For example:

```json
"setup": {
  "student": {"highest_level": "Level 2"},
  "enrolments": [{"class_key": "monday_level_2", "status": "active"}],
  "level_order": ["Level 1", "Level 2", "Level 3"],
  "attended_level": "Level 2",
  "absence_attendance": "unknown",
  "session_rosters": {"absence": ["student"], "thursday": [], "saturday": []}
}
```

Class keys resolve to the synthetic Monday/Thursday/Saturday Level 2 classes;
roster keys identify dated sessions, with `absence` being the Monday session.
`student` is the known sender and `other_student` is an unrelated synthetic student.
An enrolment, membership in a dated session, and actual attendance are separate facts.
The synthetic policy order runs from easiest to hardest; `attended_level` creates a
separate, past attended session. It defaults to Level 2; set it to null to test
missing history. `absence_attendance` is attended, absent, or unknown. Candidate
levels default to Level 2 and can be overridden with `thursday_level` and
`saturday_level`. A `conflicting_booking`, when present, adds a separate Thursday
session for the student; its start offset is relative to the 6 pm candidate. Each
scenario uses an isolated synthetic policy, not the live studio
policy. The attendance-conflict scenario backdates the first synthetic email to before
the past Monday session so it represents a genuinely earlier notice. The `fixture`
selects date/session variants (past absence, no replacements), while `setup` declares
the actual enrolments and rosters. Both symbolic setup and resolved dates/IDs are
saved in reports. New senders begin without enrolment or session membership; the
declared setup describes the pre-existing known student.

The `review` field tells the harness which valid API actions to perform. In
particular, `approve_twice` sends two `approve` requests to test idempotency; it is
not an agent contract value. `answer_checklist` finds the single teacher-input question
containing `checklist_answer.question_contains`, submits its answer, and records the
model input and raw draft before deterministic validation. The automated checks verify
the association, teacher-answer citation, required and forbidden terms in the raw
answer and body, revised draft, stale-review rejection, and unchanged business records.
Term checks are deliberately narrow and may reject valid paraphrases; the rubric
requires a human to inspect the raw prose for meaning and unsupported claims.
Optional `review_body` supplies the final edited reply
for a non-booking approval; booking approvals require the unchanged draft. `rubric` remains a human
review checklist.

Automated checks cover:

- Reviewable status, expected flow/intents, extracted dates, missing details,
  requested tools, evidenced booking proposals, and grounded reference strings.
- Verified absence session and source notice, plus validated replacement candidates,
  for every booking proposal. `makeup_approval` also asserts enrolment/notice/
  membership verification happens before searching replacements.
- Existing target membership and missing dated absence membership, even when the
  regular enrolment exists.
- Contradictory attendance, class levels above the highest actually attended level,
  missing attendance history, and options enquiries that do not book a session.
- Absence timing where required, without inventing a makeup-eligibility policy.
- Preserved incoming email text and no roster/enrolment/attendance/approved-response
  changes during drafting, including attempted instruction injection.
- Multi-email thread follow-ups retaining the original absence notice, superseding
  earlier drafts, and blocking stale approval.
- Committed student-stated memory before drafting and after each incoming email,
  with the current source email, request summary, and extracted lasting preferences.
- Teacher-reviewed memory after approval, linked to the final stored teacher response
  and matching the reconciliation output.
- Rejection, revision, failed approval, and repeated approval preserving memory as appropriate.
- Approval, duplicate approval, revision, rejection, checkpoint recreation, and
  capacity changes between drafting and approval.
- Unrelated synthetic student canaries staying out of returned evidence/drafts.

Structured checks do not establish complete semantic accuracy, identity-redaction
coverage, tone, or helpfulness. Each scenario also has a **human review rubric**.
Inspect every saved draft and revision against its inputs, evidence, and rubric.
`human_review` remains `pending`; a green automated result does not approve the prose.
Proposed confirmation language is valid only when an evidenced booking proposal
will execute on teacher approval. Unsupported enrolments/cancellations must not be
described as completed business actions.

Reports are written incrementally to ignored `workflow_evaluations/results/*.json`, or to
`--output PATH`. They include the model, dataset hash, resolved fixture, full inputs,
run/evidence/draft snapshots, review results, named checks, final database snapshot,
latency, and available token usage. Only synthetic data is supported by this dataset.
Provider/database exception messages and credentials are not included.

`memory_snapshots` records fresh database reads at each checked lifecycle boundary,
with observation timestamps. These establish commit visibility and ordering, rather
than asserting an arbitrary elapsed-time threshold. Raw emails are stored on receipt;
structured student memory is saved after interpretation, before drafting/review.
Approval stores the final teacher response first, then reconciles memory before the
run becomes `approved`. Comparing reconciliation output with saved memory verifies
persistence; the rubric still requires human review of the memory's meaning.

`--max-calls-per-case` defaults to 24 adapter requests, including follow-ups and
review. The existing adapter may retry a request once. An exhausted budget or failed
model request fails the scenario even if the application produces a fallback draft.
An automated failure returns a nonzero exit code; inspect the report before changing
an expectation. Do not weaken expectations merely to get a passing model score.

## Harness regression checks

Two adversarial safety evaluations use fictional emails, controlled model outputs,
the real workflow, and PostgreSQL. They deliberately inject a wrong notice selection
or a wrong-day draft, then inspect the approval and roster. Run them with:

```sh
uv run --env-file .env pytest tests/integration/agent/test_safety_evaluations.py --runxfail
```

Positive controls use a relevant notice and a matching draft. These probes test
whether the system contains a model mistake; they do not measure how often the real
model makes that mistake.

The current automatic notice check accepts only a narrow, unqualified first-person
absence statement containing the missed date in ISO format, optionally followed by a
small set of unambiguous makeup requests. Conflicting context, multiple enrolled
sessions on the same date, other phrasing, and relative dates require staff review;
the reviewer cannot currently
confirm an ambiguous notice through a dedicated action. This conservative text check
does not establish the full meaning of a conversation and must not be treated as a
general natural-language verifier.

Normal pytest runs use a controlled model to verify the grader and workflow harness
without OpenAI requests. Database-backed harness checks require `TEST_DATABASE_URL`:

```sh
uv run pytest tests/unit/test_evaluation_grading.py
uv run --env-file .env pytest tests/integration/agent/test_evaluations.py
```

Those deterministic checks verify the evaluator's plumbing. Only `--live` measures
the configured model on the email dataset. The local dataset/runner approach follows
OpenAI's guidance to use task-specific cases, measurable criteria, and human review:
[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
