"""Bounded structured output contracts; quote strings preserve original Unicode."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["answered", "partial", "needs_clarification", "abstained"]


class GenerationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(Strict):
    evidence_id: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=2000)


class Claim(Strict):
    id: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=1000)
    citations: list[Citation] = Field(min_length=1, max_length=4)


class Candidate(Strict):
    status: Status
    claims: list[Claim] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=8)
    reason_code: str = Field(min_length=1, max_length=80)


class Verdict(Strict):
    claim_id: str = Field(min_length=1, max_length=40)
    supported: bool


class Verification(Strict):
    claims: list[Verdict] = Field(max_length=12)
    status: Status
