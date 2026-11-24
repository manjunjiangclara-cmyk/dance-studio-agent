"""Teacher-facing labels derived from the workflow's evidence and answer states."""

from typing import Literal

from studio_copilot.agent.makeup import evidence_result

ReviewRequirement = Literal["student_information", "teacher_input", "teacher_review"]


def review_requirements(
    flow: str | None,
    interpretation: dict,
    evidence: list[dict],
    draft: dict | None,
    *,
    missing_teacher_information: bool = False,
) -> list[ReviewRequirement]:
    draft = draft or {}
    answers = draft.get("answers") or []
    resolved_ids = {item["question_id"] for item in draft.get("question_resolutions") or []}
    needs_student = any(answer["status"] == "needs_student" for answer in answers)
    needs_teacher_input = (
        missing_teacher_information
        or bool(set(draft.get("required_question_ids") or []) - resolved_ids)
        or any(
            answer["status"] == "needs_teacher" and answer.get("question_id") not in resolved_ids
            for answer in answers
        )
    )
    needs_teacher_review = flow == "teacher_handoff"
    if flow == "makeup":
        verification = evidence_result(evidence, "verify_makeup_request")
        candidates = evidence_result(evidence, "validate_makeup_candidates")
        valid_sessions = candidates.get("valid_session_ids")
        blocked_reasons = {
            item["reason"] for item in candidates.get("excluded", []) if "reason" in item
        }
        needs_student = bool(
            candidates.get("request_date_conflict")
            or candidates.get("invalid_requested_time")
            or candidates.get("ambiguous")
            or (candidates.get("options_requested") and valid_sessions)
            or (verification and interpretation.get("absence_date") is None)
            or (
                not valid_sessions
                and blocked_reasons.intersection(
                    {
                        "full",
                        "overlapping_session",
                        "already_in_session",
                        "requested_class_mismatch",
                        "requested_time_mismatch",
                    }
                )
            )
        )
        needs_teacher_review = bool(
            verification.get("existing_makeup_session_id")
            or (
                verification.get("notice_before_start") is False
                and verification.get("notice_acceptable") is False
            )
            or (verification and not verification.get("verified") and not needs_student)
            or candidates.get("search_incomplete")
            or (
                not valid_sessions
                and (
                    verification.get("verified")
                    and candidates.get("max_attended_level") is None
                    or blocked_reasons.intersection({"above_attended_level", "unknown_level"})
                )
            )
        )
    requirements: list[ReviewRequirement] = []
    if needs_student:
        requirements.append("student_information")
    if needs_teacher_input:
        requirements.append("teacher_input")
    if needs_teacher_review:
        requirements.append("teacher_review")
    return requirements
