"""Workflow steps: model decisions and state updates, with persistence delegated to the store."""

import logging
from datetime import datetime

from langgraph.types import interrupt
from pydantic import ValidationError

from studio_copilot.administration.service import conflict
from studio_copilot.agent.contracts import (
    Draft,
    EnquiryInterpretation,
    MakeupInterpretation,
    Model,
    ModelError,
    Review,
    Routing,
    State,
)
from studio_copilot.agent.document_answers import document_draft
from studio_copilot.agent.enquiry import safe_body, validate_answers
from studio_copilot.agent.makeup import clarification_body, validated_candidate_ids
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.proposals import confirmation_body
from studio_copilot.agent.question_resolutions import (
    RevisionExtractionError,
    identify_questions,
    merge_resolutions,
    resolved_question_context,
    validate_resolution_update,
)
from studio_copilot.agent.workflow.queries import QueryRunner

logger = logging.getLogger(__name__)


def select_flow(routing: Routing) -> str:
    """Business actions select the workflow; topic labels alone never authorize a booking."""
    intents = set(routing.intents)
    if routing.action == "information_only":
        return "enquiry"
    if (
        routing.action == "makeup_booking"
        and "makeup" in intents
        and intents <= {"makeup", "absence"}
    ):
        return "makeup"
    return "teacher_handoff"


def _fallback_draft(state: State) -> Draft:
    if state.get("flow", "makeup") != "makeup":
        return Draft(
            body="Thanks for your message. I'll review your enquiry and get back to you.",
            rationale=state["routing"]["reason"] + " The model was unavailable.",
            questions=state["warnings"],
            references=[],
        )
    return Draft(
        body=(
            "Thank you for your message. Could you confirm the class date you will miss "
            "and your preferred makeup dates and location? "
            "I'll check the options for you."
        ),
        rationale="The model was unavailable. This template makes no eligibility promises.",
        questions=state["warnings"],
        references=[],
    )


def _validate_references(draft: Draft, state: State) -> Draft:
    references = {"policy:" + state["context"]["policy"]["version"]}
    for item in state["evidence"]:
        references.update(item["result"].get("references", []))
    if state.get("feedback", "").strip():
        references.add("teacher_feedback")
    if any(reference not in references for reference in draft.references):
        draft.references = [reference for reference in draft.references if reference in references]
        draft.rationale += " Unsupported model references were removed; verify the draft's claims."
    return draft


def _validate_booking_proposal(draft: Draft, state: State) -> Draft:
    if any(
        item.get("tool") == "validate_makeup_candidates"
        and item.get("result", {}).get("options_requested")
        for item in state.get("evidence", [])
    ):
        draft.booking_session_id = None
    if draft.booking_session_id is None:
        if state.get("flow", state.get("context", {}).get("flow")) == "makeup":
            draft.body = clarification_body(state.get("evidence", []))
        return draft
    if state.get(
        "flow", state.get("context", {}).get("flow")
    ) != "makeup" or draft.booking_session_id not in validated_candidate_ids(
        state.get("evidence", [])
    ):
        draft.booking_session_id = None
        draft.body = (
            clarification_body(state.get("evidence", []))
            if state.get("flow", state.get("context", {}).get("flow")) == "makeup"
            else safe_body(
                draft.answers,
                state.get("interpretation", {}).get("requested_actions", []),
                draft.question_resolutions,
            )
        )
        draft.rationale += " Unsupported booking proposal removed; teacher clarification is needed."
    else:
        candidates = [
            item
            for evidence in state.get("evidence", [])
            if evidence.get("tool") == "search_sessions"
            for item in evidence.get("result", {}).get("items", [])
            if item.get("id") == str(draft.booking_session_id)
        ]
        item = candidates[-1] if candidates else {}
        try:
            start = datetime.fromisoformat(item["starts_at"])
            draft.body = confirmation_body(item["class_name"], item["location_name"], start)
        except (KeyError, TypeError, ValueError):
            draft.booking_session_id = None
            draft.body = "We need to verify the session details before arranging your makeup."
            return draft
    return draft


