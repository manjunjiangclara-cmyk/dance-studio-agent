# Agent package

Start with `service.py` to follow an API request, or `workflow/graph.py` to see the flow.

```text
agent/
  service.py                 Start, inspect, review, retry, and supersede runs
  contracts.py               Shared model outputs, graph state, and adapter protocol
  openai_model.py            Responses API calls and model instructions
  policy.py                  Load and validate the editable policy resource
  tools.py                   Read-only studio tools and their argument schemas
  telemetry.py               Structured logging
  workflow/
    graph.py                 Node registration, edges, and tracing
    nodes.py                 Interpretation, memory, drafting, and review steps
    queries.py               Bounded tool-calling loop
  persistence/
    store.py                 Load context; save memory, drafts, and approved responses
    checkpoints.py           PostgreSQL checkpointer and its setup command
    locking.py               Serialize agent runs and incoming messages per student
```

An API request goes through `service.py`, which runs the graph. Graph nodes call the OpenAI adapter, query tools, and the persistence store. Model calls stay outside database write transactions.

The `workflow` package exports `Workflow` and `select_flow` as its public entry points. The `persistence` package contains agent-specific storage support; studio table definitions stay in `studio_copilot/persistence/models.py`.

Live evaluation scripts belong in `backend/evaluations/`, outside the normal test suite and this runtime package. The editable studio policy stays in `backend/policies/studio.yaml`.
