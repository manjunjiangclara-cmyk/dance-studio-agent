"""Tracing exports only explicit operational fields, even when auto tracing is enabled."""

import json
from types import SimpleNamespace
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from langsmith import get_tracing_context

from studio_copilot.agent import tools as agent_tools
from studio_copilot.agent import tracing
from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.workflow.graph import _traced

RUN_ID = "abf8de4c-2282-42ed-a498-b284a97d91b6"
SECRET = "PRIVATE student email feedback prompt response result exception"


class FakeRun:
    instances = []
    fail_at = None

    def __init__(self, **kwargs):
        self.events = [("create", kwargs)]
        self.children = []
        self.instances.append(self)
        self._fail("create")

    def _fail(self, operation):
        if self.fail_at == operation:
            raise RuntimeError(SECRET)

    def post(self):
        self._fail("post")
        self.events.append(("post", {}))

    def create_child(self, **kwargs):
        self._fail("child")
        child = FakeRun(**kwargs)
        self.children.append(child)
        return child

    def end(self, **kwargs):
        self._fail("end")
        self.events.append(("end", kwargs))

    def patch(self):
        self._fail("patch")
        self.events.append(("patch", {}))


@pytest.fixture
def tracing_env(monkeypatch):
    FakeRun.instances = []
    FakeRun.fail_at = None
    monkeypatch.setattr(tracing, "RunTree", FakeRun)
    monkeypatch.setenv("STUDIO_LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    return FakeRun


@pytest.mark.parametrize("phase", ["start", "review", "revision", "retry"])
def test_safe_span_hierarchy_and_correlation(tracing_env, phase):
    with tracing.workflow_trace(RUN_ID, phase):
        assert get_tracing_context()["enabled"] is False
        with tracing.span("route", metadata={"body": SECRET}) as node:
            node.update(status="success", feedback=SECRET)
            with tracing.span("model_call", kind="llm") as model:
                model.update(model="test-model", input_tokens=10, output_tokens=5, response=SECRET)
            with tracing.span("tool", kind="tool", metadata={"tool": "get_enrolments"}) as tool:
                tool.update(arguments=SECRET, result=SECRET)

    root = tracing_env.instances[0]
    assert root.events[0][1]["extra"]["metadata"] == {"run_id": RUN_ID, "phase": phase}
    assert root.events[0][1]["project_name"] == "test-project"
    node = root.children[0]
    assert [child.events[0][1]["name"] for child in node.children] == ["model_call", "tool"]
    assert node.children[0].events[-2][1]["metadata"] == {
        "model": "test-model",
        "input_tokens": 10,
        "output_tokens": 5,
        "status": "success",
    }
    assert node.children[1].events[0][1]["extra"]["metadata"] == {"tool": "get_enrolments"}
    assert SECRET not in json.dumps([run.events for run in tracing_env.instances])
    assert all(run.events[-1][0] == "patch" for run in tracing_env.instances)


def test_failure_exports_generic_status_and_never_exception_text(tracing_env):
    with pytest.raises(ValueError, match="PRIVATE"):
        with tracing.workflow_trace(RUN_ID, "start"):
            with tracing.span("route"):
                raise ValueError(SECRET)
    for run in tracing_env.instances:
        end = run.events[-2][1]
        assert end["error"] == "operation_failed"
        assert end["metadata"]["status"] == "failure"
    assert SECRET not in json.dumps([run.events for run in tracing_env.instances])


@pytest.mark.parametrize("operation", ["create", "post", "child", "end", "patch"])
def test_export_failure_does_not_interrupt_workflow_or_log_exception(
    tracing_env, operation, caplog
):
    tracing_env.fail_at = operation
    with tracing.workflow_trace(RUN_ID, "start"):
        with tracing.span("route"):
            result = 42
    assert result == 42
    assert "trace_export_failed" in caplog.text
    assert SECRET not in caplog.text


def test_disabled_and_missing_key_do_not_export(monkeypatch, tracing_env):
    monkeypatch.delenv("STUDIO_LANGSMITH_TRACING")
    with tracing.workflow_trace(RUN_ID, "start"):
        assert get_tracing_context()["enabled"] is False
        with tracing.span("route"):
            pass
    monkeypatch.setenv("STUDIO_LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY")
    with tracing.workflow_trace(RUN_ID, "start"):
        pass
    assert not tracing_env.instances


def test_graph_workers_inherit_parent_and_disable_automatic_tracing(tracing_env):
    class State(TypedDict):
        secret: str

    def node(state):
        assert get_tracing_context()["enabled"] is False
        with tracing.span("route"):
            return {"secret": state["secret"]}

    builder = StateGraph(State)
    builder.add_node("route", node)
    builder.add_edge(START, "route")
    builder.add_edge("route", END)
    with tracing.workflow_trace(RUN_ID, "start"):
        assert builder.compile().invoke({"secret": SECRET}) == {"secret": SECRET}
    assert len(tracing_env.instances[0].children) == 1
    assert SECRET not in json.dumps([run.events for run in tracing_env.instances])


def test_review_interrupt_is_a_normal_pause(tracing_env):
    class State(TypedDict):
        secret: str

    def review(state):
        with tracing.span("review"):
            interrupt(state["secret"])
        return state

    builder = StateGraph(State)
    builder.add_node("review", review)
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    with tracing.workflow_trace(RUN_ID, "start"):
        builder.compile().invoke({"secret": SECRET})
    review_span = tracing_env.instances[0].children[0]
    assert review_span.events[-2][1]["error"] is None
    assert review_span.events[-2][1]["metadata"]["status"] == "paused"
    assert SECRET not in json.dumps([run.events for run in tracing_env.instances])


def test_real_instrumentation_does_not_export_workflow_contents(tracing_env, monkeypatch):
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=12, output_tokens=7), output=SECRET, status="completed"
    )
    model = OpenAIModel(client=object(), model="test-model")
    monkeypatch.setattr(agent_tools, "_execute_tool", lambda *args, **kwargs: {"content": SECRET})

    def handler(state):
        assert model._request(lambda **kwargs: response, input=state["body"]) is response
        assert agent_tools.execute_tool(None, None, None, {}, "get_enrolments", {"body": SECRET})
        return {"output": SECRET}

    with tracing.workflow_trace(RUN_ID, "review"):
        assert _traced("route", handler)({"run_id": RUN_ID, "body": SECRET}) == {"output": SECRET}

    node = tracing_env.instances[0].children[0]
    model_run, tool_run = node.children
    assert model_run.events[0][1]["extra"]["metadata"]["model"] == "test-model"
    assert model_run.events[-2][1]["metadata"]["input_tokens"] == 12
    assert model_run.events[-2][1]["metadata"]["output_tokens"] == 7
    assert tool_run.events[0][1]["extra"]["metadata"]["tool"] == "get_enrolments"
    assert SECRET not in json.dumps([run.events for run in tracing_env.instances])
