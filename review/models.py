"""Shared data contracts for the permit-review use case."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from engine.claims import ClaimScenario
from engine.models import CoolingType, VerificationReport


class ClaimInput(BaseModel):
    cooling_type: CoolingType
    metric: str
    claimed_value: float


class ReviewRequest(BaseModel):
    scenario: ClaimScenario
    applicant_text: str = ""
    claims: List[ClaimInput] = Field(default_factory=list)


class VerifyReviewRequest(BaseModel):
    """What the A2A verifier receives. It gets the scenario and the claims, never trusted numbers: it
    recomputes the engine output itself."""
    scenario: ClaimScenario
    claims_source: Literal["text", "structured"]
    applicant_text: str = ""
    claims: List[ClaimInput]
    reported_verdicts: List[dict]
    review_text: str


class ReviewResponse(BaseModel):
    status: Literal["verified", "blocked_unverified", "no_claims"]
    mode: Literal["agentic", "structured"]
    review_source: Literal["gemini", "template", "none"]
    llm_draft_blocked: bool = False
    claims: List[ClaimInput] = Field(default_factory=list)
    verdicts: List[dict] = Field(default_factory=list)
    review_markdown: str = ""
    verification: Optional[VerificationReport] = None
    provenance: dict = Field(default_factory=dict)
    notice: str = ""
