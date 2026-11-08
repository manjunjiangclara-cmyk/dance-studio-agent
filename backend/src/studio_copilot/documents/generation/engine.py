"""Single generation by default; optional paired checking never regenerates or adds facts."""

import copy
import json
import time

from studio_copilot.documents.operations import OperationsError, instrument

from .contracts import Candidate, GenerationError, Verification
from .evidence import model_payload, resolve_quote, validate_artifact
from .provider import GENERATE, VERIFY, GenerationProvider


def require_api(allow_api):
    if not allow_api:
        raise GenerationError(
            "api_permission", "Explicit --allow-api is required for model requests."
        )


def failure(code):
    return dict(
        execution_status="failed",
        status=None,
        claims=[],
        missing_information=[],
        reason_code=None,
        error_code=code,
        answer="",
        verification_applied=False,
    )


def render(result):
    status = result["status"]
    opening = {
        "answered": "",
        "partial": "I can confirm only the following from the supplied documents:",
        "needs_clarification": "I need more details before I can confirm an answer.",
        "abstained": "I cannot confirm an answer from the supplied evidence.",
    }[status]
    parts = [opening] if opening else []
    for claim in result["claims"]:
        refs = list(dict.fromkeys(c["evidence_id"] for c in claim["citations"]))
        parts.append(claim["text"] + " " + " ".join(f"[{ref}]" for ref in refs))
    if status == "partial":
        parts.append("The remaining details cannot be confirmed from this evidence.")
    return "\n\n".join(parts)


def validate_candidate(artifact, candidate):
    candidate = Candidate.model_validate(candidate)
    if len({c.id for c in candidate.claims}) != len(candidate.claims):
        raise GenerationError("invalid_response", "Claim IDs must be unique.")
    kept, invalid = [], []
    valid_citations = total_citations = 0
    for claim in candidate.claims:
        resolved = [resolve_quote(artifact, citation) for citation in claim.citations]
        total_citations += len(resolved)
        valid_citations += sum(c is not None for c in resolved)
        if not claim.text.strip() or any(c is None for c in resolved):
            invalid.append(claim.id)
        else:
            kept.append(dict(id=claim.id, text=claim.text.strip(), citations=resolved))
    status = candidate.status
    if status == "abstained":
        kept = []
    if not kept and status != "needs_clarification":
        status = "abstained"
    if invalid and candidate.status != "abstained":
        status = "partial" if kept else "abstained"
    result = dict(
        execution_status="completed",
        status=status,
        claims=kept,
        missing_information=candidate.missing_information,
        reason_code="invalid_citations" if invalid else candidate.reason_code,
        invalid_claim_ids=invalid,
        citation_counts=dict(valid=valid_citations, total=total_citations),
        verification_applied=False,
    )
    result["answer"] = render(result)
    return result


def apply_verification(baseline, verification):
    verification = Verification.model_validate(verification)
    verdicts = {v.claim_id: v.supported for v in verification.claims}
    expected = {c["id"] for c in baseline["claims"]}
    if len(verdicts) != len(verification.claims) or set(verdicts) != expected:
        raise GenerationError(
            "invalid_verification", "Verifier must judge each supplied claim once."
        )
    allowed = {
        "answered": {"answered", "partial", "needs_clarification", "abstained"},
        "partial": {"partial", "needs_clarification", "abstained"},
        "needs_clarification": {"needs_clarification", "abstained"},
        "abstained": {"abstained"},
    }
    if verification.status not in allowed[baseline["status"]]:
        raise GenerationError(
            "invalid_verification", "Verifier cannot upgrade the writer's status."
        )
    result = copy.deepcopy(baseline)
    result["claims"] = [c for c in result["claims"] if verdicts[c["id"]]]
    result["status"] = verification.status
    removed = len(result["claims"]) != len(baseline["claims"])
    if result["status"] == "abstained":
        result["claims"] = []
    elif not result["claims"] and result["status"] != "needs_clarification":
        result["status"] = "abstained"
    elif removed and result["status"] == "answered":
        result["status"] = "partial"
    result["verification_applied"] = True
    result["verification"] = verification.model_dump(mode="json")
    if removed:
        result["reason_code"] = "verification_removed_claims"
    result["answer"] = render(result)
    return result


