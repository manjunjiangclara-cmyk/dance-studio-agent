"""Privacy checks inspect actual SDK request bodies using HTTP mocks, not live calls."""

import copy
import json

import httpx
import pytest

from studio_copilot.agent.privacy import StudentPrivacy

from .test_openai_adapter import adapter, response_payload

IDENTITY = {
    "name": "Ariana Vossfield",
    "email": "ariana.vossfield@example.test",
    "id": "311a243f-b844-43ea-bf25-c9563c10fa67",
}


def sensitive_context():
    text = "ARIANA VOSSFIELD, Ariana, Vossfield: ariana.vossfield@example.test"
    return {
        "student": {
            **IDENTITY,
            "ai_summary": text,
            "context": {
                "notes": text,
                "encrypted_content": text,
                IDENTITY["email"]: text,
            },
        },
        "source": {"body": text},
        "history": [{"body": text}],
        "teacher_feedback": text,
        "question_resolutions": [
            {
                "question_id": "93af8764-4445-482f-b6ed-22e8dc178d9a",
                "decision": "answer",
                "answer": text,
            }
        ],
        "interpretation": {"request_summary": text},
        "evidence": [{"result": {"name": text, "address": "other@example.test"}}],
    }


def message_output(value):
    return [
        {
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": json.dumps(value), "annotations": []}],
        }
    ]


@pytest.mark.parametrize(
    "operation",
    ["route", "interpret_makeup", "interpret_enquiry", "draft", "reconcile", "choose_tools"],
)
def test_all_model_operations_hide_identity_and_restore_local_outputs(operation):
    captured = []
    values = {
        "route": {
            "intents": ["makeup"],
            "request_summary": "Request by [STUDENT_NAME]",
            "needs_clarification": False,
            "reason": "A makeup enquiry",
        },
        "interpret_makeup": {
            "request_summary": "Request by [STUDENT_NAME]",
            "absence_date": None,
            "preferred_date": None,
            "preferred_weekday": None,
            "location_preference": None,
            "missing_details": [],
            "enduring_preferences": [],
        },
        "interpret_enquiry": {
            "request_summary": "Request by [STUDENT_NAME]",
            "questions": ["What classes can [STUDENT_NAME] attend?"],
            "requested_actions": [],
            "missing_details": [],
            "enduring_preferences": [],
        },
        "draft": {
            "body": "Hello [STUDENT_NAME], your email is [STUDENT_EMAIL].",
            "rationale": "Teacher review",
            "questions": [],
            "references": [],
        },
        "reconcile": {"request_summary": "Reviewed for [STUDENT_NAME]", "enduring_preferences": []},
    }

    def handler(request):
        captured.append(json.loads(request.content))
        output = [] if operation == "choose_tools" else message_output(values[operation])
        return httpx.Response(200, json=response_payload(output))

    model = adapter(handler)
    context = sensitive_context()
    original = copy.deepcopy(context)
    opaque = "provider-ciphertext-Ariana Vossfield-unchanged"
    transcript = [
        {
            "id": "reason",
            "type": "reasoning",
            "encrypted_content": opaque,
            "summary": [{"type": "summary_text", "text": IDENTITY["name"]}],
        },
        {
            "type": "function_call",
            "call_id": "one",
            "name": "get_locations",
            "arguments": json.dumps({"contact": IDENTITY["name"], "email": IDENTITY["email"]}),
        },
        {
            "type": "function_call_output",
            "call_id": "one",
            "output": json.dumps(
                {"name": IDENTITY["name"], "email": IDENTITY["email"], "id": IDENTITY["id"]}
            ),
        },
    ]
    original_transcript = copy.deepcopy(transcript)
    try:
        if operation == "choose_tools":
            model.choose_tools(context, [])
            model.choose_tools(context, transcript)
            assert captured[-1]["input"][1]["encrypted_content"] == opaque
        else:
            result = getattr(model, operation)(context)
            local = result.model_dump()
            assert IDENTITY["name"] in str(local)
            if operation == "draft":
                assert IDENTITY["email"] in result.body
        for payload in captured:
            visible = copy.deepcopy(payload)
            for item in visible.get("input", []) if isinstance(visible.get("input"), list) else []:
                if item.get("type") == "reasoning":
                    item.pop("encrypted_content", None)
            sent = json.dumps(visible).casefold()
            for identifier in [*IDENTITY.values(), "Ariana", "Vossfield", "other@example.test"]:
                assert identifier.casefold() not in sent
            assert "[student_name]" in sent
            assert "originals" not in visible
        assert context == original
        assert transcript == original_transcript
    finally:
        model.client.close()


