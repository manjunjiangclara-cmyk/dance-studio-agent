"""Independent grounded generation and paired-verification safety contracts."""

from copy import deepcopy

import pytest

from tests.unit.test_generation_evidence import Characters, artifact


def candidate(value, *, claims=None, status="answered"):
    from studio_copilot.documents.generation.contracts import Candidate

    identifier = value["blocks"][0].get("evidence_id", value["blocks"][0].get("id"))
    return Candidate.model_validate(
        dict(
            status=status,
            claims=claims
            if claims is not None
            else [
                dict(
                    id="claim-one",
                    text="The exception carries no fee.",
                    citations=[dict(evidence_id=identifier, quote="Exception: no fee.")],
                )
            ],
            missing_information=[],
            reason_code="supported",
        )
    )


class Provider:
    def __init__(self, output, verification=None):
        self.output = output
        self.verification = verification
        self.generated = []
        self.verified = []

    def generate(self, payload):
        self.generated.append(deepcopy(payload))
        return self.output

    def verify(self, payload, generated):
        self.verified.append((deepcopy(payload), generated))
        if isinstance(self.verification, Exception):
            raise self.verification
        return self.verification


def verification(*, supported=True, status="answered", claim_id="claim-one"):
    from studio_copilot.documents.generation.contracts import Verification

    return Verification.model_validate(
        dict(claims=[dict(claim_id=claim_id, supported=supported)], status=status)
    )


def test_default_generates_once_and_does_not_touch_optional_verifier():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    provider = Provider(candidate(value), RuntimeError("must not run"))
    result = answer(value, Characters(), allow_api=True, provider=provider)
    assert len(provider.generated) == 1
    assert provider.verified == []
    assert result["status"] == "answered"
    assert result["claims"]
    assert "no fee" in result["answer"]
    citation = result["claims"][0]["citations"][0]
    assert citation["document_id"] == value["sources"][0]["document_id"]
    assert citation["revision"] == 1
    start, end = citation["start"], citation["end"]
    assert value["sources"][0]["text"][start:end] == "Exception: no fee."


def test_missing_explicit_api_gate_never_invokes_even_injected_provider():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    provider = Provider(candidate(value))
    with pytest.raises(Exception):
        answer(value, Characters(), provider=provider)
    assert provider.generated == provider.verified == []


def test_no_evidence_abstains_without_writer_or_verifier_calls():
    from studio_copilot.documents.generation.engine import answer

    provider = Provider(None, RuntimeError("must not run"))
    result = answer(
        artifact(blocks=False), Characters(), allow_api=True, verify=True, provider=provider
    )
    assert result["status"] == "abstained"
    assert not result["claims"]
    assert provider.generated == provider.verified == []


@pytest.mark.parametrize("quote", ["Generated heading", "Not in any source"])
def test_generated_prefix_and_fabricated_quote_cannot_be_cited(quote):
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    output = candidate(value)
    output.claims[0].citations[0].quote = quote
    result = answer(value, Characters(), allow_api=True, provider=Provider(output))
    assert result["status"] == "abstained"
    assert result["claims"] == []
    assert "The exception carries" not in result["answer"]


def test_unknown_evidence_id_removes_claim_instead_of_using_other_document():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    output = candidate(value)
    output.claims[0].citations[0].evidence_id = "another-question-or-document"
    result = answer(value, Characters(), allow_api=True, provider=Provider(output))
    assert result["status"] == "abstained"
    assert not result["claims"]


def test_removing_one_invalid_claim_downgrades_answer_to_partial():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    output = candidate(value)
    wrong = output.claims[0].model_copy(deep=True)
    wrong.id = "claim-two"
    wrong.text = "The office refunds all payments."
    wrong.citations[0].quote = "invented refund rule"
    output.claims.append(wrong)
    result = answer(value, Characters(), allow_api=True, provider=Provider(output))
    assert result["status"] == "partial"
    assert [claim["id"] for claim in result["claims"]] == ["claim-one"]
    assert "refunds" not in result["answer"]


def test_pair_reuses_exact_single_writer_result_and_verifies_only_once():
    from studio_copilot.documents.generation.engine import paired

    value = artifact()
    output = candidate(value)
    provider = Provider(output, verification(supported=False, status="abstained"))
    result = paired(value, Characters(), allow_api=True, provider=provider)
    assert len(provider.generated) == len(provider.verified) == 1
    assert result["baseline"]["status"] == "answered"
    assert result["baseline"]["claims"]
    assert result["verified"]["status"] == "abstained"
    assert not result["verified"]["claims"]
    # Branching must not mutate the baseline into the verifier's reduced answer.
    assert output.claims[0].text == "The exception carries no fee."


