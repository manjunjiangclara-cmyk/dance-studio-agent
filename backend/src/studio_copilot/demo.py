"""Add a small synthetic walkthrough once; never reset or overwrite existing data."""

import json
from datetime import date, datetime
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from studio_copilot.persistence.database import make_engine
from studio_copilot.persistence.models import (
    ClassSession,
    Conversation,
    Enrolment,
    Location,
    Message,
    Student,
    StudioClass,
    Term,
)


def demo_id(name: str):
    return uuid5(NAMESPACE_URL, f"studio-copilot-synthetic-demo/v1/{name}")


def seed_demo(db: Session) -> dict:
    ids = {
        name: demo_id(name)
        for name in [
            "alex",
            "sam",
            "term",
            "studio_a",
            "studio_b",
            "monday",
            "thursday",
            "saturday",
            "conversation",
        ]
    }
    # A single transaction creates all fixtures. Repeated calls leave them untouched.
    if db.get(Student, ids["alex"]) is not None:
        return {"created": False, "ids": {key: str(value) for key, value in ids.items()}}

    term = Term(
        id=ids["term"],
        name="Synthetic demo term 2027",
        starts_on=date(2027, 2, 1),
        ends_on=date(2027, 3, 31),
    )
    a = Location(
        id=ids["studio_a"],
        name="Demo Studio A",
        address="Fictional location A",
        timezone="Australia/Melbourne",
    )
    b = Location(
        id=ids["studio_b"],
        name="Demo Studio B",
        address="Fictional location B",
        timezone="Australia/Melbourne",
    )
    alex = Student(
        id=ids["alex"],
        display_name="Alex Example",
        email="alex.demo@example.com",
        highest_level="Level 2",
        context={"preferred_day": "Saturday"},
    )
    sam = Student(
        id=ids["sam"],
        display_name="Sam Example",
        email="sam.demo@example.com",
        highest_level="Level 2",
    )
    classes = {}
    for key, location, day in [("monday", a, 8), ("thursday", b, 11), ("saturday", a, 13)]:
        regular_class = StudioClass(
            id=ids[key],
            name=f"Demo {key.title()} Level 2",
            level="Level 2",
            term=term,
            location=location,
            prerequisites="Teacher-reviewed placement; synthetic description.",
        )
        classes[key] = regular_class
        db.add(
            ClassSession(
                id=demo_id(f"{key}_session"),
                regular_class=regular_class,
                starts_at=datetime(2027, 2, day, 18, tzinfo=ZoneInfo(location.timezone)),
                ends_at=datetime(2027, 2, day, 19, tzinfo=ZoneInfo(location.timezone)),
                capacity=12,
            )
        )
    db.add_all(
        [
            Enrolment(
                id=demo_id("alex_enrolment"),
                student=alex,
                regular_class=classes["monday"],
                starts_on=term.starts_on,
                status="active",
            ),
            Enrolment(
                id=demo_id("sam_enrolment"),
                student=sam,
                regular_class=classes["thursday"],
                starts_on=term.starts_on,
                status="active",
            ),
        ]
    )
    conversation = Conversation(id=ids["conversation"], student=alex, subject="Synthetic enquiry")
    for index, (kind, body) in enumerate(
        [
            ("student_email", "Could I attend Thursday instead?"),
            ("student_email", "Actually, Saturday would be better."),
            (
                "assistant_draft",
                "Manually entered draft awaiting staff editing; no booking or send.",
            ),
        ]
    ):
        db.add(
            Message(
                id=demo_id(f"message_{index}"),
                conversation=conversation,
                kind=kind,
                body=body,
                occurred_at=datetime(2027, 2, 7, 10, index, tzinfo=ZoneInfo("Australia/Melbourne")),
            )
        )
    db.flush()
    return {"created": True, "ids": {key: str(value) for key, value in ids.items()}}


def main() -> None:
    engine = make_engine()
    try:
        with Session(engine) as db, db.begin():
            result = seed_demo(db)
        print(json.dumps(result, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
