# Whole-agent validation

The frozen fictional suite lives in `backend/tests/fixtures/whole_agent_validation_v1/`. Its independently authored manifest hashes all case, business, and document bytes. The runner validates those hashes and the expected 5 smoke, 100 everyday, and 25 high-risk counts before it opens a database or calls a provider. Case contents are reserved for independent review; the runner reports outputs and expectations without automatically claiming semantic correctness.

Run from `backend/` with a dedicated PostgreSQL URL whose database name ends in `_test`. The runner creates and drops a random schema, runs Alembic migrations, activates the fictional documents via authenticated API, then starts each case through the real agent-run API and LangGraph. It uses the configured OpenAI model, embedding provider, document generator, and L6 reranker. It never calls approval or delivery endpoints. It records roster, enrolment, attendance, and teacher-response snapshots around each run.

```sh
uv run python -m whole_agent_evaluation --phase smoke --allow-paid-api \
  --max-requests 100 --max-input-tokens 300000 --max-output-tokens 100000 \
  --output /private/tmp/whole-agent-smoke.json
```

Use `--phase everyday`, `--phase high_risk`, or `--phase all` for the frozen sets; `--case ID` limits diagnosis to one case. Every run requires explicit positive request and token caps, and an unused output path. The JSON report is written before setup and after each case, retaining partial results and incurred usage on failure. `output_sha256` hashes each draft, document evidence, and interpretation for independent judgment. `summary.categories` counts completed and failed cases by category. A completed technical run only shows that an awaiting-review draft was produced without recorded business changes or provider failures; it is not a quality pass. Reviewers should assess route, disposition, facts, omitted conditions, review points, privacy, and handoff against the frozen expectations.
