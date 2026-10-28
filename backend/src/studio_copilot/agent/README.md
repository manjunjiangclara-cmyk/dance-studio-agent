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
  telemetry.py               Structured logging
  tracing.py                 Optional content-free LangSmith spans
  workflow/
    graph.py                 Node registration, edges, and tracing
    nodes.py                 Interpretation, memory, drafting, and review steps
    queries.py               Deterministic makeup dispatch; bounded optional handoff tools
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

Each workflow execution is correlated by its agent run ID, including review,
revision, and retry. Spans cover workflow nodes, model calls, and read-only tools;
they include timing, status, configured model, token counts, and known tool names
when available. They omit graph state, student messages, model content, tool
arguments and results, teacher feedback, and exception messages. The run ID is
still a linkable identifier; protect access and configure retention in LangSmith.
Automatic LangGraph tracing is suppressed within the workflow even when
`LANGSMITH_TRACING=true`. Trace export failures do not stop the agent.

To check a live installation, enable tracing, run a synthetic enquiry, and inspect
its project in LangSmith for the workflow and child spans. Verify that no message
content appears. This smoke test needs a configured LangSmith account and key.
