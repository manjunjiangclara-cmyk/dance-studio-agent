"""Strict content-free events. Export failures never interrupt document work."""

import json
import logging
import math
import os
from pathlib import Path
from threading import Lock
from uuid import UUID

logger = logging.getLogger(__name__)
OPERATIONS = {"ingestion", "embedding", "retrieval", "reranking", "generation"}
STAGES = {"operation", "api", "cache", "budget", "context"}
STATUSES = {"success", "failure", "degraded"}
COUNTS = {
    "attempts",
    "input_tokens",
    "output_tokens",
    "unknown_usage_calls",
    "retries",
    "cache_hits",
    "cache_misses",
    "cache_waits",
    "candidates",
    "evidence_tokens",
    "truncations",
    "items",
}
ERRORS = {
    "budget_exceeded",
    "provider_error",
    "invalid_vectors",
    "invalid_input",
    "source_missing",
    "source_incomplete",
    "permission_denied",
    "rate_limited",
    "operation_failed",
}


def safe_event(value):
    try:
        operation_id = str(UUID(str(value["operation_id"])))
        if (
            value["operation"] not in OPERATIONS
            or value["stage"] not in STAGES
            or value["status"] not in STATUSES
        ):
            return None
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    event = dict(
        version="document-operations-v1",
        operation_id=operation_id,
        operation=value["operation"],
        stage=value["stage"],
        status=value["status"],
    )
    for field in COUNTS:
        v = value.get(field)
        if type(v) is int and v >= 0:
            event[field] = v
    seconds = value.get("seconds")
    if type(seconds) in (float, int) and math.isfinite(seconds) and seconds >= 0:
        event["seconds"] = seconds
    if isinstance(value.get("error_code"), str) and value["error_code"] in ERRORS:
        event["error_code"] = value["error_code"]
    return event


def langsmith_export(event):
    if os.environ.get("STUDIO_LANGSMITH_TRACING", "").lower() != "true":
        return
    if not os.environ.get("LANGSMITH_API_KEY", "").strip():
        return
    from langsmith.run_trees import RunTree

    run = RunTree(
        name="documents_" + event["operation"] + "_" + event["stage"],
        run_type="chain",
        inputs={},
        project_name=os.environ.get("LANGSMITH_PROJECT") or "studio-copilot",
        extra={"metadata": event},
    )
    run.post()
    run.end(outputs={}, error="operation_failed" if event["status"] == "failure" else None)
    run.patch()


class EventSink:
    def __init__(self, events_file=None, exporter=None):
        self.lock = Lock()
        self.exporter = exporter if exporter is not None else langsmith_export
        self.stream = None
        if events_file is not None:
            try:
                fd = os.open(Path(events_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                self.stream = os.fdopen(fd, "w", encoding="utf-8")
            except OSError:
                try:
                    logger.warning("operations_export_failed")
                except Exception:
                    pass

    def emit(self, operation_id, operation, stage, status="success", **fields):
        event = safe_event(
            dict(fields, operation_id=operation_id, operation=operation, stage=stage, status=status)
        )
        if event is None:
            return
        # Even a misconfigured logging handler must not change business outcomes.
        try:
            logger.info(json.dumps(event, separators=(",", ":")))
        except Exception:
            pass
        try:
            with self.lock:
                if self.stream is not None:
                    self.stream.write(json.dumps(event) + "\n")
                    self.stream.flush()
            self.exporter(dict(event))
        except Exception:
            try:
                logger.warning("operations_export_failed")
            except Exception:
                pass

    def close(self):
        try:
            if self.stream:
                self.stream.close()
        except Exception:
            pass


class _SafeSDKLogs(logging.Filter):
    """LangSmith's asynchronous transport logs outside the exporter try/except."""

    def filter(self, record):
        standard = logging.LogRecord("trace", logging.WARNING, "", 0, "", (), None).__dict__
        for key in list(record.__dict__):
            if key not in standard:
                del record.__dict__[key]
        record.msg = "trace_sdk_event"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


_sdk_filter = _SafeSDKLogs()
for _name in (
    "langsmith.client",
    "langsmith.async_client",
    "langsmith._base_client",
    "langsmith._response",
    "langsmith.run_trees",
    "langsmith.run_helpers",
    "langsmith.utils",
    "langsmith._internal._background_thread",
):
    logging.getLogger(_name).addFilter(_sdk_filter)
