"""Enquiries share the durable teacher-review flow without business-record writes."""

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.agent.contracts import (
    Draft,
    EnquiryAnswer,
    EnquiryInterpretation,
    ModelError,
    Routing,
    ToolTurn,
)
from studio_copilot.agent.workflow.graph import Workflow
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Enrolment,
    Message,
    SessionAttendance,
    Student,
)

from .helpers import review, start, turn

pytestmark = pytest.mark.integration

QUESTIONS = [
    "When is the Monday class?",
    "Which level would suit my experience?",
    "What are the fees?",
]


def configure_enquiry(model):
    captured = {"interpretations": [], "drafts": []}
    model.routing = Routing(
        intents=["general_enquiry"],
        action="information_only",
        request_summary="Questions about Monday classes, level and fees.",
        needs_clarification=False,
        reason="The student requests information without asking for an action.",
    )

    def interpret(context):
        captured["interpretations"].append(context)
        return EnquiryInterpretation(
            request_summary="Questions about Monday classes, level and fees.",
            missing_details=[],
            enduring_preferences=[],
            questions=QUESTIONS,
            requested_actions=[],
        )

    def draft(context):
        captured["drafts"].append(context)
        if model.fail_draft:
            raise ModelError("Synthetic drafting failure")
        timetable = next(
            item["result"] for item in context["evidence"] if item["tool"] == "get_timetable"
        )
        item = timetable["items"][0]
        reference = "class:" + item["id"]
        revised = bool(context.get("teacher_feedback"))
        return Draft(
            body=(
                "The Monday class is at 6 pm. Please tell us about your dance experience. "
                + (
                    "Your teacher will confirm the current fees."
                    if revised
                    else "Fees need review."
                )
            ),
            rationale="Timetable evidence supports the time; level and fees remain unresolved.",
            questions=[QUESTIONS[1]],
            references=[reference],
            answers=[
                EnquiryAnswer(
                    question=QUESTIONS[0],
                    status="answered",
                    answer="The Monday class starts at 6 pm.",
                    references=[reference],
                ),
                EnquiryAnswer(
                    question=QUESTIONS[1],
                    status="needs_student",
                    answer="Please tell us about your dance experience.",
                    references=[],
                ),
                EnquiryAnswer(
                    question=QUESTIONS[2],
                    status="needs_teacher",
                    answer="Your teacher will confirm the current fees.",
                    references=[],
                ),
            ],
        )

    model.interpret_enquiry = interpret
    model.draft = draft
    model.turns = lambda n: turn("get_timetable", {}) if n % 2 else ToolTurn(calls=[], output=[])
    return captured


def business_records(engine):
    with Session(engine) as db:
        return {
            "enrolments": db.scalar(select(func.count()).select_from(Enrolment)),
            "attendance": db.scalar(select(func.count()).select_from(SessionAttendance)),
            "rosters": {
                str(item.id): list(item.students) for item in db.scalars(select(ClassSession))
            },
            "levels": {str(item.id): item.highest_level for item in db.scalars(select(Student))},
        }


def defer_teacher_questions(client, run):
    choices = [
        {"question_id": item["question_id"], "decision": "defer", "answer": None}
        for item in run["draft_details"]["answers"]
        if item["status"] == "needs_teacher"
    ]
    response = review(client, run, "revise", question_resolutions=choices)
    assert response.status_code == 200, response.text
    return response.json()


def test_regenerate_without_feedback_creates_reviewable_revision(rig, scenario, db_engine):
    client, model, _, _ = rig
    captured = configure_enquiry(model)
    run = start(rig, scenario)
    before = business_records(db_engine)
    original_drafts = len(captured["drafts"])

    response = review(client, run, "revise", regenerate=True)
    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["status"] == "awaiting_review"
    assert revised["revision"] == run["revision"] + 1
    assert revised["approved_response_id"] is None
    assert len(captured["drafts"]) == original_drafts + 1
    assert captured["drafts"][-1]["teacher_feedback"] == ""
    assert business_records(db_engine) == before

    stale = review(client, run, "revise", regenerate=True)
    assert stale.status_code == 409
    fee_id = revised["draft_details"]["answers"][2]["question_id"]
    answered = review(
        client,
        revised,
        "revise",
        question_resolutions=[
            {"question_id": fee_id, "decision": "answer", "answer": "The fee is $25."}
        ],
    ).json()
    prompted = review(client, answered, "revise", feedback="Keep it concise.").json()
    regenerated = review(client, prompted, "revise", regenerate=True)
    assert regenerated.status_code == 200, regenerated.text
    final_draft = regenerated.json()
    assert final_draft["revision"] == prompted["revision"] + 1
    assert captured["drafts"][-1]["teacher_feedback"] == "Keep it concise."
    assert final_draft["draft_details"]["answers"][2]["answer"] == "The fee is $25."
    assert "The fee is $25." in final_draft["draft_details"]["body"]
    assert (
        final_draft["draft_details"]["question_resolutions"]
        == prompted["draft_details"]["question_resolutions"]
    )
    closed = review(client, final_draft, "reject")
    assert closed.status_code == 200
    assert review(client, final_draft, "revise", regenerate=True).status_code == 409


