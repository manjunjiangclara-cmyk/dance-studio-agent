"""Unpaid PostgreSQL test of fictional setup and authenticated run boundary."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Enrolment, SessionAttendance, Student, StudioClass
from whole_agent_evaluation.runner import clear_case, run_case, seed_case

pytestmark = pytest.mark.integration


def test_run_case_seeds_enrolment_and_absence_without_business_mutation(db_engine):
    case = {
        "id": "synthetic-absence-test",
        "category": "makeup_absence",
        "message": "May I make up the class I missed?",
        "as_of": "2027-06-01",
        "setup": {"student_key": "learner", "class_key": "monday", "absence_key": "absence"},
        "expected": {"route": "makeup", "disposition": "review"},
    }
    business = {
        "students": [
            {
                "key": "learner",
                "display_name": "Fictional Learner",
                "enrolled_class_keys": ["monday"],
            }
        ],
        "classes": [{"key": "monday", "name": "Monday dance", "capacity": 12}],
        "absences": [
            {
                "key": "absence",
                "student_key": "learner",
                "class_key": "monday",
                "starts_at": "2027-05-31T18:00:00+10:00",
                "status": "absent",
            }
        ],
    }

    class Client:
        def post(self, url, json):
            assert url.startswith("/api/v1/conversations/")
            assert json["source_message_id"]
            return type(
                "Response",
                (),
                {
                    "status_code": 200,
                    "json": lambda self: {
                        "id": "synthetic-run",
                        "status": "awaiting_review",
                        "draft_details": {"body": "The teacher will review this."},
                        "evidence": [],
                        "interpretation": {},
                    },
                },
            )()

    class Model:
        calls = []
        failures = []

    class Budget:
        def snapshot(self):
            return {"requests": 0}

    row = run_case(Client(), db_engine, case, business, Budget(), Model())
    assert row["status"] == "completed"
    assert row["no_business_change"]
    assert len(row["output_sha256"]) == 64
    with Session(db_engine) as db:
        assert len(list(db.scalars(select(Student)))) == 1
        assert len(list(db.scalars(select(Enrolment)))) == 1
        assert len(list(db.scalars(select(SessionAttendance)))) == 1


def test_next_case_cannot_see_previous_class(db_engine):
    first = {
        "id": "first-isolation",
        "message": "First class?",
        "as_of": "2027-06-01",
        "setup": {"class_key": "first"},
    }
    second = {
        "id": "second-isolation",
        "message": "Second class?",
        "as_of": "2027-06-01",
        "setup": {"class_key": "second"},
    }
    seed_case(
        db_engine,
        first,
        {
            "students": [],
            "classes": [{"key": "first", "name": "First only", "day": "Monday", "time": "18:00"}],
            "absences": [],
        },
    )
    clear_case(db_engine)
    seed_case(
        db_engine,
        second,
        {
            "students": [],
            "classes": [
                {"key": "second", "name": "Second only", "day": "Tuesday", "time": "18:00"}
            ],
            "absences": [],
        },
    )
    with Session(db_engine) as db:
        assert [record.name for record in db.scalars(select(StudioClass))] == ["Second only"]
        assert [record.email for record in db.scalars(select(Student))] == [
            "whole-agent-second-isolation@example.com"
        ]
