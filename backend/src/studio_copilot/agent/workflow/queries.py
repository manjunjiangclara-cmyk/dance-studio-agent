"""Bounded, read-only tool exploration for one drafting attempt."""

import json
import logging
import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import (
    Model,
    ModelContextLimitError,
    ModelError,
    State,
    ToolCall,
)
from studio_copilot.agent.enquiry import context_evidence
from studio_copilot.agent.makeup import gather_makeup
from studio_copilot.agent.question_resolutions import resolution_evidence, resolved_question_context
from studio_copilot.agent.tools import ENQUIRY_TOOLS, TOOL_TYPES, execute_tool

logger = logging.getLogger(__name__)
MAX_ROUNDS = 4
MAX_CALLS = 3


def _feedback_evidence(feedback: str) -> dict:
    return {
        "tool": "teacher_feedback",
        "arguments": {},
        "finding": "Teacher feedback for this revision.",
        "result": {"text": feedback, "references": ["teacher_feedback"]},
    }


def _is_booked_makeup_schedule_question(state: State) -> bool:
    questions = state["interpretation"].get("questions", [])
    if (
        state.get("flow") != "enquiry"
        or state.get("routing", {}).get("intents") != ["makeup"]
        or len(questions) != 1
        or len(state["context"].get("confirmed_bookings", [])) != 1
        or state.get("question_resolutions")
    ):
        return False
    question = questions[0].casefold()
    return bool(
        re.search(r"\b(?:when|date|day|time)\b", question)
        and re.search(
            r"\b(?:booked (?:for )?me|did you book (?:for )?me|"
            r"my (?:makeup )?booking|my booked makeup)\b",
            question,
        )
        and not re.search(r"\b(?:fee|policy|deadline|rule|cancel|reschedule|another)\b", question)
    )


class QueryRunner:
    def __init__(self, engine, model: Model):
        self.engine, self.model = engine, model

    def gather(self, state: State) -> dict:
        if state.get("flow", state["context"].get("flow")) == "makeup":
            try:
                return gather_makeup(self.engine, state)
            except SQLAlchemyError:
                warning = "Studio records could not be verified; teacher clarification is needed."
                return {
                    "evidence": [
                        {
                            "tool": "verify_makeup_request",
                            "arguments": {},
                            "result": {"verified": False, "issues": [warning], "references": []},
                        }
                    ],
                    "warnings": [warning],
                }
        if _is_booked_makeup_schedule_question(state):
            context_snapshot = context_evidence(state["context"])
            context_snapshot["arguments"]["booked_schedule"] = True
            evidence = [context_snapshot]
            if feedback := state.get("feedback", "").strip():
                evidence.append(_feedback_evidence(feedback))
            return {
                "evidence": evidence,
                "warnings": [],
                "document_answers_enabled": False,
            }

        from studio_copilot.documents.online import gather as gather_documents

        document_result = gather_documents(self.engine, state)
        if document_result is not None:
            if state.get("question_resolutions"):
                document_result["evidence"].append(
                    resolution_evidence(state["question_resolutions"])
                )
            return dict(document_result, document_answers_enabled=True)
        context = {
            **state["context"],
            "interpretation": state["interpretation"],
            "teacher_feedback": state.get("feedback", ""),
            "question_resolutions": resolved_question_context(
                state["interpretation"], state.get("question_resolutions", [])
            ),
        }
        warnings = list(state["interpretation"]["missing_details"])
        evidence, transcript, seen = [], [], set()
        with Session(self.engine) as db:
            for round_number in range(1, MAX_ROUNDS + 1):
                try:
                    turn = self.model.choose_tools(context, transcript)
                except ModelContextLimitError:
                    raise
                except ModelError:
                    warnings.append(
                        "Information gathering stopped because the model was unavailable."
                    )
                    break
                if not turn.calls:
                    break
                transcript.extend(turn.output)
                stop = len(turn.calls) > MAX_CALLS
                if stop:
                    warnings.append(
                        "The model exceeded the three-call limit; extra calls were not executed."
                    )
                for call in turn.calls[:MAX_CALLS]:
                    output = self._execute_call(db, context, call, seen)
                    if output is None:
                        warnings.append(
                            "A repeated tool call was blocked; information gathering stopped."
                        )
                        stop = True
                        break
                    evidence.append(
                        {"tool": call.name, "arguments": call.arguments, "result": output}
                    )
                    if output.get("timing_unknown_reason"):
                        warnings.append(output["timing_unknown_reason"])
                    transcript.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps(output, default=str),
                        }
                    )
                    logger.info(
                        "agent_tool",
                        extra={
                            "run_id": state["run_id"],
                            "tool": call.name,
                            "round": round_number,
                        },
                    )
                    if "error" in output:
                        warnings.append(
                            "Requested information unavailable; teacher clarification needed."
                        )
                        stop = True
                        break
                    if output.get("items") == []:
                        warnings.append("This lookup returned no matching records.")
                if stop:
                    break
            else:
                warnings.append("The four-round information gathering limit was reached.")
        evidence.append(context_evidence(context))
        if state.get("question_resolutions"):
            evidence.append(resolution_evidence(state["question_resolutions"]))
        if context["teacher_feedback"].strip():
            evidence.append(_feedback_evidence(context["teacher_feedback"]))
        return {"evidence": evidence, "warnings": warnings, "document_answers_enabled": False}

    @staticmethod
    def _execute_call(db, context: dict, call: ToolCall, seen: set[str]) -> dict | None:
        """Return None for a duplicate, or a safe result/error for an attempted call."""
        try:
            if context.get("flow") == "enquiry" and call.name not in ENQUIRY_TOOLS:
                return {"error": "This tool is not available for enquiries.", "references": []}
            schema = TOOL_TYPES[call.name][0]
            arguments = schema.model_validate(call.arguments).model_dump(mode="json")
            fingerprint = call.name + ":" + json.dumps(arguments, sort_keys=True)
            if fingerprint in seen:
                return None
            seen.add(fingerprint)
            output = execute_tool(
                db,
                UUID(context["student"]["id"]),
                UUID(context["source"]["id"]),
                context["policy"],
                call.name,
                arguments,
            )
            db.rollback()  # Read-only transaction; never commit model tools.
            return output
        except (KeyError, ValueError, ValidationError, SQLAlchemyError):
            db.rollback()
            return {"error": "The requested tool data could not be retrieved.", "references": []}
