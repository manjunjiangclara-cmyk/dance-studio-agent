"""Workflow steps: model decisions and state updates, with persistence delegated to the store."""

import logging
import re
from datetime import datetime

from langgraph.types import interrupt
from pydantic import ValidationError

from studio_copilot.administration.service import conflict
from studio_copilot.agent.contracts import (
    DocumentEmailComposition,
    Draft,
    EnquiryInterpretation,
    MakeupInterpretation,
    Model,
    ModelError,
    Review,
    Routing,
    State,
)
from studio_copilot.agent.document_answers import (
    EVIDENCE_MARKER,
    document_draft,
    document_safe_body,
)
from studio_copilot.agent.enquiry import safe_body, validate_answers
from studio_copilot.agent.makeup import clarification_body, validated_candidate_ids
from studio_copilot.agent.persistence.store import WorkflowStore
from studio_copilot.agent.privacy import normalize_unknown_greeting
from studio_copilot.agent.proposals import confirmation_body
from studio_copilot.agent.question_resolutions import (
    RevisionExtractionError,
    deferral_text,
    identify_questions,
    merge_resolutions,
    resolved_question_context,
    validate_resolution_update,
)
from studio_copilot.agent.workflow.queries import QueryRunner

logger = logging.getLogger(__name__)

SIGNATURE = re.compile(
    r"\n\s*(?:best(?: regards)?|kind regards|warm regards|warmly|sincerely|thanks),?"
    r"(?:\s*\n\s*[^\n]*)?\s*$",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"\[(?:your name|teacher(?:'s)? name|studio name)\]", re.IGNORECASE)
PROMISE = re.compile(
    r"\b(?:I|we)(?:['’]ll| will)\s+(?:check|confirm|follow up|get back|look into|"
    r"email|write|reply|call|contact|reach out|let you know|send (?:you )?(?:an? )?update|"
    r"be in touch|ask (?:the )?office)",
    re.IGNORECASE,
)
NUMBER = re.compile(
    r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b"
)
TOPICS = ("refund", "offer", "deposit", "booking", "payment", "credit", "cancellation")
PERSONAL_RECORD = re.compile(
    r"\b(?:my|our|me|us)\b.*\b(?:booking|payment|balance|refund|attendance|credit|"
    r"enrolment|reservation|invoice)\b|"
    r"\b(?:booking|payment|balance|refund|attendance|credit|enrolment|reservation|invoice)"
    r"\b.*\b(?:my|our|me|us)\b",
    re.IGNORECASE,
)
LIVE_STATUS = re.compile(
    r"\b(?:receive[ds]?|arrive[ds]?|paid|booked|confirmed|approved|changed|"
    r"cancelled|processed|issued|current|status|recorded|active|gone through)\b",
    re.IGNORECASE,
)
POLICY_QUESTION = re.compile(
    r"\b(?:policy|rule|deadline|notice|requirement|eligibility)\b",
    re.IGNORECASE,
)
EXPLICIT_RECORD_OUTCOME = re.compile(
    r"\b(?:receive[ds]?|arrive[ds]?|paid|booked|confirmed|approved|"
    r"processed|issued|recorded|active|gone through)\b",
    re.IGNORECASE,
)
INFORMATION_REQUEST = re.compile(
    r"^\s*(?:explain|state|identify|compare|determine|decide|choose|describe|summarise|"
    r"summarize|tell me which)\b",
    re.IGNORECASE,
)
PERSONAL_OUTCOME_CLAIM = re.compile(
    r"\b(?:your|my|our|this|their)\s+(?:booking|payment|refund|balance|credit|"
    r"reservation|invoice|enrolment|attendance|record|account|status)\b|"
    r"\b(?:you|we|I)(?:'ve|\s+(?:have|had|already|will))\s+"
    r"(?:paid|booked|confirmed|approved|received|cancelled|processed|issued|changed)\b",
    re.IGNORECASE,
)
AMBIGUOUS_ALTERNATIVE_DEADLINE = re.compile(
    r"\beither\b[^.!?]{0,180}\bor\b[^.!?]{0,180}\bwithin\s+"
    r"(?:\w+\s+){0,3}(?:days?|hours?|weeks?)\b",
    re.IGNORECASE,
)


def _live_record_question(question: str) -> bool:
    if not (PERSONAL_RECORD.search(question) and LIVE_STATUS.search(question)):
        return False
    # A policy about a personal booking/payment is still a document question.
    # A stated record outcome remains live even when the student mentions policy.
    return not POLICY_QUESTION.search(question) or bool(EXPLICIT_RECORD_OUTCOME.search(question))


