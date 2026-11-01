"""Exercise the installed OpenAI SDK against an HTTP mock, never the live API."""

import json

import httpx
import pytest
from openai import OpenAI

from studio_copilot.agent.contracts import ModelError
from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.tools import tool_definitions


def response_payload(output, status="completed"):
    return {
        "id": "resp_mock",
        "object": "response",
        "created_at": 1,
        "model": "test-model",
        "status": status,
        "output": output,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


def adapter(handler):
    client = OpenAI(
        api_key="synthetic-test-key",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return OpenAIModel(client=client, model="test-model")


def test_sdk_parses_typed_interpretation_and_keeps_state_local():
    captured = []
    interpretation = {
        "request_summary": "Saturday makeup",
        "absence_date": "2027-02-08",
        "preferred_date": "2027-02-13",
        "preferred_weekday": "Saturday",
        "location_preference": None,
        "missing_details": [],
        "enduring_preferences": [],
    }

    def handler(request):
        captured.append(json.loads(request.content))
        output = [
            {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": json.dumps(interpretation), "annotations": []}
                ],
            }
        ]
        return httpx.Response(200, json=response_payload(output))

    model = adapter(handler)
    try:
        assert (
            model.interpret_makeup({"source": {"body": "Saturday instead"}}).preferred_weekday
            == "Saturday"
        )
        assert captured[0]["store"] is False
        assert captured[0]["text"]["format"]["strict"] is True
        assert captured[0]["include"] == ["reasoning.encrypted_content"]
    finally:
        model.client.close()


@pytest.mark.parametrize("reasoning_fields", [{}, {"status": None}])
def test_sdk_native_tool_calls_preserve_reasoning_and_results(reasoning_fields):
    captured = []
    output = [
        {
            "id": "rs_mock",
            "type": "reasoning",
            "summary": [],
            "encrypted_content": "opaque",
            **reasoning_fields,
        },
        {
            "id": "fc_mock",
            "type": "function_call",
            "call_id": "call_mock",
            "name": "get_enrolments",
            "arguments": '{"on_date":"2027-02-08"}',
            "status": "completed",
        },
    ]

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response_payload(output))

    model = adapter(handler)
    try:
        first = model.choose_tools({"source": "email"}, [])
        assert first.calls[0].arguments == {"on_date": "2027-02-08"}
        transcript = [
            *first.output,
            {"type": "function_call_output", "call_id": "call_mock", "output": "{}"},
        ]
        model.choose_tools({"source": "email"}, transcript)
        replayed = captured[-1]["input"][1:]
        assert replayed[0] == {
            "id": "rs_mock",
            "type": "reasoning",
            "summary": [],
            "encrypted_content": "opaque",
        }
        assert replayed[1] == {
            **output[1],
            "arguments": json.dumps({"on_date": "2027-02-08"}),
        }
        assert replayed[2] == {
            "type": "function_call_output",
            "call_id": "call_mock",
            "output": "{}",
        }
    finally:
        model.client.close()


@pytest.mark.parametrize("operation", ["interpret_makeup", "interpret_enquiry"])
@pytest.mark.parametrize("kind", ["refusal", "incomplete", "invalid", "provider_error"])
def test_sdk_errors_do_not_leak_provider_details(kind, operation):
    def handler(request):
        if kind == "provider_error":
            return httpx.Response(
                500,
                json={"error": {"message": "sensitive-provider-detail", "type": "server_error"}},
            )
        if kind == "refusal":
            content = [{"type": "refusal", "refusal": "Cannot comply"}]
        else:
            content = [{"type": "output_text", "text": "{}", "annotations": []}]
        output = [
            {
                "id": "msg",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": content,
            }
        ]
        return httpx.Response(
            200,
            json=response_payload(output, "incomplete" if kind == "incomplete" else "completed"),
        )

    model = adapter(handler)
    try:
        with pytest.raises(ModelError) as caught:
            getattr(model, operation)({})
        assert "sensitive-provider-detail" not in str(caught.value)
    finally:
        model.client.close()


def test_tool_schemas_are_strict_and_have_no_write_tools():
    definitions = tool_definitions()
    assert {tool["name"] for tool in definitions} == {
        "get_timetable",
        "get_enrolments",
        "search_sessions",
        "get_locations",
        "check_absence_notice",
    }
    for tool in definitions:
        schema = tool["parameters"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_real_adapter_configuration_has_bounded_timeouts_and_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    model = OpenAIModel()
    try:
        assert model.client.max_retries == 1
        assert model.client.timeout == 20.0
    finally:
        model.client.close()


def test_sdk_parses_router_independently_of_makeup_fields():
    captured = []
    routing = {
        "intents": ["enrolment"],
        "action": "other_action",
        "request_summary": "Change regular classes next term.",
        "needs_clarification": False,
        "reason": "A regular enrolment change, not a makeup.",
    }

    def handler(request):
        captured.append(json.loads(request.content))
        output = [
            {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": json.dumps(routing), "annotations": []}
                ],
            }
        ]
        return httpx.Response(200, json=response_payload(output))

    model = adapter(handler)
    try:
        result = model.route({"source": {"body": "Change classes next term"}, "history": []})
        assert result.intents == ["enrolment"]
        assert result.action == "other_action"
        properties = captured[0]["text"]["format"]["schema"]["properties"]
        assert "absence_date" not in properties
        assert "intents" in properties
    finally:
        model.client.close()


def test_sdk_extracts_enquiry_questions_and_actions_with_strict_schema():
    captured = []
    interpretation = {
        "request_summary": "Thursday times and a cancellation request",
        "missing_details": [],
        "enduring_preferences": [],
        "questions": ["What time is Thursday's class?"],
        "requested_actions": ["Cancel my regular enrolment"],
    }

    def handler(request):
        captured.append(json.loads(request.content))
        output = [
            {
                "id": "msg_mock",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": json.dumps(interpretation), "annotations": []}
                ],
            }
        ]
        return httpx.Response(200, json=response_payload(output))

    model = adapter(handler)
    try:
        result = model.interpret_enquiry(
            {"source": {"body": "What time is Thursday? Cancel my enrolment."}}
        )
        assert result.questions == interpretation["questions"]
        assert result.requested_actions == interpretation["requested_actions"]
        schema = captured[0]["text"]["format"]
        assert schema["strict"] is True
        assert "requested_actions" in schema["schema"]["required"]
        assert "question_ids" not in schema["schema"]["properties"]
        assert result.question_ids == {}
        assert captured[0]["store"] is False
    finally:
        model.client.close()
