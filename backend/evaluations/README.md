# Email evaluations

These synthetic scenarios send email contents through the real intake API,
LangGraph workflow, model adapter, studio tools, and PostgreSQL checkpoints. The
runner stops at `awaiting_review`; it never supplies a teacher decision.

## What each scenario contains

`scenarios.json` separates four concerns:

- **`setup`** declares whether the sender already exists, their level, explicit
  enrolment records, actual attended level, available dated sessions, full sessions,
  and notice timing.
  The overlap case also adds a separate enrolled class on Thursday, with its start
  offset relative to the requested 6 pm session.
- **`steps[].input`** contains the incoming email body. The runner generates a unique
  synthetic sender address per fixture to avoid database-wide sender-lock collisions.
- **`steps[].expected`** mirrors selected fields of the actual agent API output:
  `status`, `interpretation` (including routing), and optionally `draft_details`.
- **`steps[].checks`** declares factual assertions such as successful evidence tools,
  clarification, notice timing, and ignoring an injected marker in the draft.
  `required_any_draft_text` checks for an expected phrase, while
  `contradictory_draft_text` flags specified claims inconsistent with the setup.
  These lexical signals can miss paraphrases or misread context; the full response
  still needs human review.
- **`rubric`** contains criteria for human assessment of the drafts. It is not scored
  automatically; every report keeps human review pending.

For example:

```json
{
  "setup": {
    "student": {"registered": true, "highest_level": "Level 2"},
    "enrolments": [{
      "class_key": "monday_level_2", "status": "active",
      "starts_on": "{term_start}", "ends_on": null
    }],
    "sessions": ["absence", "thursday", "saturday"]
  },
  "steps": [{
    "input": {"body": "I will miss Monday {absence_date}. Could I make it up on Thursday {thursday_date}?"},
    "expected": {
      "status": "awaiting_review",
      "interpretation": {
        "flow": "makeup",
        "routing": {"intents": ["absence", "makeup"]},
        "absence_date": "{absence_date}",
        "preferred_date": "{thursday_date}"
      }
    },
    "checks": {"required_tools": ["search_sessions"]}
  }]
}
```

This excerpt omits the scenario's required ID, description and rubric. Shared class
names, levels, local times and locations are in `catalog.json`. The class keys in
each enrolment refer directly to that catalog. A baseline report saves the complete
resolved setup, catalog, dates, and session UUIDs so the comparison is inspectable.
Synthetic rosters are explicitly seeded from each scenario's enrolments. Historical
attendance is seeded separately from the staff-maintained level label. This suite
stops at teacher review; the richer `workflow_evaluations` suite also exercises
booking proposals and review actions.

Expected dictionaries are partial matches: omitted fields are not compared; explicit
`null` requires a present field whose value is null. Intent lists compare as sets;
other lists compare exactly. All actual routing, interpretation and draft outputs
must also validate against the application's Pydantic contracts. Draft references
must come from evidence or the policy snapshot. Prose is assessed using the rubric,
rather than requiring an exact wording match.

There is no `review`, `approve_twice`, or other teacher action in a scenario.
Approval idempotency belongs in integration tests using two actual `approve`
requests. An eval's expected output is the draft awaiting the teacher's decision.

## Run

From `backend/`, after installing the locked dependencies:

```sh
# No model calls or database access.
uv run python -m evaluations.evaluate --list

# Paid calls using the configured model and only synthetic data.
uv run --env-file .env python -m evaluations.evaluate --live --case clear_makeup

# Compare several independent runs.
uv run --env-file .env python -m evaluations.evaluate --live \
  --case followup_correction --case prompt_injection --repeat 3

# Full baseline, with an explicit output filename.
uv run --env-file .env python -m evaluations.evaluate --live \
  --output evaluations/results/baseline.json
```

Set `TEST_DATABASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in your ignored `.env`
or environment. The original `python evaluations/evaluate.py` entry point works too.
`--live` is required before any paid calls. `--max-calls-per-case` defaults to 24
adapter requests; bounded SDK retries may add provider requests. Failed requests,
refusals, and exhausted budgets fail a scenario even when the app produces a fallback.

The test URL must use `postgresql+psycopg`, name an existing database ending in
`_test`, and have no URL query options. The user needs permission to create schemas.
Each case/repeat gets a random schema, migrations to head, and PostgreSQL checkpoint
setup; the schema is removed in `finally`. The runner never uses `DATABASE_URL`.
An abruptly killed process can leave an `eval_*` schema behind.

Fixture dates resolve from the run's Melbourne date: next week's Monday, Thursday,
and Saturday, or the previous Monday for late notice. `{term_start}`, `{term_end}`,
and `{yesterday}` support explicit enrolment periods. Only known placeholders are
expanded, so JSON braces in email text remain literal. This initial dataset does not
evaluate ambiguous relative-date language.

Reports are saved incrementally under ignored `evaluations/results/`. They contain
the configured model, a hash of scenarios, catalog, and the synthetic evaluation policy, resolved inputs and expected
outputs, actual runs/drafts/evidence, named comparisons, final memory/database state,
latency, and available token usage. Provider/database exception messages and
credentials are omitted. The process exits nonzero when any automated case fails.
Keep prior report filenames when comparing prompt/code/model changes; running with
the same explicit `--output` path replaces that report. No report from a different
checkout or agent contract is included in this PR.

The workflow checks that drafting preserves enrolments, rosters, attendance, and teacher responses.
The suite does not access a mailbox, send email, or drive a browser. Synthetic privacy
canaries and marker checks are limited checks, not comprehensive privacy or semantic
quality guarantees. Human review against the rubric remains necessary.

## Harness tests

Normal pytest does not run live model evaluations:

```sh
uv run pytest tests/unit/test_email_evaluations.py
uv run --env-file .env pytest tests/integration/agent/test_email_evaluations.py
```

These use a controlled model to test the evaluator and its setup/contract matching.
PostgreSQL tests skip without `TEST_DATABASE_URL`; a skip is not a passing DB check.

The unknown refund policy scenario checks for an explicit uncertainty phrase and flags
common numeric currency and percentage claims. These narrow string checks cannot catch
every unsupported claim, so inspect the entire response against the human rubric.

The runner uses `evaluations/policy.yaml`, a fixed synthetic policy independent of
the editable studio policy. The policy is part of the dataset fingerprint so changes
to it are visible when comparing reports.

## Enquiry coverage

The enquiry cases cover multiple supported questions, a recommendation that needs
student details, all three answer statuses in one email, information versus
enrolment requests for new and existing senders, and a class absent from the
fixture. `question_answer_checks` matches checklist question topics by substring
and requires the declared status. When `allow_references` is false, matching
answers must have no references. A missing match fails the check.

Topic matching is lexical and does not guarantee distinct questions or source
relevance. Review the full checklist, requested actions, and draft; a valid
reference does not establish that it supports the answer. The fixture contains
no Wednesday beginner class, clothing rules, or enrolment process. These cases
do not establish real-world studio policy or availability.
