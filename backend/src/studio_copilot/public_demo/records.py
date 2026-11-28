"""Read-only adapter for the same fictional records shown by Database and Timetable."""

import json
from contextlib import contextmanager
from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from studio_copilot.agent.makeup import attended_rank, gather_makeup_records

CASES = {
    "booking": "97aa529c-2ca7-5ee9-86c6-0d7c9da03752",
    "document": "3a067002-bcaf-57b7-a336-a1e6dbe29914",
    "noah": "11021b1d-f2c9-5bc0-bed7-01d1418e57bf",
    "riley": "e7006165-a655-507c-815c-2ead33050f7f",
}
POLICY = {
    "version": "demo-1",
    "absence_notice_before_start": True,
    "level_order": ["Level 1", "Level 2", "Level 3"],
}


@lru_cache(maxsize=1)
def example_records():
    module = Path(__file__).resolve()
    bundled = module.with_name("demo_records.json")
    source = module.parents[4] / "frontend/src/data/examples.v1.json"
    return json.loads((bundled if bundled.is_file() else source).read_text(encoding="utf-8"))


def related_makeup_runs(records, student_id, absence_session_id):
    conversation_ids = {
        row["id"] for row in records["conversations"] if row["student_id"] == str(student_id)
    }
    return [
        run
        for run in records["agent_runs"]
        if run["conversation_id"] in conversation_ids
        and run["interpretation"].get("flow") == "makeup"
        and any(
            item["tool"] == "verify_makeup_request"
            and item["result"].get("absence_session_id") == str(absence_session_id)
            for item in run["evidence"]
        )
    ]