def _run(artifact, tokenizer, *, allow_api=False, verify=False, provider=None):
    require_api(allow_api)
    validate_artifact(artifact, tokenizer)
    started = time.perf_counter()
    report = dict(
        case_id=artifact["case_id"],
        variant=artifact["variant"],
        artifact_sha256=artifact["artifact_sha256"],
        raw_candidate=None,
        baseline=None,
        verified=None,
    )
    if not artifact["blocks"]:
        result = dict(
            execution_status="completed",
            status="abstained",
            claims=[],
            missing_information=[],
            reason_code="no_applicable_evidence",
            citation_counts=dict(valid=0, total=0),
            invalid_claim_ids=[],
            verification_applied=False,
        )
        result["answer"] = render(result)
        report.update(
            baseline=result,
            verified=copy.deepcopy(result) if verify else None,
            calls=[],
            real_provider=False,
            model=None,
            seconds=time.perf_counter() - started,
        )
        return report
    model = provider
    try:
        model = provider if provider is not None else GenerationProvider()
        payload = model_payload(artifact)
        if tokenizer.count(GENERATE + json.dumps(payload, ensure_ascii=False)) > 20000:
            raise GenerationError(
                "request_limit", "Generation request exceeds its local token budget."
            )
        candidate = Candidate.model_validate(model.generate(copy.deepcopy(payload)))
        report["raw_candidate"] = candidate.model_dump(mode="json")
        report["baseline"] = validate_candidate(artifact, candidate)
    except Exception as error:
        code = (
            error.code
            if isinstance(error, (GenerationError, OperationsError))
            else "generation_failed"
        )
        report["baseline"] = failure(code)
        if verify:
            report["verified"] = failure(code)
    if verify and report["baseline"]["execution_status"] == "completed":
        try:
            baseline = report["baseline"]
            checked = Candidate(
                status=baseline["status"],
                claims=[
                    dict(
                        id=c["id"],
                        text=c["text"],
                        citations=[
                            dict(evidence_id=q["evidence_id"], quote=q["quote"])
                            for q in c["citations"]
                        ],
                    )
                    for c in baseline["claims"]
                ],
                missing_information=baseline["missing_information"],
                reason_code=baseline["reason_code"],
            )
            if (
                tokenizer.count(
                    VERIFY
                    + json.dumps(
                        dict(payload, candidate=checked.model_dump(mode="json")), ensure_ascii=False
                    )
                )
                > 20000
            ):
                raise GenerationError(
                    "request_limit", "Verification request exceeds its local token budget."
                )
            verdict = model.verify(copy.deepcopy(payload), checked.model_copy(deep=True))
            report["verified"] = apply_verification(baseline, verdict)
        except Exception as error:
            report["verified"] = failure(
                error.code
                if isinstance(error, (GenerationError, OperationsError))
                else "verification_failed"
            )
    report.update(
        calls=copy.deepcopy(getattr(model, "calls", [])),
        real_provider=getattr(model, "real_provider", False),
        model=getattr(model, "model", None),
        seconds=time.perf_counter() - started,
    )
    return report


@instrument("generation")
def answer(artifact, tokenizer, *, allow_api=False, verify=False, provider=None):
    report = _run(artifact, tokenizer, allow_api=allow_api, verify=verify, provider=provider)
    return dict(
        report["verified"] if verify else report["baseline"],
        calls=report["calls"],
        model=report["model"],
        seconds=report["seconds"],
        artifact_sha256=report["artifact_sha256"],
        case_id=artifact["case_id"],
        variant=artifact["variant"],
        real_provider=report["real_provider"],
        raw_candidate=report["raw_candidate"],
    )


@instrument("generation")
def paired(artifact, tokenizer, *, allow_api=False, provider=None):
    return _run(artifact, tokenizer, allow_api=allow_api, verify=True, provider=provider)
