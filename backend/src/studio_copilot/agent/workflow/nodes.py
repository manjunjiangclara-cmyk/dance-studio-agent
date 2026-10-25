"""Workflow steps: model decisions and state updates, with persistence delegated to the store."""

import logging

from langgraph.types import interrupt

from studio_copilot.administration.service import conflict
from studio_copilot.agent.contracts import (
    Draft,
    MakeupInterpretation,
    Model,
    ModelError,
    RequestInterpretation,
    Review,
    Routing,
    State,
)
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.workflow.queries import QueryRunner

logger = logging.getLogger(__name__)


def select_flow(routing: Routing) -> str:
    """Only the implemented makeup+absence combination may enter the makeup flow."""
    intents = set(routing.intents)
    if not routing.needs_clarification and "makeup" in intents and intents <= {"makeup", "absence"}:
        return "makeup"
    return "teacher_handoff"


def _fallback_draft(state: State) -> Draft:
    if state.get("flow", "makeup") != "makeup":
        return Draft(
            body="Thank you for your message. Your teacher will review your enquiry.",
            rationale=state["routing"]["reason"] + " " + state["warnings"][0],
            questions=state["warnings"],
            references=[],
        )
    return Draft(
        body=(
            "Thank you for your message. Could you confirm the class date you will miss "
            "and your preferred makeup dates and location? "
            "Your teacher will review the options."
        ),
        rationale="The model was unavailable. This template makes no eligibility promises.",
        questions=state["warnings"],
        references=[],
    )


def _validate_references(draft: Draft, state: State) -> Draft:
    references = {"policy:" + state["context"]["policy"]["version"]}
    for item in state["evidence"]:
        references.update(item["result"].get("references", []))
    if any(reference not in references for reference in draft.references):
        draft.references = [reference for reference in draft.references if reference in references]
        draft.rationale += " Unsupported model references were removed; verify the draft's claims."
    return draft


class WorkflowNodes:
    def __init__(self, store: WorkflowStore, model: Model):
        self.store, self.model = store, model
        self.queries = QueryRunner(store.engine, model)

    def load(self, state: State) -> dict:
        return {"attempt": 1, "feedback": "", "context": self.store.load_context(state["run_id"])}

    def route(self, state: State) -> dict:
        try:
            if state["context"].get("intake", {}).get("new_sender"):
                routing = Routing(
                    intents=["new_student_enquiry"],
                    request_summary="First email from a new enquirer; teacher assessment required.",
                    needs_clarification=False,
                    reason="The sender had no student profile when this email was received.",
                )
            else:
                routing = self.model.route(state["context"])
        except ModelError:
            routing = Routing(
                intents=["unknown"],
                request_summary="Student enquiry needs teacher assessment.",
                needs_clarification=True,
                reason="The routing model was unavailable.",
            )
        flow, result = select_flow(routing), routing.model_dump()
        self.store.save_routing(state["run_id"], result, flow)
        return {
            "routing": result,
            "flow": flow,
            "context": {**state["context"], "routing": result, "flow": flow},
        }

    def interpret(self, state: State) -> dict:
        """Makeup-specific extraction, reached only after routing."""
        return {"interpretation": self.model.interpret_makeup(state["context"]).model_dump()}

    def interpret_general(self, state: State) -> dict:
        routing = state["routing"]
        explanation = (
            "The request type needs clarification by the teacher."
            if routing["needs_clarification"]
            else "This workflow is not implemented; teacher handling is required."
        )
        parsed = RequestInterpretation(
            request_summary=routing["request_summary"],
            missing_details=[explanation],
            enduring_preferences=[],
        )
        return {"interpretation": parsed.model_dump()}

    def remember_student(self, state: State) -> dict:
        flow = state.get("flow", "makeup")
        schema = MakeupInterpretation if flow == "makeup" else RequestInterpretation
        interpretation = schema.model_validate(state["interpretation"])
        self.store.remember_student(state["run_id"], interpretation, state.get("routing", {}), flow)
        logger.info("student_memory_updated", extra={"run_id": state["run_id"]})
        return {}

    def gather(self, state: State) -> dict:
        return self.queries.gather(state)

    def draft(self, state: State) -> dict:
        context = {
            **state["context"],
            "interpretation": state["interpretation"],
            "evidence": state["evidence"],
            "warnings": state["warnings"],
            "teacher_feedback": state.get("feedback", ""),
        }
        try:
            draft = self.model.draft(context)
        except ModelError:
            draft = _fallback_draft(state)
        return {"draft": _validate_references(draft, state).model_dump()}

    def persist_draft(self, state: State) -> dict:
        self.store.save_draft(
            state["run_id"], state["attempt"], state["draft"], state["evidence"], state["warnings"]
        )
        return {}

    def review(self, state: State) -> dict:
        # LangGraph restarts this node on resume: no persistence before the interrupt.
        decision = interrupt(
            {"run_id": state["run_id"], "revision": state["attempt"], "draft": state["draft"]}
        )
        review = Review.model_validate(decision)
        if (
            review.action not in {"approve", "revise"}
            or review.expected_revision != state["attempt"]
        ):
            conflict("Review does not match this draft revision.")
        return {"decision": review.model_dump()}

    def revision(self, state: State) -> dict:
        return {"attempt": state["attempt"] + 1, "feedback": state["decision"]["feedback"]}

    def approve(self, state: State) -> dict:
        response_id = self.store.approve(state["run_id"], state["decision"].get("body"))
        return {"response_id": response_id}

    def remember_approval(self, state: State) -> dict:
        body = self.store.approved_response(state["run_id"])
        memory = self.model.reconcile(
            {
                **state["context"],
                "interpretation": state["interpretation"],
                "teacher_response": {
                    "id": state["response_id"],
                    "body": body,
                    "delivery": "unconfirmed",
                },
            }
        )
        self.store.remember_approval(state["run_id"], memory)
        logger.info("approved_memory_updated", extra={"run_id": state["run_id"]})
        return {}