def _claim_references(claim: dict, answer_references: list[str]) -> list[str]:
    citations = [
        "document:" + str(citation["evidence_id"])
        for citation in claim.get("citations", [])
        if isinstance(citation, dict) and citation.get("evidence_id")
    ]
    return list(dict.fromkeys(citations)) if citations else answer_references


def _ambiguous_deadline_quote(claim: dict) -> str:
    for citation in claim.get("citations", []):
        quote = citation.get("quote", "")
        for sentence in re.split(r"(?<=[.!?])\s+", quote):
            if len(sentence) <= 1000 and AMBIGUOUS_ALTERNATIVE_DEADLINE.search(sentence):
                return sentence.strip()
    return ""


def _safe_general_process_quote(claim: dict) -> str:
    """Keep only a cited, complete process rule for a live-record handoff."""
    for citation in claim.get("citations", []):
        for sentence in re.split(r"(?<=[.!?])\s+", citation.get("quote", "")):
            sentence = sentence.strip()
            if not sentence or len(sentence) > 300:
                continue
            parts = re.split(r",?\s+but\s+|;\s+", sentence, maxsplit=1)
            if len(parts) == 2:
                # A following condition belongs to the rule. Only an explicit
                # source-scope disclaimer can be omitted from a process quote.
                if not re.match(
                    r"(?:this (?:guide|document|page|policy) does not (?:show|record|confirm)\b)",
                    parts[1].strip(),
                    re.IGNORECASE,
                ):
                    continue
                sentence = parts[0].strip()
            if (
                not PERSONAL_OUTCOME_CLAIM.search(sentence)
                and not re.search(r"\b(?:your|my|our|their|we|I)\b", sentence, re.IGNORECASE)
                and re.search(r"\b(?:may|can|must|should)\b", sentence, re.IGNORECASE)
                and re.search(
                    r"\b(?:request(?:ed)?|provid(?:e|ed)|submit(?:ted)?|ask|contact|send|obtain)\b",
                    sentence,
                    re.IGNORECASE,
                )
            ):
                return sentence.rstrip(".") + "."
    return ""


def _same_process(left: str, right: str) -> bool:
    def terms(value: str) -> set[str]:
        value = re.sub(r"\brequest(?:ed|ing|s)?\b", "request", value.lower())
        return set(re.findall(r"\b[a-z0-9]+\b", value)) - {
            "a",
            "an",
            "be",
            "by",
            "can",
            "from",
            "is",
            "may",
            "of",
            "the",
            "to",
            "you",
        }

    a, b = terms(left), terms(right)
    return bool(a and b and len(a & b) / len(a | b) >= 0.8)


def _unsigned_email(body: str, *, has_signature: bool) -> tuple[str, bool]:
    if has_signature:
        return body, False
    cleaned = SIGNATURE.sub("", body).rstrip()
    cleaned = PLACEHOLDER.sub("", cleaned).rstrip()
    return cleaned, cleaned != body


def _composition_concerns(body: str, facts: list[dict], *, deferred: bool) -> list[str]:
    concerns = []
    if not deferred and PROMISE.search(body):
        concerns.append("The draft promises a follow-up without an explicit teacher deferral.")
    for fact in facts:
        if any(
            AMBIGUOUS_ALTERNATIVE_DEADLINE.search(quote) for quote in fact.get("source_quotes", [])
        ):
            concerns.append(
                "The source lists alternative actions before one deadline; check which action "
                f"the timing qualifies for question {fact['question_id']}. Preserve the source "
                "wording until the teacher decides."
            )
        source = fact["text"].lower()
        source_topics = {topic for topic in TOPICS if topic in source}
        if not source_topics:
            continue
        for number in set(NUMBER.findall(source)):
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", body.lower()):
                if number not in NUMBER.findall(sentence):
                    continue
                draft_topics = {topic for topic in TOPICS if topic in sentence}
                if draft_topics and draft_topics.isdisjoint(source_topics):
                    span = re.search(rf"\b{re.escape(number)}\b(?:\s+\w+){{0,3}}", source)
                    phrase = span.group(0) if span else number
                    concerns.append(
                        f"Check that {phrase} remains attached to the documented "
                        f"{', '.join(sorted(source_topics))} condition "
                        f"for question {fact['question_id']}."
                    )
    return list(dict.fromkeys(concerns))