class FictionalRecords:
    def __init__(self, records=None):
        self.data = records if records is not None else example_records()
        self.classes = {row["id"]: row for row in self.data["classes"]}
        self.locations = {row["id"]: row for row in self.data["locations"]}
        self.session_rows = {row["id"]: row for row in self.data["class_sessions"]}
        self.messages = {row["id"]: row for row in self.data["messages"]}
        self.conversations = {row["id"]: row for row in self.data["conversations"]}
        self.students = {row["id"]: row for row in self.data["students"]}
        self.now = datetime.combine(
            date.fromisoformat(self.data["as_of"]), time.min, ZoneInfo("Australia/Melbourne")
        ).astimezone(UTC)

    def context(self, scenario):
        return self.context_for_message(CASES[scenario])

    def context_for_message(self, message_id):
        source = self.messages[message_id]
        conversation = self.conversations[source["conversation_id"]]
        student = self.students[conversation["student_id"]]
        related = sorted(
            (
                item
                for item in self.messages.values()
                if item["conversation_id"] == conversation["id"]
                and self._order(item) <= self._order(source)
            ),
            key=self._order,
        )
        return {
            "source": self._message_data(source),
            "conversation_id": conversation["id"],
            "student": {
                "id": student["id"],
                "name": student["display_name"],
                "email": student["email"],
                "highest_level": student["highest_level"],
                "context": student["context"],
                "ai_summary": student["ai_summary"],
            },
            "history": [
                self._message_data(row) for row in related if row["kind"] == "student_email"
            ],
            "approved_replies": [
                {**self._message_data(row), "delivery": "unconfirmed"}
                for row in related
                if row["kind"] == "teacher_response"
            ],
            "confirmed_bookings": self._confirmed_bookings(
                student["id"], conversation["id"], related
            ),
            "enrolments": self.enrolments(student["id"]),
            "policy": POLICY,
            "intake": {},
        }

    def walkthrough_context(
        self, student_id, request_id, body, *, prior=None, reply=None, prior_evidence=()
    ):
        if prior is not None:
            context = prior
            previous = context["source"]
            occurred_at = datetime.fromisoformat(previous["occurred_at"]) + timedelta(minutes=1)
            approved_reply = {
                "id": str(uuid5(UUID(previous["id"]), "demo-teacher-response")),
                "kind": "teacher_response",
                "body": reply,
                "occurred_at": occurred_at.isoformat(),
                "delivery": "unconfirmed",
            }
            context["approved_replies"].append(approved_reply)
            questions = {
                item["result"]["question_id"]: item["result"]["question"]
                for item in prior_evidence
                if item["tool"] == "document_answer"
            }
            for item in prior_evidence:
                if item["tool"] != "teacher_question_resolutions":
                    continue
                for resolution in item["result"]["items"]:
                    answer = resolution.get("answer")
                    if (
                        resolution["question_id"] in questions
                        and answer
                        and answer.casefold().strip() in reply.casefold()
                    ):
                        context.setdefault("approved_teacher_answers", []).append(
                            {
                                "question": questions[resolution["question_id"]],
                                "text": answer,
                                "references": ["message:" + approved_reply["id"]],
                            }
                        )
            occurred_at += timedelta(minutes=1)
        else:
            occurred_at = self.now
            last_message = max(
                (
                    row
                    for row in self.messages.values()
                    if self.conversations[row["conversation_id"]]["student_id"] == student_id
                    and datetime.fromisoformat(row["occurred_at"]) <= self.now
                ),
                key=self._order,
                default=None,
            )
            student = self.students.get(student_id)
            if last_message is not None:
                context = self.context_for_message(last_message["id"])
            else:
                context = {
                    "conversation_id": request_id,
                    "student": {
                        "id": student["id"] if student else request_id,
                        "name": student["display_name"] if student else "New enquirer",
                        "email": student["email"] if student else "enquirer@example.test",
                        "highest_level": student["highest_level"] if student else None,
                        "context": student["context"] if student else None,
                        "ai_summary": student["ai_summary"] if student else None,
                    },
                    "history": [],
                    "approved_replies": [],
                    "confirmed_bookings": [],
                    "enrolments": self.enrolments(student_id),
                    "policy": POLICY,
                    "intake": {},
                }
        source = {
            "id": str(uuid5(UUID(request_id), "demo-student-email")),
            "kind": "student_email",
            "body": body,
            "occurred_at": occurred_at.isoformat(),
        }
        context["source"] = source
        context["history"] = [*context["history"][-11:], source]
        context["approved_replies"] = context["approved_replies"][-12:]
        context["walkthrough"] = True
        return context

    @staticmethod
    def _message_data(message):
        return {key: message[key] for key in ("id", "kind", "body", "occurred_at")}

    @staticmethod
    def _order(message):
        return (
            datetime.fromisoformat(message["occurred_at"]),
            datetime.fromisoformat(message["created_at"]),
            message["id"],
        )

    def _confirmed_bookings(self, student_id, conversation_id, related):
        responses = {row["id"] for row in related if row["kind"] == "teacher_response"}
        bookings = []
        for run in self.data["agent_runs"]:
            if (
                run["conversation_id"] != conversation_id
                or run["status"] != "approved"
                or run["approved_response_id"] not in responses
            ):
                continue
            target = self.session_rows.get(run["draft_details"].get("booking_session_id"))
            if target and student_id in target["students"]:
                session = self.session(UUID(target["id"]))
                bookings.append(
                    {
                        "session_id": target["id"],
                        "class_name": session.regular_class.name,
                        "starts_at": target["starts_at"],
                        "location_name": session.regular_class.location.name,
                        "status": "confirmed",
                        "approved_response_id": run["approved_response_id"],
                    }
                )
        return bookings

    def enrolments(self, student_id, on_date=None):
        return [
            {**row, "class_name": self.classes[row["class_id"]]["name"]}
            for row in self.data["enrolments"]
            if row["student_id"] == str(student_id)
            and (
                on_date is None
                or (
                    row["status"] != "cancelled"
                    and row["starts_on"] <= on_date
                    and (row["ends_on"] is None or row["ends_on"] >= on_date)
                )
            )
        ]

    def session(self, session_id):
        row = self.session_rows[str(session_id)]
        group = self.classes[row["class_id"]]
        return SimpleNamespace(
            id=UUID(row["id"]),
            class_id=UUID(row["class_id"]),
            starts_at=datetime.fromisoformat(row["starts_at"]),
            ends_at=datetime.fromisoformat(row["ends_at"]),
            students={UUID(item) for item in row["students"]},
            capacity=row["capacity"],
            regular_class=SimpleNamespace(
                name=group["name"],
                level=group["level"],
                location_id=UUID(group["location_id"]),
                location=SimpleNamespace(**self.locations[group["location_id"]]),
            ),
        )

    def makeup(self, state):
        reader = FictionalMakeupReader(self, state["context"])
        return gather_makeup_records(reader, state, self.now)

    @contextmanager
    def tools(self, context):
        yield FictionalMakeupReader(self, context).tool

    def demo_documents(self, state, model):
        """Use the same grounded document pipeline on the isolated public corpus."""
        from fastapi import HTTPException

        from studio_copilot.documents import online
        from studio_copilot.public_demo import document_index

        if (
            model.demo_evidence_route(
                {**state["context"], "interpretation": state["interpretation"]}
            )
            != "documents"
        ):
            return None
        engine = None
        try:
            engine = document_index.engine_from_env()
            config = document_index.configuration(engine)
            result = online.gather(engine, state, config=config)
            if result is None or any(
                item["result"].get("status") == "failed" for item in result["evidence"]
            ):
                raise online.OnlineError("retrieval_failed")
            prior = state["context"].get("approved_teacher_answers", [])
            for item in result["evidence"]:
                answer = item["result"]
                for fact in reversed(prior):
                    if fact["question"].casefold().strip() == answer["question"].casefold().strip():
                        answer.update(
                            status="answered",
                            claims=[{"text": fact["text"]}],
                            references=fact["references"],
                            sources=[],
                            missing_information=[],
                        )
                        break
            return result
        except Exception as error:
            raise HTTPException(
                503, "Demo document search is temporarily unavailable. Please retry."
            ) from error
        finally:
            if engine is not None:
                engine.dispose()


