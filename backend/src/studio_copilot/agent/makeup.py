"""Mandatory read-only makeup verification, candidate checks, and approval revalidation.

The model extracts a request; it cannot skip these checks or grant entitlement.
Verification and candidate results are retained as evidence in existing run/checkpoint storage.
"""

import hashlib
import re
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.administration.service import conflict, require
from studio_copilot.agent.tools import execute_tool
from studio_copilot.persistence.models import (
    AgentRun,
    ClassSession,
    Conversation,
    Enrolment,
    Message,
    SessionAttendance,
    Student,
    StudioClass,
)


def evidence_result(evidence: list[dict], name: str) -> dict:
    return next((e["result"] for e in evidence if e.get("tool") == name), {})


def validated_candidate_ids(evidence: list[dict]) -> set[UUID]:
    if not evidence_result(evidence, "verify_makeup_request").get("verified"):
        return set()
    ids = evidence_result(evidence, "validate_makeup_candidates").get("valid_session_ids", [])
    searched = {
        s.get("id")
        for e in evidence
        if e.get("tool") == "search_sessions"
        for s in e.get("result", {}).get("items", [])
    }
    validated = set()
    for value in ids:
        if value not in searched:
            continue
        try:
            validated.add(UUID(value))
        except (TypeError, ValueError):
            continue
    return validated


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _local_time(value):
    try:
        result = time.fromisoformat(value)
        return result if result.tzinfo is None else None
    except (TypeError, ValueError):
        return None


def _notice_digest(message: Message) -> str:
    return hashlib.sha256(
        (message.body + "\n" + message.occurred_at.isoformat()).encode()
    ).hexdigest()


def _explicit_absence_notice(message: Message, day: date) -> bool:
    """Accept only bounded statements; unfamiliar or conflicting text needs review."""
    date_text = re.escape(day.isoformat())
    weekday = day.strftime("%A")
    statement = (
        r"i\s+(?:will\s+miss|missed|cannot\s+attend|can't\s+attend)\s+"
        rf"(?:my\s+(?:{weekday}\s+)?class\s+on\s+{date_text}|{weekday}\s+{date_text})"
    )
    question = (
        r"(?:can|could)\s+i\s+(?:make\s+it\s+up"
        r"(?:\s+(?:(?:on|in)\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"(?:\s+level\s+\d+\s+on)?(?:\s+\d{4}-\d{2}-\d{2})?"
        r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm))?"
        r"|\s+on\s+\d{4}-\d{2}-\d{2})?"
        r"|attend\s+\d{4}-\d{2}-\d{2}(?:\s+instead)?)"
    )
    return (
        re.fullmatch(
            rf"\s*{statement}\s*[.!]?(?:\s+{question}\s*[?]?)?\s*",
            message.body,
            flags=re.IGNORECASE,
        )
        is not None
    )


_MAKEUP_DATE_CHANGE = re.compile(
    r"\s*(?:actually,?\s+)?(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"(?:\s+(?P<date>\d{4}-\d{2}-\d{2}))?\s+"
    r"(?:instead(?:,?\s+please)?[.!]?|works after all[.!]\s+could I switch back to that one\?)"
    r"\s*",
    re.IGNORECASE,
)


def _makeup_date_change(body: str, absence_date: date) -> bool:
    match = _MAKEUP_DATE_CHANGE.fullmatch(body)
    if not match:
        return False
    weekday = match["weekday"].casefold()
    if match["date"] is None:
        return weekday != absence_date.strftime("%A").casefold()
    target = _date(match["date"])
    return (
        target is not None
        and target != absence_date
        and weekday == target.strftime("%A").casefold()
    )


def _notice_context_unambiguous(db: Session, notice: Message, source: Message, day: date) -> bool:
    if not _explicit_absence_notice(notice, day):
        return False
    if notice.id != source.id and notice.created_at >= source.created_at:
        return False

    # Carry forward the original evidence only across unambiguous date changes or
    # explicit confirmations of the same absence. Apply the same check at approval.
    followups = db.scalars(
        select(Message).where(
            Message.conversation_id == notice.conversation_id,
            Message.kind == "student_email",
            Message.created_at >= notice.created_at,
            Message.id != notice.id,
        )
    )
    return all(
        message.created_at <= source.created_at
        and (_makeup_date_change(message.body, day) or _explicit_absence_notice(message, day))
        for message in followups
    )