def _remove_unapproved_promises(body: str, deferred_questions: list[str]) -> tuple[str, bool]:
    """Keep only the teacher's explicit question-scoped deferral wording."""
    protected = {}
    for index, question in enumerate(deferred_questions):
        wording = deferral_text(question)
        marker = f"__approved_deferral_{index}__."
        if wording in body:
            protected[marker] = wording
            body = body.replace(wording, marker)
    pieces = re.split(r"(?<=[.!?])(\s+)", body)
    retained = []
    removed = False
    for index in range(0, len(pieces), 2):
        sentence = pieces[index]
        if PROMISE.search(sentence):
            removed = True
            continue
        separator = pieces[index - 1] if index and retained else ""
        retained.append(separator + sentence)
    body = "".join(retained)
    for marker, wording in protected.items():
        body = body.replace(marker, wording)
    return body.strip(), removed


def select_flow(routing: Routing) -> str:
    """Business actions select the workflow; topic labels alone never authorize a booking."""
    intents = set(routing.intents)
    if routing.action == "information_only":
        return "enquiry"
    if (
        routing.action == "makeup_booking"
        and "makeup" in intents
        and intents <= {"makeup", "absence"}
    ):
        return "makeup"
    return "teacher_handoff"


def _fallback_draft(state: State) -> Draft:
    if state.get("flow", "makeup") != "makeup":
        return Draft(
            body="Thanks for your message. I'll review your enquiry and get back to you.",
            rationale=state["routing"]["reason"] + " The model was unavailable.",
            questions=state["warnings"],
            references=[],
        )
    return Draft(
        body=(
            "Thank you for your message. Could you confirm the class date you will miss "
            "and your preferred makeup dates and location? "
            "I'll check the options for you."
        ),
        rationale="The model was unavailable. This template makes no eligibility promises.",
        questions=state["warnings"],
        references=[],
    )


def _validate_references(draft: Draft, state: State) -> Draft:
    references = {"policy:" + state["context"]["policy"]["version"]}
    for item in state["evidence"]:
        references.update(item["result"].get("references", []))
    if state.get("feedback", "").strip():
        references.add("teacher_feedback")
    if any(reference not in references for reference in draft.references):
        draft.references = [reference for reference in draft.references if reference in references]
        draft.rationale += " Unsupported model references were removed; verify the draft's claims."
    return draft


def _validate_booking_proposal(draft: Draft, state: State) -> Draft:
    if any(
        item.get("tool") == "validate_makeup_candidates"
        and item.get("result", {}).get("options_requested")
        for item in state.get("evidence", [])
    ):
        draft.booking_session_id = None
    if draft.booking_session_id is None:
        if state.get("flow", state.get("context", {}).get("flow")) == "makeup":
            draft.body = clarification_body(state.get("evidence", []))
        return draft
    if state.get(
        "flow", state.get("context", {}).get("flow")
    ) != "makeup" or draft.booking_session_id not in validated_candidate_ids(
        state.get("evidence", [])
    ):
        draft.booking_session_id = None
        draft.body = (
            clarification_body(state.get("evidence", []))
            if state.get("flow", state.get("context", {}).get("flow")) == "makeup"
            else safe_body(
                draft.answers,
                state.get("interpretation", {}).get("requested_actions", []),
                draft.question_resolutions,
            )
        )
        draft.rationale += " Unsupported booking proposal removed; teacher clarification is needed."
    else:
        candidates = [
            item
            for evidence in state.get("evidence", [])
            if evidence.get("tool") == "search_sessions"
            for item in evidence.get("result", {}).get("items", [])
            if item.get("id") == str(draft.booking_session_id)
        ]
        item = candidates[-1] if candidates else {}
        try:
            start = datetime.fromisoformat(item["starts_at"])
            draft.body = confirmation_body(item["class_name"], item["location_name"], start)
        except (KeyError, TypeError, ValueError):
            draft.booking_session_id = None
            draft.body = "We need to verify the session details before arranging your makeup."
            return draft
    return draft


