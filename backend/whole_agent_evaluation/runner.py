"""Fixture validation, case execution, and durable partial reports."""

import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta
from datetime import time as clock_time
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from evaluations.runner import database_snapshot
from integrated_rag_evaluation.execute import (
    BudgetEmbedder,
    BudgetModel,
    BudgetWriter,
    check_response,
    isolated_database,
    prepare_documents,
)
from integrated_rag_evaluation.runner import BudgetExceeded
from studio_copilot.agent.service import AgentService
from studio_copilot.api.app import create_app
from studio_copilot.documents import online
from studio_copilot.persistence.models import (
    ClassSession,
    Conversation,
    Enrolment,
    Location,
    Message,
    SessionAttendance,
    Student,
    StudioClass,
    Term,
)

ZONE = ZoneInfo("Australia/Melbourne")
PHASES = {"smoke": 5, "everyday": 100, "high_risk": 25}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode())


def load_suite(root):
    """Verify every frozen byte before any paid call or database mutation."""
    root = Path(root)
    manifest_raw = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get("version") != "whole-agent-validation-v1":
        raise ValueError("Unsupported whole-agent validation version")
    files = manifest.get("files", {})
    if not isinstance(files, dict) or not files:
        raise ValueError("Frozen file hashes are required")
    for relative, expected in files.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ValueError("Unsafe fixture path")
        if sha256((root / path).read_bytes()) != expected:
            raise ValueError(f"Frozen fixture changed: {relative}")
    cases = {}
    ids = set()
    for phase, count in PHASES.items():
        if f"{phase}.json" not in files:
            raise ValueError(f"Missing frozen {phase}.json")
        value = json.loads((root / f"{phase}.json").read_text())
        if isinstance(value, dict):
            value = value.get("cases")
        if not isinstance(value, list) or len(value) != count:
            raise ValueError(f"Expected {count} {phase} cases")
        for case in value:
            if not isinstance(case.get("id"), str) or not case["id"] or case["id"] in ids:
                raise ValueError("Case IDs must be nonempty and unique")
            ids.add(case["id"])
            date.fromisoformat(case["as_of"])
            if not case.get("message") or not isinstance(case.get("expected"), dict):
                raise ValueError("Case message and expectation required")
        cases[phase] = value
    if "business.json" not in files:
        raise ValueError("Missing frozen business.json")
    business = json.loads((root / "business.json").read_text())
    documents = []
    for source in manifest.get("documents", []):
        relative = source["file"]
        if relative not in files or files[relative] != source["sha256"]:
            raise ValueError("Document hash missing from frozen manifest")
        documents.append(
            {**source, "file": Path(relative).name, "text": (root / relative).read_text()}
        )
    for phase_cases in cases.values():
        for case in phase_cases:
            referenced = case.get("setup", {}).get("document_keys")
            if referenced and not set(referenced) <= {doc["key"] for doc in documents}:
                raise ValueError("Unknown case document key")
    return manifest, business, documents, cases, sha256(manifest_raw)