def test_verifier_cannot_upgrade_partial_writer_answer():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    provider = Provider(candidate(value, status="partial"), verification(status="answered"))
    result = answer(value, Characters(), allow_api=True, verify=True, provider=provider)
    assert result["status"] != "answered"
    assert result["execution_status"] == "failed"
    assert result["error_code"] == "invalid_verification"


def test_verifier_can_request_clarification_without_introducing_facts():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    provider = Provider(candidate(value), verification(status="needs_clarification"))
    result = answer(value, Characters(), allow_api=True, verify=True, provider=provider)
    assert result["status"] == "needs_clarification"
    assert len(result["claims"]) <= 1
    assert all(item["text"] == "The exception carries no fee." for item in result["claims"])


def test_verification_failure_is_technical_failure_without_baseline_fallback():
    from studio_copilot.documents.generation.engine import paired

    value = artifact()
    provider = Provider(candidate(value), RuntimeError("secret sentinel"))
    result = paired(value, Characters(), allow_api=True, provider=provider)
    assert result["baseline"]["status"] == "answered"
    assert result["verified"]["execution_status"] == "failed"
    assert result["verified"]["claims"] == []
    assert result["verified"]["answer"] == ""
    assert "secret sentinel" not in str(result)
    assert len(provider.generated) == len(provider.verified) == 1


def test_verifier_unknown_claim_ids_cannot_inject_new_content():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    provider = Provider(candidate(value), verification(claim_id="invented"))
    result = answer(value, Characters(), allow_api=True, verify=True, provider=provider)
    assert result["execution_status"] == "failed"
    assert not result["claims"]


def test_tampered_source_date_fails_before_any_model_call():
    from studio_copilot.documents.generation.engine import answer
    from studio_copilot.documents.generation.evidence import seal_artifact

    value = artifact()
    value["as_of"] = "2028-01-01"
    value = seal_artifact(value)
    provider = Provider(None)
    with pytest.raises(Exception):
        answer(value, Characters(), allow_api=True, provider=provider)
    assert provider.generated == provider.verified == []


@pytest.mark.parametrize("verdicts", [[], [True, False]])
def test_missing_or_duplicate_verdict_fails_closed(verdicts):
    from studio_copilot.documents.generation.contracts import Verification
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    check = Verification(
        claims=[dict(claim_id="claim-one", supported=supported) for supported in verdicts],
        status="answered",
    )
    provider = Provider(candidate(value), check)
    result = answer(value, Characters(), allow_api=True, verify=True, provider=provider)
    assert result["execution_status"] == "failed"
    assert result["error_code"] == "invalid_verification"
    assert result["claims"] == []
    assert len(provider.generated) == len(provider.verified) == 1


def test_invalid_artifact_is_rejected_before_constructing_sdk(monkeypatch):
    from studio_copilot.documents.generation import engine

    value = artifact()
    value["question"] = "tampered question"
    monkeypatch.setattr(
        engine, "GenerationProvider", lambda: pytest.fail("SDK constructed for invalid artifact")
    )
    with pytest.raises(Exception):
        engine.answer(value, Characters(), allow_api=True)


def test_api_gate_is_checked_before_constructing_sdk(monkeypatch):
    from studio_copilot.documents.generation import engine

    monkeypatch.setattr(
        engine, "GenerationProvider", lambda: pytest.fail("SDK constructed without API permission")
    )
    with pytest.raises(Exception):
        engine.answer(artifact(), Characters())


def test_writer_exception_is_one_failed_attempt_not_business_abstention():
    from studio_copilot.documents.generation.engine import paired

    class Failing(Provider):
        def generate(self, payload):
            self.generated.append(payload)
            raise RuntimeError("secret sentinel")

    provider = Failing(None)
    result = paired(artifact(), Characters(), allow_api=True, provider=provider)
    assert result["baseline"]["execution_status"] == "failed"
    assert result["verified"]["execution_status"] == "failed"
    assert result["baseline"]["status"] is None
    assert result["baseline"]["answer"] == ""
    assert "secret sentinel" not in str(result)
    assert len(provider.generated) == 1
    assert provider.verified == []


def test_invalid_quote_cannot_hide_behind_needs_clarification():
    from studio_copilot.documents.generation.engine import answer

    value = artifact()
    output = candidate(value, status="needs_clarification")
    output.claims[0].citations[0].quote = "not in source"
    result = answer(value, Characters(), allow_api=True, provider=Provider(output))
    assert result["status"] == "abstained"
    assert result["claims"] == []