class WorkflowNodes:
    def __init__(self, store: WorkflowStore, model: Model):
        self.store, self.model = store, model
        self.queries = QueryRunner(store.engine, model)

    def load(self, state: State) -> dict:
        return {"attempt": 1, "feedback": "", "context": self.store.load_context(state["run_id"])}

    def route(self, state: State) -> dict:
        try:
            routing = self.model.route(state["context"])
        except ModelError:
            routing = Routing(
                intents=["unknown"],
                request_summary="Student enquiry needs teacher assessment.",
                needs_clarification=True,
                reason="The routing model was unavailable.",
            )
        flow, result = select_flow(routing), routing.model_dump()
        self.store.save_routing(state["run_id"], result, flow)
        logger.info(
            "agent_routed",
            extra={
                "run_id": state["run_id"],
                "intents": routing.intents,
                "flow": flow,
                "needs_clarification": routing.needs_clarification,
                "action": routing.action,
            },
        )
        return {
            "routing": result,
            "flow": flow,
            "context": {**state["context"], "routing": result, "flow": flow},
        }

    def interpret(self, state: State) -> dict:
        """Makeup-specific extraction, reached only after routing."""
        return {
            "interpretation": self.model.interpret_makeup(state["context"]).model_dump(mode="json")
        }

    def _enquiry_interpretation(self, state: State, feedback: str = "") -> EnquiryInterpretation:
        try:
            parsed = self.model.interpret_enquiry(
                {
                    **state["context"],
                    "previous_interpretation": state.get("interpretation", {}),
                    "teacher_feedback": feedback,
                }
            )
        except (ModelError, ValidationError) as error:
            if state.get("interpretation"):
                raise RevisionExtractionError(
                    "The revised enquiry could not be interpreted."
                ) from error
            parsed = EnquiryInterpretation(
                request_summary=state["routing"]["request_summary"],
                missing_details=["The enquiry could not be interpreted; teacher review is needed."],
                enduring_preferences=[],
                questions=[state["context"]["source"]["body"][:2000]],
                requested_actions=(
                    [state["routing"]["request_summary"]]
                    if state["routing"].get("action", "unclear") != "information_only"
                    else []
                ),
            )
        if not parsed.requested_actions and state["routing"].get("action") in {
            "other_action",
            "unclear",
        }:
            parsed.requested_actions = [state["routing"]["request_summary"]]
        if state["routing"].get("action") == "information_only":
            # A request to explain or compare policies is a question, even when
            # the extractor puts its imperative wording in requested_actions.
            information_requests = [
                action for action in parsed.requested_actions if INFORMATION_REQUEST.match(action)
            ]
            parsed.questions = list(dict.fromkeys([*parsed.questions, *information_requests]))
            parsed.requested_actions = [
                action for action in parsed.requested_actions if action not in information_requests
            ]
            if not parsed.questions:
                parsed.questions = [state["context"]["source"]["body"][:2000]]
        return parsed

    def interpret_general(self, state: State) -> dict:
        parsed = self._enquiry_interpretation(state)
        identify_questions(parsed, state["run_id"], {})
        return {"interpretation": parsed.model_dump(mode="json")}

    def remember_student(self, state: State) -> dict:
        flow = state.get("flow", "makeup")
        schema = MakeupInterpretation if flow == "makeup" else EnquiryInterpretation
        interpretation = schema.model_validate(state["interpretation"])
        self.store.remember_student(state["run_id"], interpretation, state.get("routing", {}), flow)
        logger.info("student_memory_updated", extra={"run_id": state["run_id"]})
        return {}

    def gather(self, state: State) -> dict:
        return self.queries.gather(state)

    def draft(self, state: State) -> dict:
        context = {
            **state["context"],
            "interpretation": state["interpretation"],
            "evidence": state["evidence"],
            "warnings": state["warnings"],
            "teacher_feedback": state.get("feedback", ""),
            "question_resolutions": resolved_question_context(
                state["interpretation"], state.get("question_resolutions", [])
            ),
        }
        try:
            draft = document_draft(state)
            document_mode = draft is not None
            if draft is None:
                draft = self.model.draft(context)
        except ModelError:
            draft = _fallback_draft(state)
            document_mode = False
        draft = _validate_booking_proposal(
            _validate_references(validate_answers(draft, state), state), state
        )
        if document_mode:
            results = {
                item["result"].get("question_id"): item["result"]
                for item in state.get("evidence", [])
                if item.get("tool") == "document_answer"
            }
            applied_ids = {
                str(item.get("question_id")) for item in state.get("question_resolutions", [])
            }
            live_state_questions = []
            safe_live_claims = {}
            for item in draft.answers:
                if item.question_id in applied_ids:
                    continue
                if results.get(item.question_id, {}).get(
                    "reason_code"
                ) == "requires_live_data" or _live_record_question(item.question):
                    live_state_questions.append(item.question)
                    item.status = "needs_teacher"
                    source_claims = results.get(item.question_id, {}).get("claims", [])
                    policy_claims = []
                    for claim in source_claims:
                        text = _safe_general_process_quote(claim)
                        if text and not any(
                            _same_process(text, prior["text"]) for prior in policy_claims
                        ):
                            policy_claims.append({**claim, "text": text})
                    safe_live_claims[item.question_id] = policy_claims
                    item.answer = (
                        "\n\n".join(claim["text"] for claim in policy_claims)
                        if policy_claims
                        else "The teacher needs to verify this before replying."
                    )
                    item.references = list(
                        dict.fromkeys(
                            ref for claim in policy_claims for ref in _claim_references(claim, [])
                        )
                    )
                    if item.question_id:
                        draft.required_question_ids.append(item.question_id)
                    if item.question not in draft.questions:
                        draft.questions.append(item.question)
            draft.required_question_ids = sorted(set(draft.required_question_ids))
            safe_claims = {}
            ambiguous_questions = []
            for item in draft.answers:
                claims = []
                for claim in safe_live_claims.get(
                    item.question_id, results.get(item.question_id, {}).get("claims", [])
                ):
                    quote = _ambiguous_deadline_quote(claim)
                    claims.append({**claim, "text": quote or claim.get("text", "")})
                safe_claims[item.question_id] = claims
                if any(_ambiguous_deadline_quote(claim) for claim in claims):
                    ambiguous_questions.append(item.question)
                    item.answer = "\n\n".join(claim["text"] for claim in claims if claim["text"])
                    item.status = "needs_teacher"
                    if item.question_id:
                        draft.required_question_ids.append(item.question_id)
                    if item.question not in draft.questions:
                        draft.questions.append(item.question)
            draft.required_question_ids = sorted(set(draft.required_question_ids))
            draft.references = list(
                dict.fromkeys(ref for item in draft.answers for ref in item.references)
            )
            facts = [
                {
                    "question_id": item.question_id,
                    "question": item.question,
                    "text": claim.get("text", ""),
                    "citations": _claim_references(claim, item.references),
                    "source_quotes": [
                        citation.get("quote", "")
                        for citation in claim.get("citations", [])
                        if citation.get("quote")
                    ],
                    "supported": True,
                    "answer_status": item.status,
                }
                for item in draft.answers
                if item.references and all(ref.startswith("document:") for ref in item.references)
                for claim in safe_claims.get(item.question_id, [])
                if claim.get("text")
                and (
                    item.question not in live_state_questions
                    or not PERSONAL_OUTCOME_CLAIM.search(claim["text"])
                )
            ]
            composition_context = {
                "student": state["context"].get("student", {}),
                "source": state["context"].get("source", {}),
                "original_request": state["context"].get("source", {}).get("body", ""),
                "facts": facts,
                "unresolved_actions": state["interpretation"].get("requested_actions", []),
                "live_state_questions": live_state_questions,
                "answers": [
                    {
                        "question_id": item.question_id,
                        "question": item.question,
                        "status": item.status,
                        "answer": item.answer,
                        "references": item.references,
                        "unresolved_details": results.get(item.question_id, {}).get(
                            "missing_information", []
                        ),
                    }
                    for item in draft.answers
                ],
                "question_resolutions": resolved_question_context(
                    state["interpretation"], state.get("question_resolutions", [])
                ),
                "requested_actions": state["interpretation"].get("requested_actions", []),
            }
            try:
                if (
                    composition_context["unresolved_actions"]
                    or live_state_questions
                    or ambiguous_questions
                ):
                    handoff = document_safe_body(draft.answers)
                    if (
                        composition_context["unresolved_actions"] or live_state_questions
                    ) and "I can't confirm" not in handoff:
                        handoff += "\n\nI can't confirm the requested change or live status yet."
                    concerns = []
                    if ambiguous_questions:
                        concerns.append(
                            "The source has alternative actions followed by one deadline. "
                            "Its original wording is retained; the teacher must decide which "
                            "action the timing qualifies before approval."
                        )
                    if composition_context["unresolved_actions"] or live_state_questions:
                        concerns.append(
                            "The live status or requested record change needs a teacher decision; "
                            "no current state or completed action was confirmed."
                        )
                    composed = DocumentEmailComposition(
                        body=handoff,
                        review_concerns=concerns,
                    )
                else:
                    composed = DocumentEmailComposition.model_validate(
                        self.model.compose_document_email(composition_context)
                    )
                body = normalize_unknown_greeting(composed.body, composition_context["student"])
                deferred_questions = [
                    item["question"]
                    for item in composition_context["question_resolutions"]
                    if item.get("decision") == "defer"
                ]
                body, promise_removed = _remove_unapproved_promises(body, deferred_questions)
                body, signature_removed = _unsigned_email(
                    body, has_signature=bool(state["context"].get("teacher_signature"))
                )
                if (
                    not isinstance(body, str)
                    or not body.strip()
                    or len(body) > 20_000
                    or EVIDENCE_MARKER.search(body)
                    or "teacher_answer:" in body
                    or "teacher_deferral:" in body
                    or (
                        str(composition_context["student"].get("name") or "").strip().casefold()
                        == "new enquirer"
                        and "new enquirer" in body.casefold()
                    )
                ):
                    raise ModelError("The composed email is invalid.")
                draft.body = body.strip()
                draft.review_concerns = list(composed.review_concerns)
                draft.review_concerns.extend(
                    _composition_concerns(
                        draft.body,
                        facts,
                        deferred=any(
                            item.get("decision") == "defer"
                            for item in state.get("question_resolutions", [])
                        ),
                    )
                )
                if signature_removed:
                    draft.review_concerns.append(
                        "An unconfigured signature or name placeholder was removed."
                    )
                if promise_removed:
                    draft.review_concerns.append(
                        "An unapproved follow-up promise was removed from the draft."
                    )
                draft.review_concerns = list(dict.fromkeys(draft.review_concerns))
            except (ModelError, ValueError, TypeError, AttributeError):
                draft.rationale += (
                    " Email composition or its support check failed; "
                    "the teacher should review the fallback draft."
                )
        return {"draft": draft.model_dump(mode="json")}

    def persist_draft(self, state: State) -> dict:
        self.store.save_draft(
            state["run_id"], state["attempt"], state["draft"], state["evidence"], state["warnings"]
        )
        return {}

    def review(self, state: State) -> dict:
        # LangGraph restarts this node on resume: no persistence before the interrupt.
        decision = interrupt(
            {"run_id": state["run_id"], "revision": state["attempt"], "draft": state["draft"]}
        )
        review = Review.model_validate(decision)
        if (
            review.action not in {"approve", "revise"}
            or review.expected_revision != state["attempt"]
        ):
            conflict("Review does not match this draft revision.")
        return {"decision": review.model_dump(mode="json")}

    def revision(self, state: State) -> dict:
        feedback = state["decision"].get("feedback") or ""
        if state.get("feedback") and not feedback:
            feedback = state["feedback"]
        elif state.get("flow") != "makeup" and state.get("feedback"):
            feedback = (
                state["feedback"]
                + "\n\nLatest teacher feedback (supersedes conflicting earlier feedback):\n"
                + feedback
            )
        update = {"attempt": state["attempt"] + 1, "feedback": feedback}
        if state.get("flow") == "makeup":
            # Refresh extracted preferences/provenance before the fixed checks. This also
            # lets a legacy checkpoint acquire the newly required absence references.
            interpretation = self.model.interpret_makeup(
                {
                    **state["context"],
                    "previous_interpretation": state["interpretation"],
                    "teacher_feedback": feedback,
                }
            )
            self.store.save_revision_interpretation(state["run_id"], interpretation)
            update["interpretation"] = interpretation.model_dump(mode="json")
        else:
            decisions = state["decision"].get("question_resolutions", [])
            validate_resolution_update(state["interpretation"], state["draft"], decisions)
            update["question_resolutions"] = merge_resolutions(
                state.get("question_resolutions", state["draft"].get("question_resolutions", [])),
                decisions,
            )
            interpretation = self._enquiry_interpretation(state, feedback)
            identify_questions(interpretation, state["run_id"], state["interpretation"])
            self.store.save_revision_interpretation(state["run_id"], interpretation)
            update["interpretation"] = interpretation.model_dump(mode="json")
        return update

    def approve(self, state: State) -> dict:
        response_id = self.store.approve(state["run_id"], state["decision"].get("body"))
        return {"response_id": response_id}

    def remember_approval(self, state: State) -> dict:
        body = self.store.approved_response(state["run_id"])
        memory = self.model.reconcile(
            {
                **state["context"],
                "interpretation": state["interpretation"],
                "teacher_response": {
                    "id": state["response_id"],
                    "body": body,
                    "delivery": "unconfirmed",
                },
                "confirmed_booking": self.store.approved_booking(state["run_id"]),
            }
        )
        self.store.remember_approval(state["run_id"], memory)
        logger.info("approved_memory_updated", extra={"run_id": state["run_id"]})
        return {}