def seed_case(engine, case, business):
    """Create only fictional records in the disposable evaluation schema."""
    setup = case.get("setup") or {}
    as_of = date.fromisoformat(case["as_of"])
    students = {row["key"]: row for row in business.get("students", [])}
    classes = {row["key"]: row for row in business.get("classes", [])}
    absences = {row["key"]: row for row in business.get("absences", [])}
    student_spec = students.get(setup.get("student_key"))
    name = student_spec["display_name"] if student_spec else "New enquirer"
    email = f"whole-agent-{case['id']}@example.com"
    with Session(engine) as db, db.begin():
        student = Student(display_name=name, email=email)
        db.add(student)
        db.flush()
        term = Term(
            name=f"Evaluation {case['id']}",
            starts_on=as_of - timedelta(days=60),
            ends_on=as_of + timedelta(days=120),
        )
        location = Location(
            name=f"Evaluation Studio {case['id']}",
            address="Fictional address",
            timezone="Australia/Melbourne",
        )
        db.add_all([term, location])
        db.flush()
        # Keep the whole fictional class catalogue available to the real agent.
        selected = set(classes)
        if setup.get("class_key"):
            selected.add(setup["class_key"])
        absence = absences.get(setup.get("absence_key"))
        if absence:
            selected.add(absence["class_key"])
        for key in sorted(selected):
            spec = classes[key]
            cls = StudioClass(
                name=spec["name"], level=spec.get("level", "Level 2"), term=term, location=location
            )
            db.add(cls)
            db.flush()
            if key in (student_spec.get("enrolled_class_keys", []) if student_spec else []):
                db.add(
                    Enrolment(
                        student=student,
                        regular_class=cls,
                        starts_on=term.starts_on,
                        status="active",
                    )
                )
            if absence and key == absence["class_key"]:
                start = datetime.fromisoformat(absence["starts_at"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=ZONE)
            else:
                start = datetime.combine(as_of + timedelta(days=7), clock_time(18), ZONE)
            booked = spec.get("booked", 0)
            if not isinstance(booked, int) or booked < 0:
                raise ValueError("Fictional booked count must be nonnegative")
            roster = []
            for index in range(booked):
                member = Student(
                    display_name=f"Fictional roster member {index + 1}",
                    email=f"roster-{case['id']}-{key}-{index}@example.com",
                )
                db.add(member)
                db.flush()
                roster.append(member.id)
            if setup.get("student_key") and any(
                booking.get("student_key") == setup["student_key"]
                and booking.get("class_key") == key
                and booking.get("status") in {"confirmed", "booked", "active"}
                for booking in business.get("bookings", [])
            ):
                roster.append(student.id)
            session = ClassSession(
                regular_class=cls,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                capacity=spec.get("capacity", 12),
                students=roster,
            )
            db.add(session)
            db.flush()
            if (
                absence
                and key == absence["class_key"]
                and absence.get("status") in {"absent", "attended"}
            ):
                db.add(
                    SessionAttendance(
                        session_id=session.id,
                        student_id=student.id,
                        status=absence["status"],
                        level_at_attendance=cls.level,
                    )
                )
        conversation = Conversation(student=student)
        message = Message(
            conversation=conversation,
            kind="student_email",
            body=case["message"],
            occurred_at=datetime.combine(as_of, clock_time(12), ZONE),
        )
        db.add(message)
        db.flush()
        return str(conversation.id), str(message.id)


def clear_case(engine):
    """Remove all case-owned records, retaining only the activated document corpus."""
    with engine.begin() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
        if not schema or not schema.startswith(("rag_eval_", "test_")):
            raise RuntimeError("Refusing case cleanup outside a disposable evaluation schema")
        tables = (
            "agent_runs, messages, conversations, session_attendance, enrolments, "
            "class_sessions, classes, students, terms, locations"
        )
        checkpoint_tables = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")
        owners = [
            connection.scalar(
                text(
                    "SELECT n.nspname FROM pg_class c JOIN pg_namespace n "
                    "ON c.relnamespace=n.oid WHERE c.oid=to_regclass(:name)"
                ),
                {"name": name},
            )
            for name in checkpoint_tables
        ]
        if any(owner and owner != schema for owner in owners):
            raise RuntimeError("Refusing checkpoint cleanup outside the owned schema")
        if all(owner == schema for owner in owners):
            tables += ", " + ", ".join(checkpoint_tables)
        connection.execute(text("TRUNCATE TABLE " + tables))
        remaining = connection.scalar(text("SELECT count(*) FROM classes"))
        if remaining:
            raise RuntimeError("Case cleanup left business rows behind")


def run_case(client, engine, case, business, budget, model):
    conversation_id, source_id = seed_case(engine, case, business)
    before = database_snapshot(engine)
    previous_calls = len(model.calls)
    previous_failures = len(model.failures)
    started = time.monotonic()
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/agent-runs", json={"source_message_id": source_id}
    )
    elapsed = round((time.monotonic() - started) * 1000)
    run = check_response(response)
    all_evidence = run.get("evidence", [])
    evidence = [item for item in all_evidence if item.get("tool") == "document_answer"]
    draft = run.get("draft_details") or {}
    failures = model.failures[previous_failures:] + [
        call["operation"] for call in model.calls[previous_calls:] if not call["completed"]
    ]
    failures += [
        item.get("result", {}).get("error_code", "document_answer_failed")
        for item in evidence
        if item.get("result", {}).get("status") == "failed"
    ]
    failure_stages = []
    for failure in failures:
        label = str(failure)
        if label in {"retrieval_failed", "reranking_failed", "source_changed", "source_missing"}:
            failure_stages.append("retrieval")
        elif "compose" in label:
            failure_stages.append("composition")
        elif "answer" in label or "provider" in label:
            failure_stages.append("answer")
        else:
            failure_stages.append("agent")
    unchanged = before == database_snapshot(engine)
    row = {
        "id": case["id"],
        "category": case["category"],
        "risk_type": case.get("risk_type"),
        "status": "completed"
        if run["status"] == "awaiting_review" and not failures and unchanged
        else "failed",
        "run_status": run["status"],
        "run_id": run["id"],
        "source_message_id": source_id,
        "message": case["message"],
        "as_of": case["as_of"],
        "expected": case["expected"],
        "draft": draft,
        "evidence": all_evidence,
        "document_evidence": evidence,
        "interpretation": run.get("interpretation"),
        "technical_failures": failures,
        "failure_stages": sorted(set(failure_stages)),
        "no_business_change": unchanged,
        # This runner calls document setup and start-run only; the app has no delivery integration.
        "no_email_delivery": True,
        "latency_ms": elapsed,
        "budget": budget.snapshot(),
        "review": None,
    }
    row["output_sha256"] = canonical_hash(
        {"draft": draft, "evidence": all_evidence, "interpretation": row["interpretation"]}
    )
    return row