class WorkflowNodes:
    def __init__(self, store: WorkflowStore, model: Model):
        self.store, self.model = store, model
        self.queries = QueryRunner(store.engine, model)

    def load(self, state: State) -> dict:
        return {"attempt": 1, "feedback": "", "context": self.store.load_context(state["run_id"])}

    def route(self, state: State) -> dict:
        try:
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
        logger.info(
            "agent_routed",
            extra={
                "run_id": state["run_id"],
                "intents": routing.intents,
                "flow": flow,
                "needs_clarification": routing.needs_clarification,
                "action": routing.action,
            },
        )
        return {
            "routing": result,
            "flow": flow,
            "context": {**state["context"], "routing": result, "flow": flow},
        }

    def interpret(self, state: State) -> dict:
        """Makeup-specific extraction, reached only after routing."""
        return {
            "interpretation": self.model.interpret_makeup(state["context"]).model_dump(mode="json")
        }

    def _enquiry_interpretation(self, state: State, feedback: str = "") -> EnquiryInterpretation:
        try:
            parsed = self.model.interpret_enquiry(
                {
                    **state["context"],
                    "previous_interpretation": state.get("interpretation", {}),
                    "teacher_feedback": feedback,
                }
            )
        except (ModelError, ValidationError) as error:
            if state.get("interpretation"):
                raise RevisionExtractionError(
                    "The revised enquiry could not be interpreted."
                ) from error
            parsed = EnquiryInterpretation(
                request_summary=state["routing"]["request_summary"],
                missing_details=["The enquiry could not be interpreted; teacher review is needed."],
                enduring_preferences=[],
                questions=[state["context"]["source"]["body"][:2000]],
                requested_actions=(
                    [state["routing"]["request_summary"]]
                    if state["routing"].get("action", "unclear") != "information_only"
                    else []
                ),
            )
        if not parsed.requested_actions and state["routing"].get("action") in {
            "other_action",
            "unclear",
        }:
            parsed.requested_actions = [state["routing"]["request_summary"]]
        return parsed

    def interpret_general(self, state: State) -> dict:
        parsed = self._enquiry_interpretation(state)
        identify_questions(parsed, state["run_id"], {})
        return {"interpretation": parsed.model_dump(mode="json")}

    def remember_student(self, state: State) -> dict:
        flow = state.get("flow", "makeup")
        schema = MakeupInterpretation if flow == "makeup" else EnquiryInterpretation
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
            "question_resolutions": resolved_question_context(
                state["interpretation"], state.get("question_resolutions", [])
            ),
        }
        try:
            draft = document_draft(state)
            if draft is None:
                draft = self.model.draft(context)
        except ModelError:
            draft = _fallback_draft(state)
        draft = _validate_booking_proposal(
            _validate_references(validate_answers(draft, state), state), state
        )
        return {"draft": draft.model_dump(mode="json")}

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
        return {"decision": review.model_dump(mode="json")}

    def revision(self, state: State) -> dict:
        feedback = state["decision"].get("feedback") or ""
        if state.get("flow") != "makeup" and state.get("feedback"):
            feedback = (
                state["feedback"]
                + "\n\nLatest teacher feedback (supersedes conflicting earlier feedback):\n"
                + feedback
            )
        update = {"attempt": state["attempt"] + 1, "feedback": feedback}
        if state.get("flow") == "makeup":
            # Refresh extracted preferences/provenance before the fixed checks. This also
            # lets a legacy checkpoint acquire the newly required absence references.
            interpretation = self.model.interpret_makeup(
                {
                    **state["context"],
                    "previous_interpretation": state["interpretation"],
                    "teacher_feedback": feedback,
                }
            )
            self.store.save_revision_interpretation(state["run_id"], interpretation)
            update["interpretation"] = interpretation.model_dump(mode="json")
        else:
            decisions = state["decision"].get("question_resolutions", [])
            validate_resolution_update(state["interpretation"], state["draft"], decisions)
            update["question_resolutions"] = merge_resolutions(
                state.get("question_resolutions", state["draft"].get("question_resolutions", [])),
                decisions,
            )
            interpretation = self._enquiry_interpretation(state, feedback)
            identify_questions(interpretation, state["run_id"], state["interpretation"])
            self.store.save_revision_interpretation(state["run_id"], interpretation)
            update["interpretation"] = interpretation.model_dump(mode="json")
        return update

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
                "confirmed_booking": self.store.approved_booking(state["run_id"]),
            }
        )
        self.store.remember_approval(state["run_id"], memory)
        logger.info("approved_memory_updated", extra={"run_id": state["run_id"]})
        return {}
