import pytest

from studio_copilot.agent.contracts import (
    ModelError,
    Routing,
    ToolCall,
    ToolTurn,
)

from .helpers import start, turn

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "mode", ["missing", "duplicate", "budget", "excess", "invalid", "empty", "model_error"]
)
def test_information_gathering_always_terminates(rig, scenario, mode):
    client, model, _, _ = rig
    model.routing = Routing(
        intents=["general_enquiry"],
        request_summary="Timetable enquiry",
        needs_clarification=False,
        reason="Optional read-only tools",
    )
    if mode == "missing":
        model.missing = ["Which class date?"]
    elif mode == "duplicate":
        model.turns = lambda n: turn("get_enrolments", {"on_date": "2027-02-08"})
    elif mode == "budget":
        model.turns = lambda n: turn("get_enrolments", {"on_date": f"2027-02-{7 + n:02}"}, str(n))
    elif mode == "excess":

        def excess(n):
            calls = [
                ToolCall(
                    call_id=str(i),
                    name="get_enrolments",
                    arguments={"on_date": f"2027-02-{8 + i:02}"},
                )
                for i in range(5)
            ]
            return ToolTurn(calls=calls, output=[])

        model.turns = excess
    elif mode == "invalid":
        model.turns = lambda n: turn("delete_student", {})
    elif mode == "empty":
        model.turns = lambda n: turn("get_enrolments", {"on_date": "2028-01-01"})
    else:

        def fail(n):
            raise ModelError("Unavailable")

        model.turns = fail
        model.fail_draft = True
    run = start(rig, scenario)
    assert model.query_count <= 4
    assert len(run["evidence"]) <= 12
    assert run["draft_details"]["warnings"]
    if mode == "missing":
        assert model.query_count == 2
        assert run["evidence"][0]["tool"] == "get_enrolments"
    if mode == "duplicate":
        assert len(run["evidence"]) == 1
    if mode == "excess":
        assert len(run["evidence"]) == 3
