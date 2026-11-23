"""Graph topology for the enquiry workflow.

Node names and State keys are stable so pending checkpoints survive code refactors.
Step behavior and tool bounds live beside this file; database writes live in persistence/store.py.
"""

import logging
from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from studio_copilot.agent.contracts import State
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.tracing import span
from studio_copilot.agent.workflow.nodes import WorkflowNodes
from studio_copilot.agent.workflow.nodes import select_flow as select_flow

logger = logging.getLogger(__name__)


def _traced(name: str, handler: Callable):
    def execute(state: State):
        logger.info("node_started", extra={"run_id": state["run_id"], "node": name})
        with span(name):
            result = handler(state)
        logger.info("node_completed", extra={"run_id": state["run_id"], "node": name})
        return result

    return execute


class Workflow:
    def __init__(
        self, engine, model, *, store=None, records=None, evidence_review=None, draft_override=None
    ):
        self.nodes = WorkflowNodes(
            store if store is not None else WorkflowStore(engine),
            model,
            records=records,
            evidence_review=evidence_review,
            draft_override=draft_override,
        )

    def compile(self, checkpointer):
        nodes = self.nodes
        builder = StateGraph(State)
        steps = {
            "load": nodes.load,
            "route": nodes.route,
            "interpret": nodes.interpret,
            "interpret_general": nodes.interpret_general,
            "remember_student": nodes.remember_student,
            "gather": nodes.gather,
            "draft": nodes.draft,
            "persist_draft": nodes.persist_draft,
            "review": nodes.review,
            "revision": nodes.revision,
            "approve": nodes.approve,
            "remember_approval": nodes.remember_approval,
        }
        for name, handler in steps.items():
            builder.add_node(name, _traced(name, handler))

        # Route first, then converge both interpretations on the shared memory/review flow.
        builder.add_edge(START, "load")
        builder.add_edge("load", "route")
        builder.add_conditional_edges(
            "route",
            lambda state: state["flow"],
            {
                "makeup": "interpret",
                "enquiry": "interpret_general",
                "teacher_handoff": "interpret_general",
            },
        )
        builder.add_edge("interpret", "remember_student")
        builder.add_edge("interpret_general", "remember_student")
        builder.add_edge("remember_student", "gather")
        builder.add_edge("gather", "draft")
        builder.add_edge("draft", "persist_draft")
        builder.add_edge("persist_draft", "review")

        # Only explicit teacher feedback starts another drafting attempt.
        builder.add_conditional_edges(
            "review",
            lambda state: state["decision"]["action"],
            {"approve": "approve", "revise": "revision"},
        )
        builder.add_edge("revision", "gather")
        builder.add_edge("approve", "remember_approval")
        builder.add_edge("remember_approval", END)
        return builder.compile(checkpointer=checkpointer)
