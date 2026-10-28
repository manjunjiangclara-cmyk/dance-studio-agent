"""Explicit, content-free LangSmith spans for the agent runtime."""

import logging
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from langgraph.errors import GraphInterrupt
from langsmith import tracing_context
from langsmith.run_trees import RunTree

logger = logging.getLogger(__name__)
_current = ContextVar("studio_trace", default=None)
_FIELDS = {"run_id", "phase", "model", "input_tokens", "output_tokens", "tool", "status"}
_PHASES = {"start", "review", "revision", "retry"}
_TOOLS = {
    "get_timetable",
    "get_enrolments",
    "search_sessions",
    "get_locations",
    "check_absence_notice",
}


def _safe(fields):
    result = {}
    for key, value in fields.items():
        if key not in _FIELDS:
            continue
        if key == "run_id":
            try:
                result[key] = str(UUID(str(value)))
            except (ValueError, TypeError, AttributeError):
                pass
        elif key == "phase" and value in _PHASES:
            result[key] = value
        elif key == "tool" and value in _TOOLS:
            result[key] = value
        elif key == "status" and value in {"success", "failure", "paused"}:
            result[key] = value
        elif key in {"input_tokens", "output_tokens"} and type(value) is int and value >= 0:
            result[key] = value
        elif (
            key == "model"
            and isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,100}", value)
        ):
            result[key] = value
    return result


class _Handle:
    def __init__(self, run=None):
        self.run = run
        self.fields = {}

    def update(self, **fields):
        self.fields.update(_safe(fields))

    def fail(self, error_type=None):
        self.fields["status"] = "failure"


@contextmanager
def span(name, *, kind="chain", metadata=None):
    parent = _current.get()
    run = None
    if parent is not None:
        try:
            run = parent.create_child(
                name=name, run_type=kind, inputs={}, extra={"metadata": _safe(metadata or {})}
            )
            run.post()
        except Exception:
            logger.warning("trace_export_failed")
            run = None
    handle = _Handle(run)
    token = _current.set(run)
    try:
        yield handle
    except GraphInterrupt:
        handle.update(status="paused")
        raise
    except BaseException:
        handle.fail()
        raise
    finally:
        _current.reset(token)
        if run is not None:
            try:
                handle.fields.setdefault("status", "success")
                run.end(
                    outputs={},
                    error="operation_failed" if handle.fields["status"] == "failure" else None,
                    metadata=handle.fields,
                )
                run.patch()
            except Exception:
                logger.warning("trace_export_failed")


@contextmanager
def workflow_trace(run_id, phase):
    # Never permit LangGraph's automatic callbacks to export graph inputs or state.
    with tracing_context(enabled=False, parent=False):
        root = None
        enabled = os.environ.get("STUDIO_LANGSMITH_TRACING", "").lower() == "true"
        key = os.environ.get("LANGSMITH_API_KEY", "").strip()
        if enabled and key:
            try:
                root = RunTree(
                    name="agent_workflow",
                    run_type="chain",
                    inputs={},
                    project_name=os.environ.get("LANGSMITH_PROJECT") or "studio-copilot",
                    extra={"metadata": _safe({"run_id": run_id, "phase": phase})},
                )
                root.post()
            except Exception:
                logger.warning("trace_export_failed")
                root = None
        elif enabled:
            logger.warning("trace_configuration_incomplete")
        handle = _Handle(root)
        token = _current.set(root)
        try:
            yield handle
        except BaseException:
            handle.fail()
            raise
        finally:
            _current.reset(token)
            if root is not None:
                try:
                    handle.fields.setdefault("status", "success")
                    root.end(
                        outputs={},
                        error="operation_failed" if handle.fields["status"] == "failure" else None,
                        metadata=handle.fields,
                    )
                    root.patch()
                except Exception:
                    logger.warning("trace_export_failed")
