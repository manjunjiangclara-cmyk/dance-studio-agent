"""Optional paid live interpretation smoke evaluation using synthetic inputs only."""

import json
from uuid import uuid4

from studio_copilot.agent.openai_model import OpenAIModel
from studio_copilot.agent.workflow import select_flow


def main():
    source_id = str(uuid4())
    context = {
        "student": {
            "id": str(uuid4()),
            "name": "Synthetic Alex",
            "highest_level": "Level 2",
            "context": {},
            "ai_summary": None,
        },
        "enrolments": [],
        "policy": {
            "absence_notice_before_start": True,
            "explanation": "Notice must arrive before the session starts; entitlement undefined.",
        },
    }
    first = {
        "id": source_id,
        "kind": "student_email",
        "occurred_at": "2027-02-07T10:00:00+11:00",
        "body": (
            "I will miss my class on 8 February 2027. "
            "Could I make it up on Thursday 11 February 2027?"
        ),
    }
    followup = {
        **first,
        "id": str(uuid4()),
        "occurred_at": "2027-02-07T11:00:00+11:00",
        "body": "Actually, Saturday 13 February 2027 instead.",
    }
    missing = {**first, "id": str(uuid4()), "body": "Could I do a makeup?"}
    model = OpenAIModel()
    results = []
    try:
        for name, source, history, expected in [
            ("explicit_dates", first, [first], "2027-02-11"),
            ("consecutive_correction", followup, [first, followup], "2027-02-13"),
            ("missing_details", missing, [missing], None),
        ]:
            case_context = {**context, "source": source, "history": history}
            routing = model.route(case_context)
            if select_flow(routing) != "makeup":
                results.append({"case": name, "passed": False, "routing": routing.model_dump()})
                continue
            result = model.interpret_makeup({**case_context, "routing": routing.model_dump()})
            passed = result.preferred_date == expected if expected else bool(result.missing_details)
            results.append(
                {
                    "case": name,
                    "passed": passed,
                    "routing": routing.model_dump(),
                    "interpretation": result.model_dump(),
                }
            )
    finally:
        model.client.close()
    print(
        json.dumps(
            {
                "model": model.model,
                "passed": sum(r["passed"] for r in results),
                "total": len(results),
                "results": results,
            },
            indent=2,
        )
    )
    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