def test_multiquestion_enquiry_persists_review_and_memory_without_business_writes(
    rig, scenario, db_engine
):
    client, model, _, _ = rig
    captured = configure_enquiry(model)
    before = business_records(db_engine)
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "enquiry"
    assert run["interpretation"]["questions"] == QUESTIONS
    assert run["interpretation"]["requested_actions"] == []
    assert [item["status"] for item in run["draft_details"]["answers"]] == [
        "answered",
        "needs_student",
        "needs_teacher",
    ]
    assert model.contexts == []
    assert captured["interpretations"][0]["source"]["id"] == str(scenario["source"])
    assert run["draft_details"]["booking_session_id"] is None
    assert business_records(db_engine) == before
    assert (
        client.get(f"/api/v1/agent-runs/{run['id']}").json()["draft_details"]
        == run["draft_details"]
    )

    revised_response = review(client, run, "revise", feedback="Say the teacher will confirm fees.")
    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()
    assert revised["status"] == "awaiting_review"
    assert revised["revision"] == run["revision"] + 1
    assert captured["drafts"][-1]["teacher_feedback"] == "Say the teacher will confirm fees."
    assert len(revised["draft_details"]["answers"]) == len(QUESTIONS)
    revised = defer_teacher_questions(client, revised)

    final_body = "Monday is at 6 pm. Please tell me your experience; I will confirm fees."
    approved_response = review(client, revised, "approve", body=final_body)
    assert approved_response.status_code == 200, approved_response.text
    approved = approved_response.json()
    assert approved["status"] == "approved"
    assert business_records(db_engine) == before
    profile = client.get(f"/api/v1/students/{scenario['student']}").json()
    assert final_body in profile["ai_summary"]
    with Session(db_engine) as db:
        response = db.get(Message, UUID(approved["approved_response_id"]))
        assert response.body == final_body
        assert response.kind == "teacher_response"


@pytest.mark.parametrize("failure", ["draft", "query"])
def test_enquiry_failures_leave_unresolved_questions_reviewable(rig, scenario, failure):
    model = rig[1]
    configure_enquiry(model)
    if failure == "draft":
        model.fail_draft = True
    else:

        def unavailable(context, transcript):
            raise ModelError("Synthetic query failure")

        model.choose_tools = unavailable
        model.draft = lambda context: Draft(
            body="Your teacher will review these questions.",
            rationale="The timetable could not be checked.",
            questions=[],
            references=[],
            answers=[],
        )
    run = start(rig, scenario)
    answers = run["draft_details"]["answers"]
    assert {answer["question"] for answer in answers} == set(QUESTIONS)
    assert all(answer["status"] != "answered" for answer in answers)
    assert run["draft_details"]["booking_session_id"] is None
    assert "Synthetic drafting failure" not in str(run)
    assert "Synthetic query failure" not in str(run)


def test_invented_answer_reference_is_removed_and_downgraded(rig, scenario):
    model = rig[1]
    configure_enquiry(model)
    original = model.draft

    def unsupported(context):
        draft = original(context)
        draft.answers[0].references = ["class:invented"]
        draft.answers[0].answer = "UNSUPPORTED_TIMETABLE_CLAIM"
        draft.body = "UNSUPPORTED_TIMETABLE_CLAIM"
        return draft

    model.draft = unsupported
    run = start(rig, scenario)
    first = run["draft_details"]["answers"][0]
    assert first["status"] == "needs_teacher"
    assert first["references"] == []
    assert "class:invented" not in str(run["draft_details"])
    assert "UNSUPPORTED_TIMETABLE_CLAIM" not in str(run["draft_details"])


