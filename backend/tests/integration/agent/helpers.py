from studio_copilot.agent.contracts import (
    Draft,
    MakeupInterpretation,
    ModelError,
    Preference,
    ReviewedMemory,
    Routing,
    ToolCall,
    ToolTurn,
)


class FakeModel:
    def __init__(self):
        self.contexts = []
        self.query_count = 0
        self.turns = None
        self.fail_interpret = False
        self.fail_draft = False
        self.fail_reconcile = False
        self.missing = []
        self.before_query = None
        self.routing = None
        self.routing_contexts = []
        self.fail_route = False

    def route(self, context):
        self.routing_contexts.append(context)
        if self.fail_route:
            raise ModelError("Unavailable")
        return self.routing or Routing(
            intents=["makeup", "absence"],
            request_summary="Student asks about a makeup class.",
            needs_clarification=False,
            reason="A makeup enquiry related to an absence.",
        )

    def interpret_makeup(self, context):
        self.contexts.append(context)
        if self.fail_interpret:
            raise ModelError("Unavailable")
        saturday = "Saturday" in context["source"]["body"]
        return MakeupInterpretation(
            request_summary="Makeup on " + ("Saturday" if saturday else "Thursday"),
            absence_date="2027-02-08",
            preferred_date="2027-02-13" if saturday else "2027-02-11",
            preferred_weekday="Saturday" if saturday else "Thursday",
            location_preference=None,
            missing_details=self.missing,
            enduring_preferences=[],
        )

    def choose_tools(self, context, transcript):
        if self.before_query:
            self.before_query(context)
        self.query_count += 1
        if self.turns:
            return self.turns(self.query_count)
        if transcript:
            return ToolTurn(calls=[], output=[])
        return turn("get_enrolments", {"on_date": "2027-02-08"}, "enrolments")

    def draft(self, context):
        if self.fail_draft:
            raise ModelError("Unavailable")
        return Draft(
            body=(
                "Your teacher will review your enquiry."
                if context.get("flow") == "teacher_handoff"
                else "Your teacher will review the makeup options."
            ),
            rationale="Teacher review needed.",
            questions=context["warnings"],
            references=[],
        )

    def reconcile(self, context):
        if self.fail_reconcile:
            raise ModelError("Unavailable")
        return ReviewedMemory(
            request_summary="Teacher approved saying: " + context["teacher_response"]["body"],
            enduring_preferences=[Preference(key="travel", value="public transport")],
        )


def turn(name, arguments, call_id="one"):
    call = ToolCall(call_id=call_id, name=name, arguments=arguments)
    return ToolTurn(calls=[call], output=[])


def start(rig, scenario):
    client = rig[0]
    response = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/agent-runs",
        json={"source_message_id": str(scenario["source"])},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "awaiting_review", result
    return result


def review(client, run, action, **kwargs):
    return client.post(
        f"/api/v1/agent-runs/{run['id']}/review",
        json={"action": action, "expected_revision": run["revision"], **kwargs},
    )
