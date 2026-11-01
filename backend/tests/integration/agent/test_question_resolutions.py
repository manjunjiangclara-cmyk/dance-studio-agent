"""Missing studio facts require applied teacher decisions before approval."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.administration.service import AdministrationError
from studio_copilot.agent.contracts import (
    Draft,
    EnquiryAnswer,
    EnquiryInterpretation,
    ModelError,
    Review,
)
from studio_copilot.agent.persistence.checkpoints import postgres_checkpointer
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.service import AgentService
from studio_copilot.agent.workflow.graph import Workflow
from studio_copilot.persistence.models import AgentRun, Message

from .helpers import FakeModel, review, start
from .test_enquiry import QUESTIONS, business_records, configure_enquiry

pytestmark = pytest.mark.integration

CLOTHING = "What should I wear?"


def configure_clothing(model):
    captured = configure_enquiry(model)

    def interpret(context):
        captured["interpretations"].append(context)
        return EnquiryInterpretation(
            request_summary="Clothing requirements",
            missing_details=[],
            enduring_preferences=[],
            questions=[CLOTHING],
            requested_actions=[],
        )

    def draft(context):
        captured["drafts"].append(context)
        if model.fail_draft:
            raise ModelError("Synthetic drafting failure")
        return Draft(
            body="I will check the clothing requirements and get back to you.",
            rationale="The studio has supplied no clothing rules.",
            questions=[],
            references=[],
            answers=[
                EnquiryAnswer(
                    question=CLOTHING,
                    status="needs_teacher",
                    answer="The clothing requirements need checking.",
                    references=[],
                )
            ],
        )

    model.interpret_enquiry = interpret
    model.draft = draft
    return captured


def choice(
    run,
    decision="answer",
    answer="Comfortable clothes and soft shoes are suitable.",
    question=CLOTHING,
):
    question_id = next(
        item["question_id"]
        for item in run["draft_details"]["answers"]
        if item["question"] == question
    )
    return {
        "question_id": question_id,
        "decision": decision,
        "answer": answer if decision == "answer" else None,
    }


def response_count(engine):
    with Session(engine) as db:
        return db.scalar(
            select(func.count()).select_from(Message).where(Message.kind == "teacher_response")
        )


def test_unresolved_fact_blocks_api_and_transactional_approval(rig, scenario, db_engine):
    client, model, _, _ = rig
    configure_clothing(model)
    before = business_records(db_engine)
    run = start(rig, scenario)
    answer = run["draft_details"]["answers"][0]
    assert UUID(answer["question_id"])
    assert run["interpretation"]["question_ids"][CLOTHING] == answer["question_id"]
    blocked = review(client, run, "approve", body="I manually typed an answer.")
    assert blocked.status_code == 409, blocked.text
    with pytest.raises(AdministrationError) as error:
        WorkflowStore(db_engine).approve(run["id"], "Bypass the API guard")
    assert "teacher" in str(error.value).lower() or "question" in str(error.value).lower()
    assert response_count(db_engine) == 0
    assert business_records(db_engine) == before
    assert client.get(f"/api/v1/agent-runs/{run['id']}").json()["status"] == "awaiting_review"


@pytest.mark.parametrize("decision", ["answer", "defer"])
def test_teacher_choice_is_applied_even_when_model_ignores_it(rig, scenario, db_engine, decision):
    client, model, _, _ = rig
    configure_clothing(model)
    before = business_records(db_engine)
    run = start(rig, scenario)
    selected = choice(run, decision)
    response = review(client, run, "revise", question_resolutions=[selected])
    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["revision"] == run["revision"] + 1
    answer = revised["draft_details"]["answers"][0]
    assert answer["question_id"] == selected["question_id"]
    assert revised["draft_details"]["question_resolutions"] == [selected]
    if decision == "answer":
        assert answer["status"] == "answered"
        assert selected["answer"] in revised["draft_details"]["body"]
        reference = "teacher_answer:" + selected["question_id"]
        assert reference in answer["references"]
        assert any(
            reference in item["result"].get("references", []) for item in revised["evidence"]
        )
    else:
        assert answer["status"] == "needs_teacher"
        assert (
            "confirm" in revised["draft_details"]["body"].lower()
            or "check" in revised["draft_details"]["body"].lower()
        )
    approved = review(client, revised, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    repeated = review(client, revised, "approve")
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["approved_response_id"] == approved.json()["approved_response_id"]
    assert response_count(db_engine) == 1
    assert business_records(db_engine) == before


def test_teacher_answer_and_question_are_sent_to_agent_for_new_draft(rig, scenario):
    client, model, _, _ = rig
    captured = configure_clothing(model)
    run = start(rig, scenario)
    selected = choice(run)

    response = review(client, run, "revise", question_resolutions=[selected])

    assert response.status_code == 200, response.text
    revised = response.json()
    assert len(captured["drafts"]) == 2
    assert captured["drafts"][-1]["question_resolutions"] == [{**selected, "question": CLOTHING}]
    assert revised["revision"] == run["revision"] + 1
    assert revised["status"] == "awaiting_review"
    assert selected["answer"] in revised["draft_details"]["body"]
    assert revised["draft_details"]["body"] != run["draft_details"]["body"]


def test_mixed_known_and_unknown_questions_need_only_teacher_fact_resolved(rig, scenario):
    client, model, _, _ = rig
    configure_enquiry(model)
    run = start(rig, scenario)
    selected = choice(run, question=QUESTIONS[2], answer="A trial costs $25.")
    revised = review(client, run, "revise", question_resolutions=[selected]).json()
    assert revised["status"] == "awaiting_review", revised
    assert [item["status"] for item in revised["draft_details"]["answers"]] == [
        "answered",
        "needs_student",
        "answered",
    ]
    assert "6 pm" in revised["draft_details"]["body"]
    assert "$25" in revised["draft_details"]["body"]
    assert review(client, revised, "approve").status_code == 200


def test_unresolved_requirement_survives_model_relabelling_on_freeform_revision(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    run = start(rig, scenario)

    def invented(context):
        reference = next(
            item["result"]["references"][0]
            for item in context["evidence"]
            if item["tool"] == "get_timetable"
        )
        return Draft(
            body="You must wear a pink leotard.",
            rationale="A model citation does not replace an explicit teacher decision.",
            questions=[],
            references=[reference],
            answers=[
                EnquiryAnswer(
                    question=CLOTHING,
                    status="answered",
                    answer="You must wear a pink leotard.",
                    references=[reference],
                )
            ],
        )

    model.draft = invented
    revised_response = review(client, run, "revise", feedback="Make the reply warmer.")
    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()
    assert review(client, revised, "approve").status_code == 409
    deferred = review(client, revised, "revise", question_resolutions=[choice(revised, "defer")])
    assert deferred.status_code == 200, deferred.text
    assert "pink leotard" not in deferred.json()["draft_details"]["body"]
    assert review(client, deferred.json(), "approve").status_code == 200


def test_stable_question_identity_and_teacher_corrections_survive_revisions(rig, scenario):
    client, model, _, _ = rig
    configure_enquiry(model)
    run = start(rig, scenario)
    selected = choice(run, question=QUESTIONS[2], answer="A trial costs $25.")
    first = review(client, run, "revise", question_resolutions=[selected]).json()
    interpretation = model.interpret_enquiry

    def reordered(context):
        parsed = interpretation(context)
        parsed.questions = [QUESTIONS[2], QUESTIONS[0]]
        return parsed

    model.interpret_enquiry = reordered
    second = review(client, first, "revise", feedback="Make the reply warmer.").json()
    assert second["status"] == "awaiting_review", second
    assert second["interpretation"]["questions"] == QUESTIONS
    assert second["interpretation"]["question_ids"] == run["interpretation"]["question_ids"]
    assert "$25" in second["draft_details"]["body"]
    corrected_choice = {**selected, "answer": "Correction: a trial costs $30."}
    corrected = review(client, second, "revise", question_resolutions=[corrected_choice]).json()
    assert corrected["status"] == "awaiting_review", corrected
    assert "$30" in corrected["draft_details"]["body"]
    assert "$25" not in corrected["draft_details"]["body"]
    assert corrected["draft_details"]["question_resolutions"] == [corrected_choice]


def test_revision_recovers_omitted_question_and_retains_teacher_decision(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    run = start(rig, scenario)
    selected = choice(run)
    first = review(client, run, "revise", question_resolutions=[selected]).json()
    interpretation = model.interpret_enquiry
    recovered = "Are special shoes required?"

    def add_missing_question(context):
        parsed = interpretation(context)
        parsed.questions.append(recovered)
        return parsed

    model.interpret_enquiry = add_missing_question
    response = review(client, first, "revise", feedback="Also address my question about shoes.")
    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["interpretation"]["questions"] == [CLOTHING, recovered]
    assert revised["interpretation"]["question_ids"][CLOTHING] == selected["question_id"]
    assert revised["draft_details"]["question_resolutions"] == [selected]
    answers = {item["question"]: item for item in revised["draft_details"]["answers"]}
    assert answers[CLOTHING]["answer"] == selected["answer"]
    assert answers[recovered]["status"] == "needs_teacher"
    assert review(client, revised, "approve").status_code == 409
    deferred = review(
        client,
        revised,
        "revise",
        question_resolutions=[choice(revised, "defer", question=recovered)],
    )
    assert deferred.status_code == 200, deferred.text
    assert review(client, deferred.json(), "approve").status_code == 200


def test_failed_revision_extraction_blocks_approval_until_successful_retry(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    run = start(rig, scenario)
    selected = choice(run)
    first = review(client, run, "revise", question_resolutions=[selected]).json()

    def unavailable(context):
        raise ModelError("Synthetic extraction failure")

    interpret = model.interpret_enquiry
    model.interpret_enquiry = unavailable
    response = review(client, first, "revise", feedback="Make the reply warmer.")
    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["status"] == "failed"
    assert "could not be interpreted" in revised["error"]
    assert revised["interpretation"]["questions"] == [CLOTHING]
    assert revised["interpretation"]["question_ids"] == first["interpretation"]["question_ids"]
    assert revised["draft_details"]["question_resolutions"] == [selected]
    assert revised["draft_details"]["answers"][0]["answer"] == selected["answer"]
    assert review(client, revised, "approve").status_code == 409
    model.interpret_enquiry = interpret
    retried = client.post(f"/api/v1/agent-runs/{run['id']}/retry").json()
    assert retried["status"] == "awaiting_review"
    assert retried["interpretation"]["questions"] == [CLOTHING]
    assert retried["draft_details"]["question_resolutions"] == [selected]


def test_overflow_cannot_retry_and_discard_the_recovered_question(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    interpret = model.interpret_enquiry
    questions = [f"What is requirement {index}?" for index in range(20)]
    overflow = False

    def extract(context):
        parsed = interpret(context)
        parsed.questions = ["One more question?"] if overflow else questions
        return parsed

    model.interpret_enquiry = extract
    run = start(rig, scenario)
    overflow = True
    failed = review(client, run, "revise", feedback="Check for omitted questions.").json()
    assert failed["status"] == "failed"
    assert "20 questions" in failed["error"]
    assert failed["draft_details"]["failure_code"] == "question_limit_exceeded"
    assert failed["interpretation"]["questions"] == questions
    assert review(client, failed, "approve").status_code == 409

    overflow = False
    retried = client.post(f"/api/v1/agent-runs/{run['id']}/retry")
    assert retried.status_code == 409
    saved = client.get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["status"] == "failed"
    assert saved["draft_details"]["failure_code"] == "question_limit_exceeded"


def test_persistent_overflow_can_be_closed_without_response_or_business_writes(
    rig, scenario, db_engine
):
    client, model, _, _ = rig
    configure_clothing(model)
    interpret = model.interpret_enquiry
    questions = [f"What is requirement {index}?" for index in range(20)]
    overflow = False

    def extract(context):
        parsed = interpret(context)
        parsed.questions = ["One more question?"] if overflow else questions
        return parsed

    model.interpret_enquiry = extract
    before = business_records(db_engine)
    run = start(rig, scenario)
    overflow = True
    failed = review(client, run, "revise", feedback="Check for omitted questions.").json()
    assert failed["status"] == "failed"
    assert client.post(f"/api/v1/agent-runs/{run['id']}/retry").status_code == 409
    stale = review(client, {**failed, "revision": failed["revision"] + 1}, "reject")
    assert stale.status_code == 409
    closed = review(client, failed, "reject")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert response_count(db_engine) == 0
    assert business_records(db_engine) == before


def test_multiple_questions_can_be_resolved_and_replaced_across_revisions(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    second_question = "Are special shoes required?"
    interpret = model.interpret_enquiry

    def two_questions(context):
        parsed = interpret(context)
        parsed.questions = [CLOTHING, second_question]
        return parsed

    model.interpret_enquiry = two_questions
    run = start(rig, scenario)
    first_choice = choice(run, decision="defer")
    first_response = review(client, run, "revise", question_resolutions=[first_choice])
    assert first_response.status_code == 200, first_response.text
    first = first_response.json()
    assert review(client, first, "approve").status_code == 409

    second_choice = choice(first, decision="defer", question=second_question)
    second_response = review(client, first, "revise", question_resolutions=[second_choice])
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()
    decisions = {
        item["question_id"]: item for item in second["draft_details"]["question_resolutions"]
    }
    assert decisions == {
        first_choice["question_id"]: first_choice,
        second_choice["question_id"]: second_choice,
    }

    replacement = choice(second, answer="Comfortable clothes are suitable.")
    third_response = review(client, second, "revise", question_resolutions=[replacement])
    assert third_response.status_code == 200, third_response.text
    third = third_response.json()
    decisions = {
        item["question_id"]: item for item in third["draft_details"]["question_resolutions"]
    }
    assert decisions == {
        replacement["question_id"]: replacement,
        second_choice["question_id"]: second_choice,
    }
    answers = {item["question"]: item for item in third["draft_details"]["answers"]}
    assert answers[CLOTHING]["status"] == "answered"
    assert answers[CLOTHING]["answer"] == replacement["answer"]
    assert answers[second_question]["status"] == "needs_teacher"
    assert replacement["answer"] in third["draft_details"]["body"]
    assert second_question in third["draft_details"]["body"]
    assert review(client, third, "approve").status_code == 200


@pytest.mark.parametrize("invalid", ["unknown", "answered", "needs_student"])
def test_resolution_cannot_attach_to_an_unrelated_or_inapplicable_question(rig, scenario, invalid):
    client, model, _, _ = rig
    configure_enquiry(model)
    run = start(rig, scenario)
    question = QUESTIONS[0] if invalid == "answered" else QUESTIONS[1]
    selected = choice(run, question=question)
    if invalid == "unknown":
        selected["question_id"] = str(uuid4())
    result = review(client, run, "revise", question_resolutions=[selected])
    assert result.status_code in {409, 422}, result.text
    saved = client.get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["revision"] == run["revision"]
    assert saved["status"] == "awaiting_review"
    assert saved["draft_details"] == run["draft_details"]


def test_stale_revision_cannot_apply_a_teacher_decision(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    run = start(rig, scenario)
    first = review(client, run, "revise", question_resolutions=[choice(run, "defer")]).json()
    stale = review(client, run, "revise", question_resolutions=[choice(run)])
    assert stale.status_code == 409
    saved = client.get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["revision"] == first["revision"]
    assert (
        saved["draft_details"]["question_resolutions"]
        == first["draft_details"]["question_resolutions"]
    )


def test_oversized_combined_answers_cannot_be_silently_truncated(rig, scenario):
    client, model, _, _ = rig
    configure_clothing(model)
    questions = [f"What is studio requirement {index}?" for index in range(6)]
    interpret = model.interpret_enquiry

    def multiple(context):
        parsed = interpret(context)
        parsed.questions = questions
        return parsed

    model.interpret_enquiry = multiple
    run = start(rig, scenario)
    decisions = [
        choice(run, question=question, answer=f"ANSWER_{index} " + "x" * 3900)
        for index, question in enumerate(questions)
    ]
    result = review(client, run, "revise", question_resolutions=decisions)
    assert result.status_code in {409, 422}, result.text
    saved = client.get(f"/api/v1/agent-runs/{run['id']}").json()
    assert saved["status"] == "awaiting_review"
    assert saved["revision"] == run["revision"]


def test_fresh_model_expansion_leaves_an_overlong_reply_reviewable(rig, scenario, db_engine):
    client, model, _, _ = rig
    configure_clothing(model)
    supported = [f"What time does studio class {index} start?" for index in range(5)]
    questions = [*supported, CLOTHING]
    interpret = model.interpret_enquiry
    expanded = False

    def multiple(context):
        parsed = interpret(context)
        parsed.questions = questions
        return parsed

    def draft(context):
        timetable = next(
            item["result"] for item in context["evidence"] if item["tool"] == "get_timetable"
        )
        reference = "class:" + timetable["items"][0]["id"]
        answer = "The class starts at 6 pm."
        if expanded:
            answer += " " + "x" * (3900 - len(answer) - 1)
        return Draft(
            body="The classes start at 6 pm; I will check the clothing rules.",
            rationale="Timetable answers are supported; clothing needs teacher input.",
            questions=[],
            references=[reference],
            answers=[
                *[
                    EnquiryAnswer(
                        question=question,
                        status="answered",
                        answer=answer,
                        references=[reference],
                    )
                    for question in supported
                ],
                EnquiryAnswer(
                    question=CLOTHING,
                    status="needs_teacher",
                    answer="The teacher needs to confirm the clothing rules.",
                    references=[],
                ),
            ],
        )

    model.interpret_enquiry = multiple
    model.draft = draft
    before = business_records(db_engine)
    run = start(rig, scenario)
    teacher_answer = "Wear comfortable clothes. " + "y" * 1000
    selected = choice(run, answer=teacher_answer)
    expanded = True
    response = review(client, run, "revise", question_resolutions=[selected])
    assert response.status_code == 200, response.text
    revised = response.json()
    assert revised["status"] == "awaiting_review", revised
    assert revised["revision"] == run["revision"] + 1
    assert teacher_answer in revised["draft_details"]["body"]
    assert len(revised["draft_details"]["body"]) <= 20_000
    clothing = next(
        answer for answer in revised["draft_details"]["answers"] if answer["question"] == CLOTHING
    )
    assert clothing["status"] == "answered"
    assert clothing["answer"] == teacher_answer
    assert revised["draft_details"]["question_resolutions"] == [selected]
    flagged = [
        answer
        for answer in revised["draft_details"]["answers"]
        if answer["status"] == "needs_teacher"
    ]
    assert flagged
    assert all(answer["question"] in supported for answer in flagged)
    assert all(
        answer["question_id"] in revised["draft_details"]["required_question_ids"]
        for answer in flagged
    )
    assert review(client, revised, "approve").status_code == 409
    with pytest.raises(AdministrationError) as error:
        WorkflowStore(db_engine).approve(run["id"], None)
    assert error.value.status == 409
    assert response_count(db_engine) == 0

    shortened = [
        choice(revised, question=answer["question"], answer="The class starts at 6 pm.")
        for answer in flagged
    ]
    updated_response = review(client, revised, "revise", question_resolutions=shortened)
    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert updated["status"] == "awaiting_review", updated
    assert teacher_answer in updated["draft_details"]["body"]
    assert len(updated["draft_details"]["body"]) <= 20_000
    assert review(client, updated, "approve").status_code == 200
    assert response_count(db_engine) == 1
    assert business_records(db_engine) == before


def test_model_failure_still_applies_teacher_answer_and_approval_recovers_once(
    rig, scenario, db_engine
):
    client, model, _, _ = rig
    configure_clothing(model)
    run = start(rig, scenario)
    selected = choice(run)
    model.fail_draft = True
    revised = review(client, run, "revise", question_resolutions=[selected]).json()
    assert revised["status"] == "awaiting_review", revised
    assert selected["answer"] in revised["draft_details"]["body"]
    model.fail_reconcile = True
    failed = review(client, revised, "approve").json()
    assert failed["status"] == "failed", failed
    assert failed["approved_response_id"]
    assert review(client, failed, "reject").status_code == 409
    model.fail_reconcile = False
    retried = client.post(f"/api/v1/agent-runs/{run['id']}/retry").json()
    assert retried["status"] == "approved", retried
    assert retried["approved_response_id"] == failed["approved_response_id"]
    assert response_count(db_engine) == 1


def test_legacy_missing_ids_requires_regeneration_before_question_controls(
    rig, scenario, db_engine
):
    client, model, _, saver = rig
    configure_clothing(model)
    run = start(rig, scenario)
    graph = Workflow(db_engine, model).compile(saver)
    config = {"configurable": {"thread_id": run["id"]}}
    state = graph.get_state(config).values
    interpretation = {
        key: value for key, value in state["interpretation"].items() if key != "question_ids"
    }
    draft = {
        **state["draft"],
        "answers": [
            {key: value for key, value in item.items() if key != "question_id"}
            for item in state["draft"]["answers"]
        ],
    }
    graph.update_state(
        config, {"interpretation": interpretation, "draft": draft}, as_node="persist_draft"
    )
    with Session(db_engine) as db, db.begin():
        saved = db.get(AgentRun, UUID(run["id"]))
        saved.interpretation = {
            key: value for key, value in saved.interpretation.items() if key != "question_ids"
        }
        saved.draft_details = {**saved.draft_details, "answers": draft["answers"]}
    assert review(client, run, "approve").status_code == 409
    bad_choice = review(client, run, "revise", question_resolutions=[choice(run)])
    assert bad_choice.status_code in {409, 422}, bad_choice.text
    regenerated = review(client, run, "revise", feedback="Regenerate the question checklist.")
    assert regenerated.status_code == 200, regenerated.text
    updated = regenerated.json()
    assert updated["draft_details"]["answers"][0]["question_id"]
    applied = review(client, updated, "revise", question_resolutions=[choice(updated, "defer")])
    assert applied.status_code == 200, applied.text
    assert review(client, applied.json(), "approve").status_code == 200


@pytest.mark.parametrize("decision", ["answer", "defer"])
def test_postgres_checkpoint_retains_teacher_decision_after_service_restart(
    db_engine, scenario, decision
):
    with postgres_checkpointer(db_engine) as saver:
        saver.setup()
    model = FakeModel()
    configure_clothing(model)
    before = business_records(db_engine)
    service = AgentService(db_engine, model)
    run = service.start(scenario["conversation"], scenario["source"])
    assert run.status == "awaiting_review", run.error
    selected = choice({"draft_details": run.draft_details}, decision)
    applied = service.review(
        run.id,
        Review(action="revise", expected_revision=run.revision, question_resolutions=[selected]),
    )
    assert applied.status == "awaiting_review", applied.error

    # New model, service, graph and database connections must recover the applied
    # decision from PostgreSQL rather than process-local state or model memory.
    fresh_model = FakeModel()
    configure_clothing(fresh_model)
    fresh = AgentService(db_engine, fresh_model)
    revised = fresh.review(
        run.id,
        Review(action="revise", expected_revision=applied.revision, feedback="Make it warmer."),
    )
    assert revised.status == "awaiting_review", revised.error
    assert revised.revision == applied.revision + 1
    assert revised.draft_details["question_resolutions"] == [selected]
    answer = revised.draft_details["answers"][0]
    assert answer["question_id"] == selected["question_id"]
    assert answer["status"] == ("answered" if decision == "answer" else "needs_teacher")
    evidence = next(
        item for item in revised.evidence if item["tool"] == "teacher_question_resolutions"
    )
    assert evidence["result"]["items"] == [selected]
    assert answer["references"][0] in evidence["result"]["references"]
    if decision == "answer":
        assert selected["answer"] in revised.draft_details["body"]
    else:
        assert "confirm" in revised.draft_details["body"]
    approved = fresh.review(run.id, Review(action="approve", expected_revision=revised.revision))
    assert approved.status == "approved", approved.error
    assert response_count(db_engine) == 1
    assert business_records(db_engine) == before