@pytest.mark.parametrize("malformation", ["missing", "duplicate", "unknown", "no_reference"])
def test_answer_normalization_preserves_each_extracted_question_once(rig, scenario, malformation):
    model = rig[1]
    configure_enquiry(model)
    original = model.draft

    def malformed(context):
        draft = original(context)
        if malformation == "missing":
            draft.answers = draft.answers[1:]
        elif malformation == "duplicate":
            draft.answers.append(draft.answers[0].model_copy())
        elif malformation == "unknown":
            draft.answers.append(
                EnquiryAnswer(
                    question="An invented question",
                    status="needs_teacher",
                    answer="An invented answer",
                    references=[],
                )
            )
        else:
            draft.answers[0].references = []
        return draft

    model.draft = malformed
    answers = start(rig, scenario)["draft_details"]["answers"]
    assert [answer["question"] for answer in answers] == QUESTIONS
    if malformation in {"missing", "no_reference"}:
        assert answers[0]["status"] == "needs_teacher"


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("get_locations", {"location_id": None}),
        (
            "search_sessions",
            {
                "from_date": "2027-02-08",
                "to_date": "2027-02-08",
                "weekday": 0,
                "level": None,
                "location_id": None,
            },
        ),
    ],
)
def test_enquiry_can_retrieve_precise_sessions_and_locations(rig, scenario, tool, arguments):
    model = rig[1]
    configure_enquiry(model)
    model.turns = lambda n: turn(tool, arguments) if n == 1 else ToolTurn(calls=[], output=[])

    def draft(context):
        references = context["evidence"][0]["result"]["references"]
        return Draft(
            body="The live studio details have been checked.",
            rationale="The requested public information was retrieved.",
            questions=[],
            references=references,
            answers=[
                EnquiryAnswer(
                    question=QUESTIONS[0],
                    status="answered",
                    answer="The live studio details have been checked.",
                    references=references,
                )
            ],
        )

    model.draft = draft
    run = start(rig, scenario)
    result = run["evidence"][0]["result"]
    assert result["items"]
    assert str(scenario["student"]) not in str(result)
    assert run["draft_details"]["answers"][0]["status"] == "answered"
    assert run["draft_details"]["booking_session_id"] is None


def test_enquiry_tool_dispatch_does_not_execute_student_record_lookup(rig, scenario, monkeypatch):
    model = rig[1]
    configure_enquiry(model)
    model.turns = lambda n: turn("get_enrolments", {"on_date": "2027-02-08"})
    executed = []

    def forbidden(*args, **kwargs):
        executed.append((args, kwargs))
        raise AssertionError("An enquiry must not dispatch a student-record lookup")

    monkeypatch.setattr("studio_copilot.agent.workflow.queries.execute_tool", forbidden)
    model.draft = lambda context: Draft(
        body="The teacher will review your enquiry.",
        rationale="A disallowed lookup cannot supply evidence.",
        questions=[],
        references=[],
    )
    run = start(rig, scenario)
    assert executed == []
    assert all(not item["result"].get("items") for item in run["evidence"])
    assert all(item["status"] != "answered" for item in run["draft_details"]["answers"])


@pytest.mark.parametrize("failure", ["model", "schema"])
def test_enquiry_interpretation_failure_has_a_reviewable_fallback(rig, scenario, failure):
    model = rig[1]
    configure_enquiry(model)

    def unavailable(context):
        if failure == "schema":
            return EnquiryInterpretation(
                request_summary="Invalid extraction",
                missing_details=[],
                enduring_preferences=[],
                questions=[""],
                requested_actions=[],
            )
        raise ModelError("Synthetic extraction failure")

    model.interpret_enquiry = unavailable
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "enquiry"
    assert run["interpretation"]["missing_details"]
    assert run["draft_details"]["answers"]
    assert all(answer["status"] == "needs_teacher" for answer in run["draft_details"]["answers"])
    assert "Synthetic extraction failure" not in str(run)