def summarize(rows, expected_count):
    by_category = {}
    by_risk_type = {}
    for row in rows:
        category = row.get("category", "unknown")
        bucket = by_category.setdefault(category, {"completed": 0, "failed": 0})
        bucket["completed" if row.get("status") == "completed" else "failed"] += 1
        if row.get("risk_type"):
            risk_bucket = by_risk_type.setdefault(row["risk_type"], {"completed": 0, "failed": 0})
            risk_bucket["completed" if row.get("status") == "completed" else "failed"] += 1
    return {
        "expected": expected_count,
        "attempted": len(rows),
        "completed": sum(row.get("status") == "completed" for row in rows),
        "failed": sum(row.get("status") != "completed" for row in rows),
        "categories": by_category,
        "risk_types": by_risk_type,
    }


def execute(
    url,
    selected_cases,
    business,
    documents,
    budget,
    output,
    *,
    manifest_hash,
    phase,
    expected_count,
):
    rows = []
    report = {
        "version": "whole-agent-report-v1",
        "fixture_manifest_sha256": manifest_hash,
        "phase": phase,
        "model": os.environ["OPENAI_MODEL"],
        "results": rows,
        "sources": [],
        "error_type": None,
    }

    def save():
        report["summary"] = summarize(rows, expected_count)
        report["budget"] = budget.snapshot()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")

    save()
    BudgetEmbedder.budget = BudgetWriter.budget = budget
    model = None
    try:
        with isolated_database(url) as engine:
            model = BudgetModel(budget)
            app = create_app(
                engine,
                admin_token="fictional-whole-agent-evaluation",
                agent_service=AgentService(engine, model),
            )
            with (
                patch.object(online, "Embedder", BudgetEmbedder),
                patch.object(online, "GenerationProvider", BudgetWriter),
                TestClient(
                    app, headers={"Authorization": "Bearer fictional-whole-agent-evaluation"}
                ) as client,
            ):
                report["sources"] = prepare_documents(
                    client, engine, budget, source_documents=documents
                )
                save()
                for case in selected_cases:
                    if budget.exhausted:
                        break
                    try:
                        row = run_case(client, engine, case, business, budget, model)
                    except BudgetExceeded:
                        row = {
                            "id": case["id"],
                            "category": case["category"],
                            "risk_type": case.get("risk_type"),
                            "status": "failed",
                            "error_type": "BudgetExceeded",
                        }
                        budget.exhausted = True
                    except Exception as error:
                        row = {
                            "id": case["id"],
                            "category": case["category"],
                            "risk_type": case.get("risk_type"),
                            "status": "failed",
                            "error_type": type(error).__name__,
                        }
                    rows.append(row)
                    save()
                    try:
                        clear_case(engine)
                    except Exception as error:
                        report["error_type"] = f"case_cleanup:{type(error).__name__}"
                        save()
                        break
    except Exception as error:
        report["error_type"] = type(error).__name__
        save()
    finally:
        if model is not None:
            model.client.close()
        save()
    return report
