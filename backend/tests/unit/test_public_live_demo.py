"""Exercise the real shared LangGraph with fictional records and an isolated SQLite ledger."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from threading import Event
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from studio_copilot.agent.contracts import (
    DocumentEmailComposition,
    Draft,
    EnquiryAnswer,
    EnquiryInterpretation,
    Routing,
    ToolTurn,
)
from studio_copilot.agent.makeup import validated_candidate_ids
from studio_copilot.api import public_demo as api
from studio_copilot.api.app import create_app
from studio_copilot.api.public_demo import DraftInput
from studio_copilot.public_demo.records import CASES, FictionalRecords, example_records
from studio_copilot.public_demo.service import PublicDemo, unsigned_demo_draft
from tests.integration.agent.helpers import FakeModel, turn

BASE = "/api/public-demo"
ORIGIN = "http://localhost:8010"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "Hi Riley,\n\nWear comfortable clothes.\n\nBest,\nRiley James",
            "Hi Riley,\n\nWear comfortable clothes.",
        ),
        (
            "Hi Riley,\n\nWear comfortable clothes.\n\nRiley James",
            "Hi Riley,\n\nWear comfortable clothes.",
        ),
        (
            "Hi Riley,\n\nWear comfortable clothes.\n\nKind regards,\nMerri Ballet",
            "Hi Riley,\n\nWear comfortable clothes.",
        ),
        (
            "Hi Riley,\n\nWear comfortable clothes.\n\n[Teacher Name]",
            "Hi Riley,\n\nWear comfortable clothes.",
        ),
        ("Hi Riley,\n\nSee you then!", "Hi Riley,\n\nSee you then!"),
        (
            "Hi Riley,\n\nYour class is at Merri Ballet.",
            "Hi Riley,\n\nYour class is at Merri Ballet.",
        ),
    ],
)
def test_demo_generated_draft_has_no_signature(body, expected):
    assert unsigned_demo_draft(body, {"context": {"student": {"name": "Riley James"}}}) == expected


def test_public_document_example_is_a_single_clothing_question():
    context = FictionalRecords().context("document")
    assert context["source"]["body"] == (
        "I have never danced before. What should I wear to my first ballet class?"
    )


def test_public_generated_document_draft_removes_signature_but_preserves_teacher_edit(demo):
    ledger, model = demo
    model.routing = Routing(
        intents=["new_student_enquiry"],
        action="information_only",
        request_summary="What should I wear?",
        needs_clarification=False,
        reason="The student asks about clothing.",
    )
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary="What should I wear?",
        questions=["What should I wear?"],
        requested_actions=[],
        missing_details=[],
        enduring_preferences=[],
    )
    model.compose_document_email = lambda context: DocumentEmailComposition(
        body="Hi there,\n\nSocks are suitable for your first class.\n\nBest,\nRiley James",
        review_concerns=[],
    )
    token = ledger.create_walkthrough(str(uuid4()), "new", "What should I wear?")["token"]
    assert not ledger.execute(token, "evidence")["missing_information"]
    draft = ledger.execute(token, "draft")
    assert draft["body"] == "Hi there,\n\nSocks are suitable for your first class."
    edited = draft["body"] + "\n\nTeacher edit"
    assert (
        ledger.execute(token, "approve", revision=draft["revision"], body=edited)["body"] == edited
    )


class DemoGraphModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.drafts = []
        self.compositions = []
        self.approvals = []
        self.proposal = None

    def route(self, context):
        if context["source"]["id"] == CASES["document"]:
            self.routing = Routing(
                intents=["general_enquiry"],
                action="information_only",
                request_summary="Trial policy and class timetable questions.",
                needs_clarification=False,
                reason="The student asks for information.",
            )
        return super().route(context)

    def demo_evidence_route(self, context):
        questions = " ".join(context["interpretation"].get("questions", [])).lower()
        return (
            "documents"
            if any(word in questions for word in ("wear", "clothes", "trial cost"))
            else "records"
        )

    def interpret_enquiry(self, context):
        if context["source"]["id"] == CASES["document"]:
            return EnquiryInterpretation(
                request_summary="Trial policy and class timetable questions.",
                questions=[
                    "What should I wear?",
                    "When and where is the Thursday class?",
                    "What does a trial cost?",
                ],
                missing_details=[],
                enduring_preferences=[],
            )
        return super().interpret_enquiry(context)

    def draft(self, context):
        self.drafts.append(context)
        result = super().draft(context)
        result.booking_session_id = self.proposal
        return result

    def compose_document_email(self, context):
        self.compositions.append(context)
        return DocumentEmailComposition(
            body="\n\n".join(
                item["answer"] for item in context["answers"] if item["status"] == "answered"
            ),
            review_concerns=[],
        )

    def reconcile(self, context):
        self.approvals.append(context)
        return super().reconcile(context)


@pytest.fixture
def demo(tmp_path):
    model = DemoGraphModel()
    return PublicDemo(tmp_path / "ledger.sqlite", factory=lambda: model), model


@pytest.fixture(autouse=True)
def fake_document_provider(monkeypatch):
    """Supply deterministic document answers; retrieval integration is tested separately."""
    from contextlib import nullcontext

    from studio_copilot.documents import online
    from studio_copilot.public_demo import document_index
    from studio_copilot.public_demo.service import DemoStore

    monkeypatch.setattr(document_index, "engine_from_env", lambda: create_engine("sqlite://"))
    monkeypatch.setattr(document_index, "configuration", lambda engine: object())
    monkeypatch.setattr(online, "check_identities", lambda *args, **kwargs: None)
    monkeypatch.setattr(DemoStore, "document_approval_guard", lambda *args: nullcontext())

    def gather(engine, state, **kwargs):
        resolved = {str(x["question_id"]) for x in state.get("question_resolutions", [])}
        evidence = []
        for question in state["interpretation"]["questions"]:
            qid = state["interpretation"]["question_ids"][question]
            if qid in resolved:
                continue
            supported = "wear" in question.lower() or "thursday" in question.lower()
            quote = (
                "Socks are suitable for your first class."
                if "wear" in question.lower()
                else "Thursday class is at 6 pm in Carlton."
            )
            refs = ["document:E0123456789abcdef01234567"] if supported else []
            result = {
                "question_id": qid,
                "question": question,
                "status": "answered" if supported else "abstained",
                "claims": [
                    {
                        "text": quote,
                        "citations": [{"title": "Clothing", "revision": 1, "quote": quote}],
                    }
                ]
                if supported
                else [],
                "references": refs,
                "sources": [{"run_id": str(uuid4())}] if supported else [],
                "missing_information": [] if supported else [question],
            }
            evidence.append(
                {"tool": "document_answer", "arguments": {}, "finding": question, "result": result}
            )
        return {"evidence": evidence, "warnings": []}

    monkeypatch.setattr(online, "gather", gather)


def create(demo, scenario="booking"):
    return demo.create(scenario, str(uuid4()))["token"]


def selected_saturday(records, level="Level 2"):
    return next(
        row
        for row in records["class_sessions"]
        if row["starts_at"].startswith("2027-02-13T")
        and next(group["level"] for group in records["classes"] if group["id"] == row["class_id"])
        == level
    )


def test_daily_admission_idempotency_and_shared_file(demo):
    ledger, model = demo
    request = str(uuid4())
    first = ledger.create("booking", request)
    assert ledger.create("booking", request) == first
    with pytest.raises(HTTPException) as mismatch:
        ledger.create("document", request)
    assert mismatch.value.status_code == 409
    for _ in range(19):
        create(ledger)
    with pytest.raises(HTTPException) as limit:
        create(PublicDemo(ledger.path, factory=lambda: model))
    assert limit.value.status_code == 429
    assert not model.routing_contexts


def test_concurrent_admission_cannot_exceed_twenty(demo):
    ledger, model = demo

    def admit(_):
        try:
            return create(PublicDemo(ledger.path, factory=lambda: model))
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(admit, range(25)))
    assert sum(isinstance(result, str) for result in results) == 20
    assert results.count(429) == 5


def test_sqlite_resume_and_mock_booking_are_revision_bound(demo):
    ledger, model = demo
    saturday = selected_saturday(ledger.records.data)
    model.proposal = UUID(saturday["id"])
    roster = list(saturday["students"])
    token = create(ledger)
    with pytest.raises(HTTPException) as premature:
        ledger.execute(token, "draft")
    assert premature.value.status_code == 409
    evidence = ledger.execute(token, "evidence")
    assert any(
        f"{saturday['capacity'] - len(roster)} places open" in item and "awaiting" in item
        for item in evidence["evidence"]
    )
    assert any("Level 2" in item for item in evidence["evidence"])
    assert not model.drafts and not model.approvals

    next_worker = PublicDemo(ledger.path, factory=lambda: model)
    assert next_worker.execute(token, "evidence") == evidence
    draft = next_worker.execute(token, "draft")
    assert draft["booking_proposed"] is True
    assert next_worker.execute(token, "draft") == draft
    assert len(model.routing_contexts) == len(model.drafts) == 1

    next_worker = PublicDemo(ledger.path, factory=lambda: model)
    with pytest.raises(HTTPException) as stale:
        next_worker.execute(token, "approve", revision=draft["revision"] + 1)
    assert stale.value.status_code == 409
    with pytest.raises(HTTPException) as edited:
        next_worker.execute(token, "approve", revision=draft["revision"], body="A different class.")
    assert edited.value.status_code == 409
    approval = next_worker.execute(token, "approve", revision=draft["revision"])
    assert approval["status"] == "approved_mock"
    assert approval["booking_simulated"] is True
    assert approval["body"] == draft["body"]
    assert approval["body"].startswith("Hi Alex,\n\nThanks for letting me know.")
    assert "on Saturday 13 February 2027 at 6 pm" in approval["body"]
    assert approval["booking"]["session"]["id"] == saturday["id"]
    assert approval["booking"]["student"]["name"] == "Alex Morgan"
    assert next_worker.execute(token, "approve", revision=draft["revision"]) == approval
    assert len(model.approvals) == 1
    assert saturday["students"] == roster
    assert next_worker.records.session_rows[saturday["id"]]["students"] == roster
    with pytest.raises(HTTPException) as different_decision:
        next_worker.execute(token, "approve", revision=draft["revision"], body="Different wording.")
    assert different_decision.value.status_code == 409
    with next_worker.db() as db:
        assert (
            db.execute("SELECT count(*) FROM graph_runs WHERE approval IS NOT NULL").fetchone()[0]
            == 1
        )


def test_document_resume_requires_original_teacher_answers(demo):
    ledger, model = demo
    token = create(ledger, "document")
    evidence = ledger.execute(token, "evidence")
    assert evidence["missing_information"] == ["What does a trial cost?"]
    assert any("socks" in item.lower() for item in evidence["evidence"])
    assert not model.drafts and not model.compositions

    next_worker = PublicDemo(ledger.path, factory=lambda: model)
    with pytest.raises(HTTPException) as unanswered:
        next_worker.execute(token, "draft")
    assert unanswered.value.status_code == 422
    draft = next_worker.execute(token, "draft", teacher_answers=["The trial costs $25."])
    assert "The trial costs $25." in draft["body"]
    assert draft["booking_proposed"] is False
    assert len(model.compositions) == 1
    with pytest.raises(HTTPException) as changed_answers:
        next_worker.execute(token, "draft", teacher_answers=["The trial costs $30."])
    assert changed_answers.value.status_code == 409

    approval = next_worker.execute(
        token, "approve", revision=draft["revision"], body="Reviewed: " + draft["body"]
    )
    assert approval["booking_simulated"] is False
    assert approval["body"].startswith("Reviewed:")


def test_post_draft_teacher_question_can_be_answered_and_regenerated(demo):
    ledger, model = demo
    model.routing = Routing(
        intents=["general_enquiry"],
        action="information_only",
        request_summary="Questions about a Thursday booking.",
        needs_clarification=False,
        reason="The student asks about a personal record.",
    )
    first_question = "Is my Thursday booking confirmed?"
    followup_question = "Was my trial payment received?"
    same_answer = "The teacher confirms this is recorded."
    interpretations = 0

    def interpret(context):
        nonlocal interpretations
        interpretations += 1
        return EnquiryInterpretation(
            request_summary="Questions about a Thursday booking.",
            questions=[first_question]
            if interpretations == 1
            else [first_question, followup_question],
            missing_details=[],
            enduring_preferences=[],
        )

    model.interpret_enquiry = interpret
    token = ledger.create_walkthrough(str(uuid4()), "new", first_question)["token"]
    evidence = ledger.execute(token, "evidence")
    assert evidence["missing_information"] == []
    assert evidence["review_requirements"] == []

    draft = ledger.execute(token, "draft")
    assert draft["missing_information"] == [first_question]
    assert draft["review_requirements"] == ["teacher_input"]
    assert "can't confirm" in draft["body"].lower()

    first_revision = ledger.execute(
        token,
        "revise",
        revision=draft["revision"],
        teacher_answers=[same_answer],
    )
    assert first_revision["missing_information"] == [followup_question]
    assert first_revision["review_requirements"] == ["teacher_input"]
    assert first_revision["revision"] == draft["revision"] + 1

    revised = ledger.execute(
        token,
        "revise",
        revision=first_revision["revision"],
        teacher_answers=[same_answer],
    )
    assert revised["missing_information"] == []
    assert revised["review_requirements"] == []
    assert revised["body"].count(same_answer) == 2
    assert revised["revision"] == first_revision["revision"] + 1
    assert (
        ledger.execute(
            token, "revise", revision=first_revision["revision"], teacher_answers=[same_answer]
        )
        == revised
    )

    approval = ledger.execute(token, "approve", revision=revised["revision"])
    assert approval["status"] == "approved_mock"


def test_teacher_answer_api_accepts_the_shared_question_limit():
    accepted = DraftInput(teacher_answers=[f"Answer {index}" for index in range(20)])
    assert len(accepted.teacher_answers) == 20
    with pytest.raises(ValueError):
        DraftInput(teacher_answers=[f"Answer {index}" for index in range(21)])


def test_public_document_deferral_stays_a_deferral_after_approval(demo):
    ledger, model = demo
    token = create(ledger, "document")
    evidence = ledger.execute(token, "evidence")
    assert evidence["missing_information"] == ["What does a trial cost?"]
    draft = ledger.execute(
        token, "draft", teacher_answers=["I will confirm this information later."]
    )
    assert model.compositions[0]["question_resolutions"][0]["decision"] == "defer"
    approval = ledger.execute(token, "approve", revision=draft["revision"])
    assert approval["status"] == "approved_mock"
    assert not approval["booking_simulated"]
    with ledger.db() as db:
        saved = json.loads(db.execute("SELECT draft FROM graph_runs").fetchone()[0])
        assert saved["question_resolutions"][0]["answer"] is None


@pytest.mark.parametrize("problem", ["full", "over_level", "ambiguous"])
def test_shared_makeup_validation_rejects_unsafe_demo_proposals(tmp_path, problem):
    examples = deepcopy(example_records())
    saturday = selected_saturday(examples)
    if problem == "full":
        saturday["capacity"] = len(saturday["students"])
    elif problem == "over_level":
        saturday = selected_saturday(examples, level="Level 3")
    else:
        examples["class_sessions"].append({**saturday, "id": str(uuid4())})
    model = DemoGraphModel()
    model.proposal = UUID(saturday["id"])
    ledger = PublicDemo(
        tmp_path / "ledger.sqlite", factory=lambda: model, records=FictionalRecords(examples)
    )
    token = create(ledger)
    ledger.execute(token, "evidence")
    draft = ledger.execute(token, "draft")
    assert draft["booking_proposed"] is False
    assert model.proposal not in validated_candidate_ids(model.drafts[0]["evidence"])
    approval = ledger.execute(token, "approve", revision=draft["revision"])
    assert approval["status"] == "approved_mock"
    assert not approval["booking_simulated"]


def test_maya_confirmed_booking_is_reported_without_another_proposal(tmp_path):
    examples = deepcopy(example_records())
    maya = next(
        student for student in examples["students"] if student["display_name"] == "Maya Chen"
    )
    conversation_ids = {
        case["id"] for case in examples["conversations"] if case["student_id"] == maya["id"]
    }
    source = next(
        message
        for message in examples["messages"]
        if message["conversation_id"] in conversation_ids and message["kind"] == "student_email"
    )

    class MayaRecords(FictionalRecords):
        def context(self, scenario):
            context = super().context(scenario)
            timestamped_source = self._message_data(source)
            return {
                **context,
                "source": timestamped_source,
                "history": [timestamped_source],
                "student": {**context["student"], "id": maya["id"], "name": maya["display_name"]},
                "conversation_id": source["conversation_id"],
            }

    records = MayaRecords(examples)
    model = DemoGraphModel()
    model.proposal = UUID(selected_saturday(examples)["id"])
    ledger = PublicDemo(tmp_path / "ledger.sqlite", factory=lambda: model, records=records)
    token = create(ledger)
    evidence = ledger.execute(token, "evidence")
    assert any("Existing makeup booking:" in item for item in evidence["evidence"])
    assert ledger.execute(token, "draft")["booking_proposed"] is False


def test_retry_resumes_persisted_evidence_without_rerouting(demo):
    ledger, model = demo
    token = create(ledger)
    ledger.execute(token, "evidence")
    draft = model.draft

    def temporary_failure(_):
        raise RuntimeError("private provider failure")

    model.draft = temporary_failure
    with pytest.raises(HTTPException) as failed:
        ledger.execute(token, "draft")
    assert failed.value.status_code == 502
    assert "private" not in failed.value.detail

    model.draft = draft
    next_worker = PublicDemo(ledger.path, factory=lambda: model)
    assert next_worker.execute(token, "draft")["body"]
    assert len(model.routing_contexts) == 1
    with next_worker.db() as db:
        assert db.execute("SELECT draft_attempts FROM graph_runs").fetchone()[0] == 2


def test_an_active_stage_cannot_be_started_twice(demo):
    ledger, model = demo
    entered, release = Event(), Event()
    route = model.route

    def slow_route(context):
        entered.set()
        assert release.wait(5)
        return route(context)

    model.route = slow_route
    token = create(ledger)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(ledger.execute, token, "evidence")
        try:
            assert entered.wait(5)
            with pytest.raises(HTTPException) as already_running:
                ledger.execute(token, "evidence")
            assert already_running.value.status_code == 409
        finally:
            release.set()
        assert first.result()["evidence"]
    assert len(model.routing_contexts) == 1


def test_expiry_and_melbourne_day_reset(tmp_path):
    now = [datetime(2026, 11, 15, 23, 59, 50, tzinfo=ZoneInfo("Australia/Melbourne")).timestamp()]
    ledger = PublicDemo(tmp_path / "ledger.sqlite", factory=DemoGraphModel, clock=lambda: now[0])
    token = create(ledger)
    ledger.execute(token, "evidence")
    now[0] += 20
    with pytest.raises(HTTPException) as expired:
        ledger.execute(token, "evidence")
    assert expired.value.status_code == 410
    for _ in range(20):
        create(ledger)
    now[0] += 3601
    with pytest.raises(HTTPException) as still_limited:
        create(ledger)
    assert still_limited.value.status_code == 429
    now[0] += 86400
    create(ledger)
    with ledger.db() as db:
        assert db.execute("SELECT count(*) FROM graph_runs").fetchone()[0] == 22
        assert db.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0


@pytest.fixture
def client(monkeypatch, demo):
    ledger, _ = demo
    monkeypatch.setenv("STUDIO_PUBLIC_LIVE_DEMO", "true")
    monkeypatch.setenv("STUDIO_PUBLIC_DEMO_DB", ledger.path)
    monkeypatch.setenv("PUBLIC_BASE_URL", ORIGIN)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_MODEL", "fake-model")
    monkeypatch.setattr(api, "PublicDemo", lambda _path, **_options: ledger)
    engine = create_engine("sqlite://")
    with TestClient(create_app(engine, admin_token="owner-only"), headers={"Origin": ORIGIN}) as c:
        yield c
    engine.dispose()


@pytest.mark.parametrize("scenario", ["booking", "document", "noah", "riley"])
def test_static_case_get_and_fixed_run_admission(client, demo, scenario):
    ledger, model = demo
    case = client.get(f"{BASE}/cases/{scenario}")
    assert case.status_code == 200
    assert case.json()["messages"][-1]["id"] == CASES[scenario]
    with ledger.db() as db:
        assert db.execute("SELECT count(*) FROM graph_runs").fetchone()[0] == 0

    created = client.post(f"{BASE}/runs", json={"scenario": scenario, "request_id": str(uuid4())})
    assert created.status_code == 200
    assert created.headers["cache-control"] == "no-store"
    assert not model.routing_contexts


def test_public_token_cannot_access_owner_or_mutate_inputs(client):
    for unsafe in (
        {"scenario": "custom"},
        {"scenario": "riley", "email_body": "my request"},
        {"scenario": "noah", "student": "someone-else"},
    ):
        response = client.post(f"{BASE}/runs", json={"request_id": str(uuid4()), **unsafe})
        assert response.status_code == 422
    assert client.post(f"{BASE}/threads", json={}).status_code == 404
    assert client.post(f"{BASE}/evidence", json={}).status_code == 401

    created = client.post(f"{BASE}/runs", json={"scenario": "booking", "request_id": str(uuid4())})
    headers = {"Authorization": "Bearer " + created.json()["token"]}
    assert client.get("/api/v1/students", headers=headers).status_code == 401
    assert client.get("/api/v1/documents", headers=headers).status_code == 401
    assert (
        client.post(
            f"/api/v1/agent-runs/{uuid4()}/review",
            json={"action": "approve", "expected_revision": 1},
            headers=headers,
        ).status_code
        == 401
    )

    evidence = client.post(f"{BASE}/evidence", json={}, headers=headers)
    assert evidence.status_code == 200
    draft = client.post(f"{BASE}/draft", json={}, headers=headers)
    assert draft.status_code == 200
    approval = client.post(
        f"{BASE}/approve", json={"revision": draft.json()["revision"]}, headers=headers
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved_mock"


def test_cross_origin_cannot_admit_or_resume_a_demo(client):
    response = client.post(
        f"{BASE}/runs",
        json={"scenario": "booking", "request_id": str(uuid4())},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403


def test_walkthrough_uses_the_same_graph_and_only_carries_approved_reply(demo):
    ledger, _ = demo
    model = DemoGraphModel()
    model.routing = Routing(
        intents=["general_enquiry"],
        action="information_only",
        request_summary="Question about ballet clothes",
        needs_clarification=False,
        reason="The student asks a question.",
    )
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary="Question about ballet clothes",
        questions=["What should I wear?", "What does a trial cost?"],
        missing_details=[],
        enduring_preferences=[],
    )
    ledger.factory = lambda: model
    request_id = str(uuid4())
    text = "What should I wear, and what's the cost?"
    token = ledger.create_walkthrough(request_id, "new", text)["token"]
    assert ledger.create_walkthrough(request_id, "new", text)["token"] == token
    with pytest.raises(HTTPException) as changed:
        ledger.create_walkthrough(request_id, "new", text + " On Saturday?")
    assert changed.value.status_code == 409
    with pytest.raises(HTTPException) as unapproved:
        ledger.create_walkthrough(str(uuid4()), "new", "Thanks!", token)
    assert unapproved.value.status_code == 409
    evidence = ledger.execute(token, "evidence")
    assert evidence["missing_information"] == ["What does a trial cost?"]
    assert evidence["review_requirements"] == ["teacher_input"]
    resumed = PublicDemo(ledger.path, factory=lambda: model)
    draft = resumed.execute(token, "draft", teacher_answers=["The trial costs $15."])
    assert draft["review_requirements"] == []
    reply = draft["body"] + "\nThanks for checking."
    resumed.execute(token, "approve", revision=draft["revision"], body=reply)

    followup = resumed.create_walkthrough(str(uuid4()), "new", "Can I wear socks?", token)
    followup_evidence = resumed.execute(followup["token"], "evidence")
    assert followup_evidence["missing_information"] == []
    assert "The trial costs $15." in followup_evidence["evidence"]
    with resumed.checkpoints() as saver:
        checkpoint = saver.get({"configurable": {"thread_id": request_id}})
    assert checkpoint is not None
    context = model.routing_contexts[-1]
    assert [item["body"] for item in context["history"]] == [text, "Can I wear socks?"]
    assert [item["body"] for item in context["approved_replies"]] == [reply]
    assert context["student"]["name"] == "New enquirer"
    assert context["confirmed_bookings"] == []


def test_walkthrough_admission_only_accepts_fictional_student_and_origin(client):
    url = f"{BASE}/walkthrough/runs"
    payload = {"request_id": str(uuid4()), "student": str(uuid4()), "email_body": "Hello."}
    assert client.post(url, json=payload).status_code == 422
    payload["student"] = "new"
    assert (
        client.post(url, json=payload, headers={"Origin": "https://other.example"}).status_code
        == 403
    )
    response = client.post(url, json=payload)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    assert client.get("/api/v1/students", headers=headers).status_code == 401
    assert client.get("/api/v1/documents", headers=headers).status_code == 401


def test_walkthrough_checks_the_selected_students_existing_makeup(demo):
    ledger, model = demo
    maya = next(
        row["id"] for row in ledger.records.students.values() if row["display_name"] == "Maya Chen"
    )
    model.proposal = UUID(selected_saturday(ledger.records.data)["id"])
    token = ledger.create_walkthrough(
        str(uuid4()), maya, "Is my Saturday makeup for Monday 8 February booked?"
    )["token"]
    evidence = ledger.execute(token, "evidence")["evidence"]
    assert any("Existing makeup booking:" in item for item in evidence)
    assert ledger.execute(token, "draft")["booking_proposed"] is False
    assert model.routing_contexts[-1]["student"]["id"] == maya


def test_walkthrough_trial_handoff_keeps_session_details_without_a_followup_promise(demo):
    ledger, model = demo
    riley = next(
        row["id"]
        for row in ledger.records.students.values()
        if row["display_name"] == "Riley James"
    )
    model.routing = Routing(
        intents=["enrolment"],
        action="other_action",
        request_summary="Book the Saturday Level 1 trial.",
        needs_clarification=False,
        reason="Trial booking requires a teacher.",
    )
    question = "Which class suits a beginner?"
    action = "Book the Saturday Level 1 trial."
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary=action,
        questions=[question],
        requested_actions=[action],
        missing_details=[],
        enduring_preferences=[],
    )
    session = "Adult Ballet Level 1 is on Saturday 13 February at 4 pm in Brunswick."
    model.draft = lambda context: Draft(
        body=(
            f"Hi Riley,\n\n{session} I haven’t booked it yet; "
            "I’ll confirm your placement and follow up about enrolment."
        ),
        rationale="Trial booking requires a teacher.",
        questions=[],
        references=[f"student:{riley}"],
        answers=[
            EnquiryAnswer(
                question=question,
                status="answered",
                answer=session,
                references=[f"student:{riley}"],
            )
        ],
    )
    run = ledger.create_walkthrough(
        str(uuid4()), riley, "Yes, please book the Level 1 trial on Saturday."
    )
    evidence = ledger.execute(run["token"], "evidence")
    assert evidence["review_requirements"] == ["teacher_review"]
    draft = ledger.execute(run["token"], "draft")
    assert draft["review_requirements"] == ["teacher_review"]
    assert session in draft["body"]
    assert "I haven’t booked it yet." in draft["body"]
    assert "follow up" not in draft["body"]
    assert "confirm your placement" not in draft["body"]
    assert draft["booking_proposed"] is False


def test_trial_handoff_retains_a_verified_session_for_action_only_requests(demo):
    ledger, model = demo
    riley = next(
        row["id"]
        for row in ledger.records.students.values()
        if row["display_name"] == "Riley James"
    )
    action = "Book the Saturday Level 1 trial."
    model.routing = Routing(
        intents=["enrolment"],
        action="other_action",
        request_summary=action,
        needs_clarification=False,
        reason="Trial booking requires a teacher.",
    )
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary=action,
        questions=[],
        requested_actions=[action],
        missing_details=[],
        enduring_preferences=[],
    )
    model.turns = lambda count: (
        turn(
            "search_sessions",
            {
                "from_date": "2027-02-13",
                "to_date": "2027-02-13",
                "level": "Level 1",
                "weekday": 5,
                "location_id": None,
            },
        )
        if count == 1
        else ToolTurn(calls=[], output=[])
    )
    run = ledger.create_walkthrough(str(uuid4()), riley, "Please book the Saturday Level 1 trial.")
    ledger.execute(run["token"], "evidence")
    draft = ledger.execute(run["token"], "draft")
    assert (
        "Adult Ballet Level 1 at Merri Ballet, Brunswick on Saturday 13 February 2027 at 4 pm"
        in draft["body"]
    )
    assert "12 places are currently available." in draft["body"]
    assert "Placement needs to be confirmed before a trial can be booked." in draft["body"]
    assert draft["booking_proposed"] is False


def _trial_model(model):
    model.routing = Routing(
        intents=["enrolment"],
        action="other_action",
        request_summary="Handle the Level 1 trial.",
        needs_clarification=False,
        reason="The student is interested in a trial.",
    )


def test_public_trial_books_automatically_and_replays_saved_confirmation(demo):
    ledger, model = demo
    _trial_model(model)
    riley = next(
        row["id"]
        for row in ledger.records.students.values()
        if row["display_name"] == "Riley James"
    )
    session = selected_saturday(ledger.records.data, "Level 1")
    roster = list(session["students"])
    run = ledger.create_walkthrough(
        str(uuid4()),
        riley,
        "Please book me into the Level 1 trial on Saturday 13 February at 4 pm in Brunswick.",
    )
    result = ledger.execute(run["token"], "evidence")
    approval = result["automatic_approval"]
    assert result["review_requirements"] == []
    assert approval["booking_kind"] == "trial"
    assert approval["booking"]["session"]["id"] == session["id"]
    assert "I've booked you into Adult Ballet Level 1" in approval["body"]
    assert session["students"] == roster
    resumed = PublicDemo(ledger.path, factory=lambda: model)
    assert resumed.execute(run["token"], "evidence") == result
    with pytest.raises(HTTPException) as edited:
        resumed.execute(
            run["token"], "approve", revision=approval["revision"], body="Book another class."
        )
    assert edited.value.status_code == 409
    duplicate = ledger.create_walkthrough(
        str(uuid4()),
        riley,
        "Please book me into the Level 1 trial on Saturday 13 February at 4 pm in Brunswick.",
        run["token"],
    )
    assert "automatic_approval" not in ledger.execute(duplicate["token"], "evidence")


def test_trial_with_an_additional_answered_question_stays_on_review_path(demo):
    ledger, model = demo
    _trial_model(model)
    model.routing = Routing(
        intents=["enrolment"],
        action="other_action",
        request_summary="Book an available trial.",
        needs_clarification=False,
        reason="The student requests a trial.",
    )
    model.interpret_enquiry = lambda context: EnquiryInterpretation(
        request_summary="Book an available trial and answer a clothing question.",
        questions=["What should I wear?"],
        requested_actions=["Book the Level 1 trial on Saturday at 4 pm in Brunswick."],
        missing_details=[],
        enduring_preferences=[],
    )
    run = ledger.create_walkthrough(
        str(uuid4()),
        "new",
        "Please book me into the Level 1 trial on Saturday 13 February at 4 pm in Brunswick. "
        "What should I wear?",
    )
    result = ledger.execute(run["token"], "evidence")
    assert "automatic_approval" not in result
    assert any("socks" in item.lower() for item in result["evidence"])
    assert result["review_requirements"] == ["teacher_review"]


def test_short_acceptance_books_only_a_verified_previous_trial_offer(demo):
    ledger, model = demo
    _trial_model(model)
    model.turns = lambda count: (
        turn(
            "search_sessions",
            {
                "from_date": "2027-02-13",
                "to_date": "2027-02-13",
                "weekday": 5,
                "level": "Level 1",
                "location_id": None,
            },
        )
        if count == 1
        else ToolTurn(calls=[], output=[])
    )
    prior = ledger.create_walkthrough(str(uuid4()), "new", "I'm interested in a beginner trial.")
    assert "automatic_approval" not in ledger.execute(prior["token"], "evidence")
    draft = ledger.execute(prior["token"], "draft")
    ledger.execute(
        prior["token"],
        "approve",
        revision=draft["revision"],
        body="Would you like me to book the Level 1 trial in Brunswick on Saturday at 4–5 pm?",
    )

    followup = ledger.create_walkthrough(
        str(uuid4()), "new", "Yes, please book it.", prior["token"]
    )
    response = ledger.execute(followup["token"], "evidence")
    assert (
        response["automatic_approval"]["booking"]["session"]["id"]
        == selected_saturday(ledger.records.data, "Level 1")["id"]
    )


@pytest.mark.parametrize(
    "email",
    [
        "Can I book the Level 1 trial on Saturday at 4 pm in Brunswick?",
        "Please book me into the Level 1 trial on Saturday at 4 pm in Brunswick if it's free.",
        "Please book me into the Level 1 trial on Saturday 14 February at 4 pm.",
        "Please book me into the Level 1 trial on Saturday at 4 pm or 5 pm.",
        "Please book me into the Level 1 trial on Saturday at 4 pm in Coburg.",
        "Thanks for the information.\n> Please book the Level 1 trial on Saturday at 4 pm.",
        "Yes, please book it.",
    ],
)
def test_trial_requires_clear_consent_and_a_single_matching_session(demo, email):
    ledger, model = demo
    _trial_model(model)
    run = ledger.create_walkthrough(str(uuid4()), "new", email)
    assert "automatic_approval" not in ledger.execute(run["token"], "evidence")


def test_full_fictional_trial_does_not_auto_book(demo):
    ledger, model = demo
    _trial_model(model)
    session = selected_saturday(ledger.records.data, "Level 1")
    session["capacity"] = len(session["students"])
    run = ledger.create_walkthrough(
        str(uuid4()), "new", "Please book the Level 1 trial on Saturday at 4 pm in Brunswick."
    )
    assert "automatic_approval" not in ledger.execute(run["token"], "evidence")
    assert ledger.execute(run["token"], "draft")["booking_proposed"] is False


def test_public_documents_include_the_expanded_fictional_library():
    response = TestClient(api.create_public_demo_app()).get("/api/public-demo/documents")
    assert response.status_code == 200
    rows = response.json()
    assert len({item["id"] for item in rows}) == len(rows)
    assert len({item["filename"] for item in rows}) == len(rows)
    assert len(rows) >= 24
    assert all(len(item["content"].split()) >= 300 for item in rows[6:])
    assert all(item["byte_size"] == len(item["content"].encode("utf-8")) for item in rows)