def test_requested_action_is_visible_but_approval_cannot_change_enrolment(rig, scenario, db_engine):
    client, model, _, _ = rig
    configure_enquiry(model)
    model.routing = model.routing.model_copy(
        update={"action": "other_action", "intents": ["enrolment"]}
    )
    original = model.interpret_enquiry

    def extract_action(context):
        result = original(context)
        result.questions = []
        result.requested_actions = ["Enrol me in the Monday class."]
        return result

    model.interpret_enquiry = extract_action
    before = business_records(db_engine)
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert run["interpretation"]["questions"] == []
    assert run["interpretation"]["requested_actions"] == ["Enrol me in the Monday class."]
    assert run["draft_details"]["answers"] == []
    result = review(client, run, "approve", body="I will review your enrolment request.")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "approved"
    assert business_records(db_engine) == before


@pytest.mark.parametrize("action", ["other_action", "unclear"])
def test_action_classification_is_not_lost_when_extraction_omits_it(rig, scenario, action):
    model = rig[1]
    configure_enquiry(model)
    model.routing = model.routing.model_copy(update={"action": action})
    original = model.interpret_enquiry

    def empty(context):
        return original(context).model_copy(update={"questions": [], "requested_actions": []})

    model.interpret_enquiry = empty
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "teacher_handoff"
    assert run["interpretation"]["requested_actions"] == [model.routing.request_summary]
    assert run["draft_details"]["booking_session_id"] is None


