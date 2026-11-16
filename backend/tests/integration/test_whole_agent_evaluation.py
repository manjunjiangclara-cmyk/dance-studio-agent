"""Unpaid PostgreSQL test of fictional setup and authenticated run boundary."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import Enrolment, SessionAttendance, Student
from whole_agent_evaluation.runner import run_case

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