def _existing_makeup(
    db: Session, conversation: Conversation, missed_id: UUID
) -> ClassSession | None:
    approved = db.scalars(
        select(AgentRun).where(
            AgentRun.conversation_id == conversation.id,
            AgentRun.approved_response_id.is_not(None),
            AgentRun.draft_details["booking_session_id"].astext.is_not(None),
        )
    )
    for run in approved:
        if evidence_result(run.evidence, "verify_makeup_request").get("absence_session_id") != str(
            missed_id
        ):
            continue
        booked = db.get(ClassSession, UUID(run.draft_details["booking_session_id"]))
        if booked is not None and conversation.student_id in booked.students:
            return booked
    return None


def _snapshot(session: ClassSession) -> dict:
    return {
        "id": str(session.id),
        "class_id": str(session.class_id),
        "starts_at": session.starts_at.isoformat(),
        "ends_at": session.ends_at.isoformat(),
        "class_name": session.regular_class.name,
        "level": session.regular_class.level,
        "location_id": str(session.regular_class.location_id),
        "timezone": session.regular_class.location.timezone,
    }


def attendance_status(db, student_id, session_id):
    row = db.scalar(
        select(SessionAttendance).where(
            SessionAttendance.student_id == student_id, SessionAttendance.session_id == session_id
        )
    )
    return row.status if row else "unknown"


def attended_level(db, student_id, policy, reference_at):
    """Return the highest recorded attended level, failing closed on unknown labels."""
    order = policy.get("level_order", [])
    ranks = {name.casefold(): index for index, name in enumerate(order)}
    levels = list(
        db.scalars(
            select(SessionAttendance.level_at_attendance)
            .join(ClassSession, ClassSession.id == SessionAttendance.session_id)
            .where(
                SessionAttendance.student_id == student_id,
                SessionAttendance.status == "attended",
                ClassSession.ends_at <= reference_at,
            )
        )
    )
    if not ranks or not levels or any(level.casefold() not in ranks for level in levels):
        return None
    return max(ranks[level.casefold()] for level in levels)


def overlapping_session(db, student_id, target):
    return (
        db.scalar(
            select(ClassSession.id)
            .where(
                ClassSession.id != target.id,
                ClassSession.students.any(student_id),
                ClassSession.starts_at < target.ends_at,
                ClassSession.ends_at > target.starts_at,
            )
            .limit(1)
        )
        is not None
    )