def test_informational_makeup_cannot_propose_or_approve_a_booking(rig, scenario, db_engine):
    client, model, _, _ = rig
    configure_enquiry(model)
    model.routing = model.routing.model_copy(update={"intents": ["makeup"]})
    original = model.draft

    def invalid_proposal(context):
        result = original(context)
        result.body = "I've booked you into Monday."
        result.booking_session_id = scenario["session"]
        return result

    model.draft = invalid_proposal
    before = business_records(db_engine)
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == "enquiry"
    assert model.contexts == []
    assert run["draft_details"]["booking_session_id"] is None
    assert "I've booked" not in run["draft_details"]["body"]
    run = defer_teacher_questions(client, run)
    approved = review(client, run, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert business_records(db_engine) == before


def test_empty_extraction_preserves_source_request_for_teacher_review(rig, scenario):
    model = rig[1]
    configure_enquiry(model)
    original = model.interpret_enquiry

    def empty(context):
        return original(context).model_copy(update={"questions": [], "requested_actions": []})

    model.interpret_enquiry = empty
    model.draft = lambda context: Draft(
        body="An unsupported answer without a question checklist.",
        rationale="Synthetic empty extraction",
        questions=[],
        references=[],
    )
    run = start(rig, scenario)
    answers = run["draft_details"]["answers"]
    assert len(answers) == 1
    assert answers[0]["question"] == "Thursday please"
    assert answers[0]["status"] == "needs_teacher"
    assert answers[0]["question_id"] in run["draft_details"]["required_question_ids"]
    assert "unsupported answer" not in run["draft_details"]["body"]
    assert run["draft_details"]["body"].strip()


def test_legacy_handoff_checkpoint_can_be_revised_then_approved(rig, scenario, db_engine):
    client, model, service, saver = rig
    configure_enquiry(model)
    model.routing = model.routing.model_copy(update={"action": "other_action"})
    before = business_records(db_engine)
    run = start(rig, scenario)
    config = {"configurable": {"thread_id": run["id"]}}
    graph = Workflow(db_engine, model).compile(saver)
    state = graph.get_state(config).values
    legacy_routing = {key: value for key, value in state["routing"].items() if key != "action"}
    legacy_interpretation = {
        key: value
        for key, value in state["interpretation"].items()
        if key not in {"questions", "requested_actions"}
    }
    legacy_draft = {key: value for key, value in state["draft"].items() if key != "answers"}
    graph.update_state(
        config,
        {
            "routing": legacy_routing,
            "context": {**state["context"], "routing": legacy_routing},
            "interpretation": legacy_interpretation,
            "draft": legacy_draft,
        },
        as_node="persist_draft",
    )
    with Session(db_engine) as db, db.begin():
        saved = db.get(AgentRun, UUID(run["id"]))
        saved.interpretation = {
            **legacy_interpretation,
            "routing": legacy_routing,
            "flow": "teacher_handoff",
        }
        saved.draft_details = {
            key: value for key, value in saved.draft_details.items() if key != "answers"
        }
    revised_response = review(client, run, "revise", feedback="Please confirm the current fees.")
    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()
    assert revised["status"] == "awaiting_review", revised
    assert revised["interpretation"]["flow"] == "teacher_handoff"
    assert len(revised["draft_details"]["answers"]) == len(QUESTIONS)
    revised = defer_teacher_questions(client, revised)
    approved = review(client, revised, "approve", body="I will confirm these details.")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert business_records(db_engine) == before


@pytest.mark.parametrize("flow", ["enquiry", "teacher_handoff"])
def test_non_makeup_can_answer_from_retained_student_context(rig, scenario, flow):
    model = rig[1]
    configure_enquiry(model)
    if flow == "teacher_handoff":
        model.routing.action = "other_action"
    question = "Which regular class am I enrolled in?"
    original_interpret = model.interpret_enquiry

    def interpret(context):
        result = original_interpret(context)
        result.questions = [question]
        return result

    def draft(context):
        snapshot = next(
            item["result"] for item in context["evidence"] if item["tool"] == "student_context"
        )
        enrolment = snapshot["enrolments"][0]
        reference = "enrolment:" + enrolment["id"]
        return Draft(
            body="You are enrolled in " + enrolment["class_name"] + ".",
            rationale="The supplied official enrolment is retained as evidence.",
            questions=[],
            references=[reference],
            answers=[
                EnquiryAnswer(
                    question=question,
                    status="answered",
                    answer=enrolment["class_name"],
                    references=[reference],
                )
            ],
        )

    model.interpret_enquiry = interpret
    model.choose_tools = lambda context, transcript: ToolTurn(calls=[], output=[])
    model.draft = draft
    run = start(rig, scenario)
    assert run["interpretation"]["flow"] == flow
    answer = run["draft_details"]["answers"][0]
    assert answer["status"] == "answered"
    assert answer["references"][0].startswith("enrolment:")
    assert "Monday Level 2" in run["draft_details"]["body"]
    assert run["evidence"][0]["tool"] == "student_context"
    assert run["draft_details"]["references"] == answer["references"]


@pytest.mark.parametrize("flow", ["enquiry", "teacher_handoff"])
def test_successive_revisions_retain_teacher_facts_and_latest_corrections(rig, scenario, flow):
    client, model, _, _ = rig
    captured = configure_enquiry(model)
    if flow == "teacher_handoff":
        model.routing.action = "other_action"
    original = model.draft

    def draft(context):
        result = original(context)
        feedback = context.get("teacher_feedback", "")
        amount = "$30" if "$30" in feedback else "$25" if "$25" in feedback else None
        if amount:
            result.answers[2] = EnquiryAnswer(
                question=QUESTIONS[2],
                status="answered",
                answer=f"The confirmed fee is {amount}.",
                references=["teacher_feedback"],
            )
            result.body = f"The Monday class is at 6 pm. The confirmed fee is {amount}."
        return result

    model.draft = draft
    run = start(rig, scenario)
    question_id = run["draft_details"]["answers"][2]["question_id"]
    fee_answer = {
        "question_id": question_id,
        "decision": "answer",
        "answer": "The confirmed fee is $25.",
    }
    first = review(
        client,
        run,
        "revise",
        feedback="The confirmed fee is $25.",
        question_resolutions=[fee_answer],
    ).json()
    second = review(client, first, "revise", feedback="Make the wording warmer.").json()
    assert second["status"] == "awaiting_review", second
    assert second["draft_details"]["answers"][2]["status"] == "answered"
    assert "$25" in second["draft_details"]["body"]
    assert "$25" in captured["interpretations"][-1]["teacher_feedback"]
    assert "warmer" in captured["drafts"][-1]["teacher_feedback"]
    evidence = next(item for item in second["evidence"] if item["tool"] == "teacher_feedback")
    assert "$25" in evidence["result"]["text"]
    assert "warmer" in evidence["result"]["text"]
    corrected = review(
        client,
        second,
        "revise",
        feedback="Correction: the fee is $30.",
        question_resolutions=[{**fee_answer, "answer": "The confirmed fee is $30."}],
    ).json()
    assert corrected["status"] == "awaiting_review", corrected
    assert "$30" in corrected["draft_details"]["body"]
    assert captured["drafts"][-1]["teacher_feedback"].endswith("Correction: the fee is $30.")
