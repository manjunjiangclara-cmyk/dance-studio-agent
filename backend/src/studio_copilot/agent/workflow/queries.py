"""Bounded, read-only tool exploration for one drafting attempt."""

import json
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import Model, ModelError, State, ToolCall
from studio_copilot.agent.enquiry import context_evidence
from studio_copilot.agent.makeup import gather_makeup
from studio_copilot.agent.question_resolutions import resolution_evidence
from studio_copilot.agent.tools import ENQUIRY_TOOLS, TOOL_TYPES, execute_tool

logger = logging.getLogger(__name__)
MAX_ROUNDS = 4
MAX_CALLS = 3


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
        context = {
            **state["context"],
            "interpretation": state["interpretation"],
            "teacher_feedback": state.get("feedback", ""),
            "question_resolutions": state.get("question_resolutions", []),
        }
        warnings = list(state["interpretation"]["missing_details"])
        evidence, transcript, seen = [], [], set()
        with Session(self.engine) as db:
            for round_number in range(1, MAX_ROUNDS + 1):
                try:
                    turn = self.model.choose_tools(context, transcript)
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
            evidence.append(
                {
                    "tool": "teacher_feedback",
                    "arguments": {},
                    "finding": "Teacher feedback for this revision.",
                    "result": {
                        "text": context["teacher_feedback"],
                        "references": ["teacher_feedback"],
                    },
                }
            )
        return {"evidence": evidence, "warnings": warnings}

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