def gather_makeup(engine, state: dict) -> dict:
    """Fixed sequence: date-specific enrolments, source/notice verification, search, validation."""
    context, parsed = state["context"], state["interpretation"]
    student_id, source_id = UUID(context["student"]["id"]), UUID(context["source"]["id"])
    evidence, warnings = [], list(parsed.get("missing_details", []))

    def record(name, arguments, result):
        evidence.append({"tool": name, "arguments": arguments, "result": result})
        return result

    with Session(engine) as db:

        def tool(name, arguments, *, session_cursor=None):
            return record(
                name,
                arguments,
                execute_tool(
                    db,
                    student_id,
                    source_id,
                    context["policy"],
                    name,
                    arguments,
                    **({"session_cursor": session_cursor} if session_cursor else {}),
                ),
            )

        require(db, Student, student_id)
        source = require(db, Message, source_id)
        absence_date = _date(parsed.get("absence_date"))
        verification = {
            "verified": False,
            "absence_session_id": None,
            "absence_message_id": None,
            "notice_acceptable": False,
            "issues": [],
            "references": [],
        }
        issues = verification["issues"]
        enrolments = []
        if absence_date is None:
            issues.append("Confirm the missed class and its date.")
        else:
            enrolments = tool("get_enrolments", {"on_date": absence_date.isoformat()})["items"]
        active_classes = {e["class_id"] for e in enrolments}
        matches = []
        if absence_date is not None:
            lower = datetime.combine(absence_date - timedelta(days=1), time.min, UTC)
            upper = datetime.combine(absence_date + timedelta(days=2), time.min, UTC)
            sessions = db.scalars(
                select(ClassSession).where(
                    ClassSession.starts_at >= lower,
                    ClassSession.starts_at < upper,
                    ClassSession.students.any(student_id),
                )
            )
            for session in sessions:
                zone = ZoneInfo(session.regular_class.location.timezone)
                if (
                    session.starts_at.astimezone(zone).date() == absence_date
                    and str(session.class_id) in active_classes
                ):
                    matches.append(session)
            if len(matches) != 1:
                issues.append(
                    "The missed class/date must match one enrolled session in your student list."
                )
            elif parsed.get("absence_class_id") and str(matches[0].class_id) != str(
                parsed["absence_class_id"]
            ):
                issues.append("The selected class does not match the missed session.")
        missed = matches[0] if len(matches) == 1 else None
        try:
            notice_id = UUID(str(parsed.get("absence_message_id")))
        except (TypeError, ValueError):
            notice_id = None
        notice = db.get(Message, notice_id) if notice_id else None
        visible_ids = {
            m["id"] for m in context.get("history", []) if m.get("kind") == "student_email"
        } | {str(source_id)}
        if (
            notice is None
            or str(notice.id) not in visible_ids
            or notice.kind != "student_email"
            or notice.conversation_id != source.conversation_id
            or source.conversation.student_id != student_id
            or notice.occurred_at > source.occurred_at
            or notice.created_at > source.created_at
        ):
            issues.append("Confirm the student email that reported this absence.")
        elif missed is not None and not _notice_context_unambiguous(
            db, notice, source, absence_date
        ):
            issues.append("Staff must confirm that the selected email reports this absence.")
        elif missed is not None:
            result = tool(
                "check_absence_notice",
                {"session_id": str(missed.id), "absence_message_id": str(notice.id)},
            )
            if result.get("absence_message_id") != str(notice.id):
                issues.append("Absence notice provenance could not be verified.")
            else:
                verification["notice_before_start"] = result.get("notice_before_start")
                verification["notice_acceptable"] = (
                    not result.get("rule_enabled") or result.get("notice_before_start") is True
                )
                if not verification["notice_acceptable"]:
                    warnings.append("The absence notice was late; teacher review is needed.")
        if missed is not None:
            booked = _existing_makeup(db, source.conversation, missed.id)
            if booked is not None:
                verification["existing_makeup_session_id"] = str(booked.id)
                verification["references"].append("session:" + str(booked.id))
                issues.append(
                    "A makeup is already booked for this absence. Staff must review changes."
                )
            status = attendance_status(db, student_id, missed.id)
            verification["attendance_status"] = status
            if status == "attended":
                issues.append(
                    "The attendance record says the student attended this session; "
                    "staff review is needed."
                )
            elif status == "unknown" and missed.ends_at <= datetime.now(UTC):
                issues.append(
                    "Attendance for the missed session is not recorded; staff review is needed."
                )
        if missed is not None and not issues:
            enrolment = next(e for e in enrolments if e["class_id"] == str(missed.class_id))
            verification.update(
                verified=True,
                absence_session_id=str(missed.id),
                absence_message_id=str(notice.id),
                source_message_id=str(source_id),
                enrolment_id=enrolment["id"],
                absence_date=absence_date.isoformat(),
                missed_session=_snapshot(missed),
                notice_digest=_notice_digest(notice),
                references=[
                    "session:" + str(missed.id),
                    "enrolment:" + enrolment["id"],
                    "message:" + str(notice.id),
                ],
            )
        record("verify_makeup_request", {"absence_date": parsed.get("absence_date")}, verification)
        warnings.extend(issues)
        # Timetable facts can still help a clarification; this never grants a booking.
        tool("get_timetable", {})
        preferred = _date(parsed.get("preferred_date"))
        requested_class = parsed.get("preferred_class_name")
        requested_time_text = parsed.get("preferred_time")
        requested_time = _local_time(requested_time_text)
        validated = {
            "valid_session_ids": [],
            "excluded": [],
            "references": [],
            "requested_class_name": requested_class,
            "requested_time": requested_time_text,
            "invalid_requested_time": bool(requested_time_text and requested_time is None),
        }
        max_level = attended_level(db, student_id, context["policy"], datetime.now(UTC))
        level_order = context["policy"].get("level_order", [])
        validated["max_attended_level"] = level_order[max_level] if max_level is not None else None
        validated["options_requested"] = preferred is None
        if verification["verified"] and max_level is None:
            warnings.append(
                "Record attended class levels and configure the studio level order "
                "before offering a makeup."
            )
        if validation_time_invalid := validated["invalid_requested_time"]:
            warnings.append("Confirm the requested makeup start time.")
        if (
            verification["verified"]
            and verification["notice_acceptable"]
            and max_level is not None
            and not validation_time_invalid
        ):
            location_id = None
            preference = parsed.get("location_preference")
            if preference:
                locations = tool("get_locations", {"location_id": None})["items"]
                options = [
                    location
                    for location in locations
                    if preference.casefold() in location["name"].casefold()
                    or preference == location["id"]
                ]
                if len(options) == 1:
                    location_id = options[0]["id"]
                else:
                    warnings.append("Confirm which studio location you prefer.")
            weekday = parsed.get("preferred_weekday")
            weekdays = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
            inconsistent_day = (
                preferred is not None
                and weekday
                and weekday.casefold() != weekdays[preferred.weekday()]
            )
            if weekday and weekday.casefold() not in weekdays:
                inconsistent_day = True
            if inconsistent_day:
                warnings.append("Confirm the preferred date and weekday; they do not match.")
            elif not preference or location_id:
                search_args = {
                    "from_date": (preferred or datetime.now(UTC).date()).isoformat(),
                    "to_date": (
                        preferred or (datetime.now(UTC).date() + timedelta(days=60))
                    ).isoformat(),
                    "weekday": preferred.weekday()
                    if preferred
                    else weekdays.index(weekday.casefold())
                    if weekday
                    else None,
                    "level": None,
                    "location_id": location_id,
                }
                cursor = None
                for _ in range(20):
                    result = tool("search_sessions", search_args, session_cursor=cursor)
                    for item in result["items"]:
                        session = require(db, ClassSession, UUID(item["id"]))
                        item["student_already_in_session"] = student_id in session.students
                        item["location_name"] = session.regular_class.location.name
                        reason = None
                        if requested_class and (
                            " ".join(requested_class.casefold().split())
                            != " ".join(session.regular_class.name.casefold().split())
                        ):
                            reason = "requested_class_mismatch"
                        elif requested_time is not None and (
                            session.starts_at.astimezone(
                                ZoneInfo(session.regular_class.location.timezone)
                            ).time()
                            != requested_time
                        ):
                            reason = "requested_time_mismatch"
                        elif session.starts_at <= datetime.now(UTC):
                            reason = "past"
                        elif item["student_already_in_session"]:
                            reason = "already_in_session"
                        elif len(session.students) >= session.capacity:
                            reason = "full"
                        elif overlapping_session(db, student_id, session):
                            reason = "overlapping_session"
                        elif session.regular_class.level.casefold() not in [
                            x.casefold() for x in level_order
                        ]:
                            reason = "unknown_level"
                        elif [x.casefold() for x in level_order].index(
                            session.regular_class.level.casefold()
                        ) > max_level:
                            reason = "above_attended_level"
                        if reason:
                            validated["excluded"].append(
                                {"session_id": item["id"], "reason": reason}
                            )
                        else:
                            validated["valid_session_ids"].append(item["id"])
                            validated["references"].append("session:" + item["id"])
                    next_cursor = result.get("next_cursor")
                    if not next_cursor or len(validated["valid_session_ids"]) >= 30:
                        break
                    cursor = (datetime.fromisoformat(next_cursor[0]), UUID(next_cursor[1]))
                else:
                    validated["search_incomplete"] = True
                    warnings.append(
                        "The session search was incomplete; please review further options."
                    )
                if not validated["valid_session_ids"] and not validated.get("search_incomplete"):
                    warnings.append(
                        "No available replacement session matches the verified request."
                    )
        record("validate_makeup_candidates", {}, validated)
        # All reads end without a commit; model calls happen after this session closes.
        db.rollback()
    return {"evidence": evidence, "warnings": warnings}


