"""Routing decisions are observable without copying student content to logs."""

import json
import logging
from types import SimpleNamespace

import pytest

from studio_copilot.agent.contracts import Routing
from studio_copilot.agent.telemetry import EventFormatter
from studio_copilot.agent.workflow.nodes import WorkflowNodes


@pytest.mark.parametrize("new_sender", [False, True])
def test_route_emits_safe_classification_metadata(new_sender, monkeypatch):
    routing = Routing(
        intents=["enrolment"],
        action="other_action",
        request_summary="Private email summary",
        needs_clarification=False,
        reason="Private student request details",
    )
    model = SimpleNamespace(route=lambda context: routing)
    saved = []
    store = SimpleNamespace(engine=None, save_routing=lambda *args: saved.append(args))
    nodes = WorkflowNodes(store, model)
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("studio_copilot.agent.workflow.nodes")
    # Alembic's test migration logging configuration disables pre-existing loggers.
    monkeypatch.setattr(logger, "disabled", False)
    handler, previous_level = Capture(), logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        result = nodes.route(
            {
                "run_id": "test-run",
                "context": {
                    "source": {"body": "Private email body"},
                    "student": {"email": "private@example.test"},
                    "intake": {"new_sender": new_sender},
                },
            }
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
    event = json.loads(EventFormatter().format(next(r for r in records if r.msg == "agent_routed")))
    assert event["run_id"] == "test-run"
    assert event["intents"] == ["enrolment"]
    assert event["action"] == "other_action"
    assert event["flow"] == "teacher_handoff"
    assert event["needs_clarification"] is False
    assert saved[0][1] == result["routing"]
    assert "Private" not in json.dumps(event)
    assert "private@example.test" not in json.dumps(event)


def test_formatter_omits_free_text_even_when_supplied_as_extra():
    record = logging.makeLogRecord(
        {
            "msg": "agent_routed",
            "levelname": "INFO",
            "run_id": "test-run",
            "intents": ["makeup", "absence"],
            "flow": "makeup",
            "needs_clarification": True,
            "reason": "private reason",
            "email": "private@example.test",
            "body": "private body",
        }
    )
    event = json.loads(EventFormatter().format(record))
    assert event["intents"] == ["makeup", "absence"]
    assert event["needs_clarification"] is True
    assert {"reason", "email", "body"}.isdisjoint(event)
