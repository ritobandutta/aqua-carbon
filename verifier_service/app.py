"""
Standalone verifier service. Run separately from the main API:
    uvicorn verifier_service.app:app --port 8100

Independence: the caller sends the scenario and the text to check, never the numbers to check
against. This service recomputes the engine output itself, so a compromised or buggy caller cannot
supply favourable ground truth. It imports only the engine and the verifier, never the advisor,
the orchestrator or any prompt.
"""

from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from engine.models import ScenarioInput, VerificationReport
from engine.calculator import evaluate_scenario
from agents.verifier_agent import VerifierAgent

app = FastAPI(title="AquaCarbon DC verifier", version="1.0.0")
_verifier = VerifierAgent()


class VerifyBriefsRequest(BaseModel):
    scenario: ScenarioInput
    operator_brief: str
    community_brief: str


class VerifyTextRequest(BaseModel):
    scenario: ScenarioInput
    text: str


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "aquacarbon-verifier"}


@app.post("/verify/briefs", response_model=VerificationReport)
async def verify_briefs(req: VerifyBriefsRequest):
    assessments = evaluate_scenario(req.scenario)
    return _verifier.verify_briefs(req.operator_brief, req.community_brief, assessments)


@app.post("/verify/text", response_model=VerificationReport)
async def verify_text(req: VerifyTextRequest):
    return _verifier.verify_text(req.text, evaluate_scenario(req.scenario))