def clarification_body(evidence: list[dict]) -> str:
    verified = evidence_result(evidence, "verify_makeup_request").get("verified")
    excluded = evidence_result(evidence, "validate_makeup_candidates").get("excluded", [])
    verification = evidence_result(evidence, "verify_makeup_request")
    if verification.get("existing_makeup_session_id"):
        return (
            "Our records show a makeup is already booked for that absence. "
            "We can review your request to change it."
        )
    if verification.get("attendance_status") == "attended":
        return (
            "Our attendance record shows you attended that session. "
            "We'll review the records before arranging a makeup."
        )
    if verification.get("attendance_status") == "unknown" and any(
        "Attendance" in x for x in verification.get("issues", [])
    ):
        return "We need to check the attendance record for that session before arranging a makeup."
    if any("selected email reports this absence" in x for x in verification.get("issues", [])):
        return "We need to review the absence notice for that class before arranging a makeup."
    if not verified:
        return (
            "Thanks for your message. Could you confirm which class you missed and its date? "
            "I need to check these against your class records before arranging a makeup."
        )
    if verification.get("notice_acceptable") is False:
        return (
            "The absence notice was received after the class started. "
            "We'll review your request and let you know."
        )
    validation = evidence_result(evidence, "validate_makeup_candidates")
    if validation.get("search_incomplete") and not validation.get("valid_session_ids"):
        return "We need to review more sessions before we can confirm the available options."
    if validation.get("invalid_requested_time"):
        return "Could you confirm the requested makeup start time?"
    if validation.get("max_attended_level") is None:
        return "We need to review your attendance and class levels before suggesting a makeup."
    if validation.get("options_requested") and validation.get("valid_session_ids"):
        valid = set(validation["valid_session_ids"])
        items = [
            item
            for e in evidence
            if e.get("tool") == "search_sessions"
            for item in e.get("result", {}).get("items", [])
            if item["id"] in valid
        ]
        options = "; ".join(
            f"{item['class_name']} ({item['level']}) at {item['starts_at']}, "
            f"{item['location_name']}"
            for item in items
        )
        return (
            "Available options over the next 60 days include: "
            + options
            + ". Please tell us which session you prefer; availability will be checked again."
        )
    if (
        validation.get("requested_class_name")
        and not validation.get("valid_session_ids")
        and all(
            item.get("reason") in {"requested_class_mismatch", "requested_time_mismatch"}
            for item in excluded
        )
    ):
        return (
            "I couldn't find an available session matching the requested class. "
            "Could you confirm the class name, date and time?"
        )
    if (
        validation.get("requested_time")
        and not validation.get("valid_session_ids")
        and all(item.get("reason") == "requested_time_mismatch" for item in excluded)
    ):
        return "I couldn't find a session at the requested time. Could you confirm the time?"
    if validation.get("options_requested"):
        return (
            "We could not find a suitable available makeup session in the next 60 days. "
            "We'll review the options with you."
        )
    if any(e["reason"] == "above_attended_level" for e in excluded):
        return (
            "The requested class is above the level shown in your attendance records. "
            "We'll review other makeup options with you."
        )
    if any(e["reason"] == "overlapping_session" for e in excluded):
        return (
            "Our records show another class at that time. "
            "Could you choose a different makeup session?"
        )
    if any(e["reason"] == "already_in_session" for e in excluded):
        return (
            "Our records already list you in the requested session. "
            "Could you confirm which makeup session you mean?"
        )
    if any(e["reason"] == "full" for e in excluded):
        return (
            "The requested session currently has no places available. "
            "Could you suggest another makeup date?"
        )
    return (
        "Thanks for your message. Could you confirm your preferred makeup date and location "
        "so I can check the available options?"
    )