class FictionalMakeupReader:
    def __init__(self, records, context):
        self.records, self.context = records, context

    def source(self, source_id):
        return self.notice(source_id)

    def notice(self, notice_id):
        row = self.records.messages.get(str(notice_id))
        if row is not None and row["conversation_id"] != self.context["conversation_id"]:
            return None
        if row is None and self.context.get("walkthrough"):
            row = next(
                (item for item in self.context["history"] if item["id"] == str(notice_id)), None
            )
        if row is None:
            return None
        return SimpleNamespace(
            id=UUID(row["id"]),
            kind=row["kind"],
            body=row["body"],
            conversation_id=UUID(self.context["conversation_id"]),
            conversation=SimpleNamespace(student_id=UUID(self.context["student"]["id"])),
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            created_at=datetime.fromisoformat(row.get("created_at", row["occurred_at"])),
        )

    def notice_followups(self, notice):
        return [
            message
            for row in self.context["history"]
            if (message := self.notice(row["id"]))
            and message.id != notice.id
            and message.created_at >= notice.created_at
        ]

    def sessions_on(self, student_id, absence_date):
        return [
            session
            for row in self.records.session_rows.values()
            if (session := self.session(UUID(row["id"])))
            and student_id in session.students
            and session.starts_at.astimezone(
                ZoneInfo(session.regular_class.location.timezone)
            ).date()
            == absence_date
        ]

    def session(self, session_id):
        return self.records.session(session_id)

    def existing_makeup(self, student_id, missed_id):
        for run in related_makeup_runs(self.records.data, student_id, missed_id):
            target = run["draft_details"].get("booking_session_id")
            if run["status"] == "approved" and run["approved_response_id"] and target:
                session = self.session(target)
                if student_id in session.students:
                    return session
        return None

    def pending_makeups(self, student_id, missed_id, run_id):
        return {
            row["draft_details"]["booking_session_id"]
            for row in related_makeup_runs(self.records.data, student_id, missed_id)
            if row["status"] == "awaiting_review"
            and row["id"] != run_id
            and row["draft_details"].get("booking_session_id")
        }

    def attendance_status(self, student_id, session_id):
        return next(
            (
                row["status"]
                for row in self.records.data["session_attendance"]
                if row["student_id"] == str(student_id) and row["session_id"] == str(session_id)
            ),
            "unknown",
        )

    def attended_level(self, student_id, policy, now):
        levels = [
            row["level_at_attendance"]
            for row in self.records.data["session_attendance"]
            if row["student_id"] == str(student_id)
            and row["status"] == "attended"
            and self.session(row["session_id"]).ends_at <= now
        ]
        return attended_rank(policy, levels)

    def overlaps(self, student_id, target):
        return any(
            session.id != target.id
            and student_id in session.students
            and session.starts_at < target.ends_at
            and session.ends_at > target.starts_at
            for row in self.records.session_rows.values()
            if (session := self.session(row["id"]))
        )

    def tool(self, name, arguments, *, session_cursor=None):
        if name == "get_enrolments":
            items = self.records.enrolments(self.context["student"]["id"], arguments.get("on_date"))
            return {"items": items, "references": ["enrolment:" + row["id"] for row in items]}
        if name == "get_locations":
            items = [
                row
                for row in self.records.locations.values()
                if not arguments.get("location_id") or arguments["location_id"] == row["id"]
            ]
            return {"items": items, "references": ["location:" + row["id"] for row in items]}
        if name == "get_timetable":
            items = [
                {
                    **row,
                    "location": self.records.locations[row["location_id"]],
                    "upcoming_sessions": [
                        self._item(self.session(session["id"]))
                        for session in self.records.session_rows.values()
                        if session["class_id"] == row["id"]
                        and self.session(session["id"]).starts_at >= self.records.now
                    ],
                }
                for row in self.records.classes.values()
            ]
            return {"items": items, "references": ["class:" + row["id"] for row in items]}
        if name == "search_sessions":
            return self._search(arguments, session_cursor)
        if name == "check_absence_notice":
            notice = self.notice(arguments["absence_message_id"])
            session = self.session(arguments["session_id"])
            if notice is None:
                return {"error": "Notice not found.", "references": []}
            return {
                "absence_message_id": str(notice.id),
                "rule_enabled": self.context["policy"]["absence_notice_before_start"],
                "notice_before_start": notice.occurred_at < session.starts_at,
                "references": ["message:" + str(notice.id), "session:" + str(session.id)],
            }
        return {"error": "This lookup is unavailable in the fictional records.", "references": []}

    @staticmethod
    def _item(session):
        group = session.regular_class
        return {
            "id": str(session.id),
            "class_id": str(session.class_id),
            "class_name": group.name,
            "level": group.level,
            "location_id": str(group.location_id),
            "location_name": group.location.name,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "capacity": session.capacity,
            "remaining_places": max(0, session.capacity - len(session.students)),
        }

    def _search(self, arguments, cursor):
        sessions = sorted(
            (self.session(value) for value in self.records.session_rows),
            key=lambda row: (row.starts_at, row.id),
        )
        items = []
        for session in sessions:
            if cursor is not None and (session.starts_at, session.id) <= cursor:
                continue
            local = session.starts_at.astimezone(ZoneInfo(session.regular_class.location.timezone))
            if not arguments["from_date"] <= local.date().isoformat() <= arguments["to_date"]:
                continue
            if arguments.get("weekday") is not None and arguments["weekday"] != local.weekday():
                continue
            if arguments.get("level") and arguments["level"] != session.regular_class.level:
                continue
            if arguments.get("location_id") and arguments["location_id"] != str(
                session.regular_class.location_id
            ):
                continue
            items.append(self._item(session))
        next_cursor = [items[29]["starts_at"], items[29]["id"]] if len(items) > 30 else None
        return {
            "items": items[:30],
            "references": ["session:" + row["id"] for row in items[:30]],
            "next_cursor": next_cursor,
        }
