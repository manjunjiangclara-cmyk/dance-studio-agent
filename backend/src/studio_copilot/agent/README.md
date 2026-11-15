# Agent package

Start with `service.py` to follow an API request, or `workflow/graph.py` to see the flow.

```text
agent/
  service.py                 Start, inspect, review, retry, and supersede runs
  contracts.py               Shared model outputs, graph state, and adapter protocol
  openai_model.py            Responses API calls and model instructions
  privacy.py                 Local identity placeholders and output restoration
  policy.py                  Load and validate the editable policy resource
  tools.py                   Read-only studio tools and their argument schemas
  makeup.py                  Mandatory source verification, candidate checks, approval revalidation
  enquiry.py                 Retained context evidence and question/citation validation
  telemetry.py               Structured logging
  tracing.py                 Optional content-free LangSmith spans
  workflow/
    graph.py                 Node registration, edges, and tracing
    nodes.py                 Interpretation, memory, drafting, and review steps
    queries.py               Deterministic makeup dispatch; bounded enquiry/handoff tools
  persistence/
    store.py                 Load context; save memory, drafts, and approved responses
    checkpoints.py           PostgreSQL checkpointer and its setup command
    locking.py               Serialize agent runs and incoming messages per student
```

An API request goes through `service.py`, which runs the graph. Graph nodes call the OpenAI adapter, query tools, and the persistence store. Model calls stay outside database write transactions.

For makeup, `gather` runs fixed code checks: date-specific enrolment, dated-session
membership, and a source-linked absence notice, followed by replacement search and
capacity/duplicate validation. The model cannot skip these steps. General enquiries
retain optional model-selected read-only tools. Approval revalidates the source and
candidate under locks; stale or unverified legacy proposals require a new draft.

The `workflow` package exports `Workflow` and `select_flow` as its public entry points. The `persistence` package contains agent-specific storage support; studio table definitions stay in `studio_copilot/persistence/models.py`.

Live evaluation scripts belong in `backend/evaluations/`, outside the normal test suite and this runtime package. The editable studio policy stays in `backend/policies/studio.yaml`.

### Optional LangSmith tracing

Set `STUDIO_LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in the backend's
ignored environment file or shell to export operational traces. Optionally set
`LANGSMITH_PROJECT` (default `studio-copilot`). Restart the backend after changing
its environment. Tracing is off by default; a missing key leaves it disabled.

#### What is tracked

Each graph execution produces an `agent_workflow` trace with nested spans. Initial
processing, approval review, revision, and retry are separate traces linked by the
same application `run_id`. The root metadata includes that UUID and a `phase` of
`start`, `review`, `revision`, or `retry`. Rejecting a draft does not invoke the
graph and therefore does not create one of these traces.

| Span | Recorded details |
| --- | --- |
| Workflow and graph nodes | Span name, parent relationship, start/end times, and `status`: `success`, `failure`, or `paused` for a review interrupt. |
| Model calls | The above, plus the configured model name and input/output token counts when the provider returns usage. |
| Read-only tool calls | The above, plus the tool name for `get_timetable`, `get_enrolments`, `search_sessions`, `get_locations`, or `check_absence_notice`. |

Model spans also export LangSmith usage metadata and provider/model identifiers for estimated
token-based costs, including cached input and reasoning tokens when available. LangSmith
requires a matching model price; missing usage or pricing is not zero spend. Estimates may
differ from provider billing and do not backfill earlier traces. Check the model span and
workflow trace for usage and cost, and use the OpenAI usage dashboard for billed spending.

Failed spans use the generic error `operation_failed`; they do not include the
exception text. Timing comes from the span's start and end timestamps. Fields are
allowlisted and may be absent if unavailable or if tracing fails. The run ID is a
linkable identifier, so protect project access and configure retention in LangSmith.

Graph state, emails, conversation history, student details, prompts, model responses,
tool arguments and results, teacher feedback, and provider reasoning are not exported.
The traces do not include evaluation scores or detailed explanations of decisions.
Automatic LangGraph tracing is suppressed within the workflow even when
`LANGSMITH_TRACING=true`. Trace export failures do not stop the agent.

To check a live installation, enable tracing, run a synthetic enquiry, and inspect
its project in LangSmith for the workflow and child spans. Verify that no message
content appears. This smoke test needs a configured LangSmith account and key.