def revalidate_makeup(db: Session, run, target_id: UUID) -> None:
    """Protect approval from old checkpoints, changed source facts, and bypassed model checks."""
    verified = evidence_result(run.evidence, "verify_makeup_request")
    if run.interpretation.get("flow") != "makeup" or target_id not in validated_candidate_ids(
        run.evidence
    ):
        conflict("Regenerate the draft: its makeup request and candidate were not verified.")
    try:
        enrolment_id = UUID(verified["enrolment_id"])
        missed_id = UUID(verified["absence_session_id"])
        notice_id = UUID(verified["absence_message_id"])
    except (KeyError, TypeError, ValueError):
        conflict("Regenerate the draft: its absence verification is incomplete.")
    # Match enrolment edit lock order; then acquire all class locks in stable UUID order.
    conversation = require(db, Conversation, run.conversation_id)
    require(db, Student, conversation.student_id, lock=True)
    if _existing_makeup(db, conversation, missed_id) is not None:
        conflict("A makeup is already booked for this absence. Review the change manually.")
    enrolment = require(db, Enrolment, enrolment_id, lock=True)
    missed = require(db, ClassSession, missed_id)
    target = require(db, ClassSession, target_id)
    for class_id in sorted({missed.class_id, target.class_id}, key=str):
        require(db, StudioClass, class_id, lock=True)
    missed = require(db, ClassSession, missed_id, lock=True)
    target = require(db, ClassSession, target_id, lock=True)
    notice = require(db, Message, notice_id, lock=True)
    source = require(db, Message, run.source_message_id)
    conversation = require(db, Conversation, run.conversation_id)
    day = _date(verified.get("absence_date"))
    if (
        day is None
        or enrolment.student_id != conversation.student_id
        or enrolment.class_id != missed.class_id
        or not enrolment.is_active_on(day)
        or conversation.student_id not in missed.students
        or missed.starts_at.astimezone(ZoneInfo(missed.regular_class.location.timezone)).date()
        != day
        or _snapshot(missed) != verified.get("missed_session")
        or verified.get("source_message_id") != str(source.id)
        or notice.kind != "student_email"
        or notice.conversation_id != conversation.id
        or notice.occurred_at > source.occurred_at
        or notice.created_at > source.created_at
        or _notice_digest(notice) != verified.get("notice_digest")
        or not _notice_context_unambiguous(db, notice, source, day)
    ):
        conflict(
            "The missed-session or absence records changed. Request a new draft before booking."
        )

    if (
        run.policy_snapshot.get("absence_notice_before_start")
        and notice.occurred_at >= missed.starts_at
    ):
        conflict("The absence notice was late. Review the request before arranging a makeup.")
    active_classes = {
        row.class_id
        for row in db.scalars(
            select(Enrolment).where(Enrolment.student_id == conversation.student_id)
        )
        if row.is_active_on(day)
    }
    nearby_sessions = db.scalars(
        select(ClassSession).where(
            ClassSession.starts_at >= datetime.combine(day - timedelta(days=1), time.min, UTC),
            ClassSession.starts_at < datetime.combine(day + timedelta(days=2), time.min, UTC),
            ClassSession.students.any(conversation.student_id),
        )
    )
    matches = [
        session.id
        for session in nearby_sessions
        if session.class_id in active_classes
        and session.starts_at.astimezone(ZoneInfo(session.regular_class.location.timezone)).date()
        == day
    ]
    if matches != [missed.id]:
        conflict("The absence notice no longer identifies one session. Request a new draft.")
    status = attendance_status(db, conversation.student_id, missed.id)
    if status == "attended" or (status == "unknown" and missed.ends_at <= datetime.now(UTC)):
        conflict("Attendance no longer supports this makeup. Request a new draft before booking.")
    rank = attended_level(db, conversation.student_id, run.policy_snapshot, datetime.now(UTC))
    order = [level.casefold() for level in run.policy_snapshot.get("level_order", [])]
    requested_class = run.interpretation.get("preferred_class_name")
    if requested_class and (
        " ".join(requested_class.casefold().split())
        != " ".join(target.regular_class.name.casefold().split())
    ):
        conflict("The requested class no longer matches this session. Request a new draft.")
    requested_time_text = run.interpretation.get("preferred_time")
    requested_time = _local_time(requested_time_text)
    if requested_time_text and (
        requested_time is None
        or target.starts_at.astimezone(ZoneInfo(target.regular_class.location.timezone)).time()
        != requested_time
    ):
        conflict("The requested start time no longer matches this session. Request a new draft.")
    requested_weekday = run.interpretation.get("preferred_weekday")
    if requested_weekday:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if requested_weekday.casefold() not in weekdays or target.starts_at.astimezone(
            ZoneInfo(target.regular_class.location.timezone)
        ).weekday() != weekdays.index(requested_weekday.casefold()):
            conflict("The requested weekday no longer matches this session. Request a new draft.")
    target_level = target.regular_class.level.casefold()
    if rank is None or target_level not in order or order.index(target_level) > rank:
        conflict("The student's recorded attendance does not support this class level.")
    if overlapping_session(db, conversation.student_id, target):
        conflict("The student is already assigned to an overlapping session.")