def test_unicode_names_nested_json_and_word_boundaries():
    student = {"name": "Zoë Straßenfeld", "email": "zoe@example.test", "id": "student-uuid"}
    privacy = StudentPrivacy(student)
    safe = privacy.redact(
        {
            "body": "ZOE\u0308 Straßenfeld; STRASSENFELD; zoe@EXAMPLE.test",
            "tool_output": json.dumps({"name": student["name"], "email": student["email"]}),
        }
    )
    sent = json.dumps(safe).casefold()
    assert "straßenfeld" not in sent and "strassenfeld" not in sent
    assert "zoe@" not in sent
    assert json.loads(safe["tool_output"])["name"] == "[STUDENT_NAME]"
    assert privacy.restore(safe)["body"].startswith("Zoë Straßenfeld")
    short = StudentPrivacy({"name": "Ann Li"})
    assert (
        short.redact("Ann likes planning at Hillside")
        == "[STUDENT_NAME_1] likes planning at Hillside"
    )


def test_adapter_identity_mapping_is_not_reused_for_a_different_student():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response_payload(
                message_output(
                    {
                        "body": "Hello [STUDENT_NAME].",
                        "rationale": "Review",
                        "questions": [],
                        "references": [],
                    }
                )
            ),
        )

    model = adapter(handler)
    try:
        assert model.draft({"student": IDENTITY}).body == "Hello Ariana Vossfield."
        assert (
            model.draft(
                {
                    "student": {
                        "id": "second",
                        "name": "Bianca Frostvale",
                        "email": "bianca@example.test",
                    }
                }
            ).body
            == "Hello Bianca Frostvale."
        )
        assert "Ariana" not in json.dumps(captured[-1])
        assert "Bianca" not in json.dumps(captured[-1])
    finally:
        model.client.close()


@pytest.mark.parametrize(
    ("name", "body", "identifiers"),
    [
        ("李明", "学生李明今天请假", ["李明"]),
        ("王 小明", "王同学，您好。小明", ["王", "小明"]),
        ("A Li", "Hi A, contact Li.", [" A,", "Li"]),
    ],
)
def test_request_masks_names_without_latin_word_boundaries(name, body, identifiers):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response_payload([]))

    model = adapter(handler)
    try:
        model.choose_tools(
            {
                "student": {**IDENTITY, "name": name},
                "source": {"body": body + " _" + IDENTITY["id"]},
            },
            [],
        )
        sent = json.dumps(captured, ensure_ascii=False)
        for identifier in [*identifiers, IDENTITY["id"]]:
            assert identifier not in sent
        privacy = StudentPrivacy({"name": name})
        assert privacy.restore(privacy.redact(body)) == body
    finally:
        model.client.close()


def test_known_quoted_email_is_masked_in_actual_request():
    address = '"billing team"@example.com'
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response_payload([]))

    model = adapter(handler)
    context = {
        "student": {"name": "Alice Voss", "email": address},
        "source": {"body": "Reply to " + address},
    }
    try:
        model.choose_tools(context, [])
        sent_context = json.loads(captured[0]["input"][0]["content"])
        assert sent_context["student"]["email"] == "[STUDENT_EMAIL]"
        assert sent_context["source"]["body"] == "Reply to [STUDENT_EMAIL]"
        privacy = StudentPrivacy(context["student"])
        assert privacy.restore(privacy.redact(address)) == address
    finally:
        model.client.close()
