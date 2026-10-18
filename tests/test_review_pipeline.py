"""Permit-review pipeline: structured and agentic modes, MCP over HTTP, A2A between real processes."""

import asyncio
import pytest
pytest.importorskip("google.adk")
from fastapi.testclient import TestClient
from api.main import app
from engine.claims import ClaimScenario, check_claim
from engine.models import CoolingType
from review.models import ClaimInput, ReviewRequest
from review.service import ReviewService, ReviewError
from tests.scripted_llm import ScriptedLlm

SC = ClaimScenario(region="bengaluru", it_capacity_mw=15.0)
H = CoolingType.HYBRID_ADIABATIC
TEXT = "The hybrid adiabatic design will use 40 ML of water per year."


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("GEMINI_API_KEY", "MCP_URL", "A2A_VERIFIER_URL", "GOOGLE_GENAI_USE_VERTEXAI", "VERIFIER_URL"):
        monkeypatch.delenv(k, raising=False)


def run(coro):
    return asyncio.run(coro)


def structured(value=40.0, metric="direct_water_ml"):
    return ReviewRequest(scenario=SC, claims=[ClaimInput(cooling_type=H, metric=metric, claimed_value=value)])


def test_structured_in_process():
    r = run(ReviewService().review(structured()))
    assert r.status == "verified" and r.mode == "structured"
    assert r.verdicts[0]["verdict"] == "below_modelled_range"
    assert "Questions for the applicant" in r.review_markdown and r.provenance["a2a_verifier"] == "in_process"


def test_structured_over_real_mcp_http(mcp_url, monkeypatch):
    monkeypatch.setenv("MCP_URL", mcp_url)
    r = run(ReviewService().review(structured()))
    assert r.status == "verified" and r.provenance["mcp"] == mcp_url


def test_structured_over_real_a2a_process(a2a_verifier_url, monkeypatch):
    monkeypatch.setenv("A2A_VERIFIER_URL", a2a_verifier_url)
    r = run(ReviewService().review(structured()))
    assert r.status == "verified" and r.provenance["verification"] == "a2a_remote"
    assert r.verification.signature.startswith("VERIFIED")


def test_a2a_down_fails_closed(monkeypatch):
    monkeypatch.setenv("A2A_VERIFIER_URL", "http://127.0.0.1:9")
    r = run(ReviewService().review(structured()))
    assert r.status == "blocked_unverified" and r.review_markdown == "" and r.verdicts == []
    assert r.verification.signature.startswith("UNVERIFIED")


def test_agentic_extracts_claims_and_uses_mcp_tools(mcp_url, a2a_verifier_url, monkeypatch):
    monkeypatch.setenv("MCP_URL", mcp_url); monkeypatch.setenv("A2A_VERIFIER_URL", a2a_verifier_url)
    llm = ScriptedLlm(extract={"claims": [{"cooling_type": "hybrid_adiabatic", "metric": "direct_water_ml", "claimed_value": 40.0}]})
    r = run(ReviewService(model=llm).review(ReviewRequest(scenario=SC, applicant_text=TEXT)))
    assert r.status == "verified" and r.mode == "agentic"
    assert r.claims[0].claimed_value == 40.0 and r.verdicts[0]["verdict"] == "below_modelled_range"
    assert r.provenance["verification"] == "a2a_remote"


def test_agentic_invented_claim_is_blocked(a2a_verifier_url, monkeypatch):
    """The 'model' extracts 12 ML, which the applicant never wrote. The verifier must catch it."""
    monkeypatch.setenv("A2A_VERIFIER_URL", a2a_verifier_url)
    llm = ScriptedLlm(extract={"claims": [{"cooling_type": "hybrid_adiabatic", "metric": "direct_water_ml", "claimed_value": 12.0}]})
    r = run(ReviewService(model=llm).review(ReviewRequest(scenario=SC, applicant_text=TEXT)))
    assert r.status == "blocked_unverified" and r.review_markdown == ""
    assert any("does not appear in the applicant" in (c.discrepancy_note or "") for c in r.verification.checks)


def test_agentic_model_tampering_with_tool_args_is_blocked(monkeypatch):
    """The agent calls the tool with a different value than the one extracted: reported verdict will not match."""
    llm = ScriptedLlm(extract={"claims": [{"cooling_type": "hybrid_adiabatic", "metric": "direct_water_ml", "claimed_value": 40.0}]},
                      mutate_args=lambda a: {**a, "claimed_value": 90.0})
    r = run(ReviewService(model=llm).review(ReviewRequest(scenario=SC, applicant_text=TEXT)))
    assert r.status == "blocked_unverified"


def test_agentic_lazy_model_that_skips_the_tool_is_blocked():
    llm = ScriptedLlm(extract={"claims": [{"cooling_type": "hybrid_adiabatic", "metric": "direct_water_ml", "claimed_value": 40.0}]}, skip_tools=True)
    r = run(ReviewService(model=llm).review(ReviewRequest(scenario=SC, applicant_text=TEXT)))
    assert r.status == "blocked_unverified"


def test_agentic_no_claims_found():
    r = run(ReviewService(model=ScriptedLlm(extract={"claims": []})).review(ReviewRequest(scenario=SC, applicant_text="We care about the environment.")))
    assert r.status == "no_claims" and r.verdicts == []


def test_text_without_a_model_is_a_clear_error():
    with pytest.raises(ReviewError, match="needs a model"):
        run(ReviewService().review(ReviewRequest(scenario=SC, applicant_text=TEXT)))


def test_empty_request_and_bad_metric_are_errors():
    with pytest.raises(ReviewError):
        run(ReviewService().review(ReviewRequest(scenario=SC)))
    with pytest.raises(ReviewError, match="Unknown metric"):
        run(ReviewService().review(structured(metric="vibes")))


def test_api_endpoint_roundtrip_and_errors():
    c = TestClient(app)
    body = {"scenario": {"region": "bengaluru", "it_capacity_mw": 15.0},
            "claims": [{"cooling_type": "hybrid_adiabatic", "metric": "direct_water_ml", "claimed_value": 40.0}]}
    r = c.post("/api/review", json=body)
    assert r.status_code == 200 and r.json()["status"] == "verified"
    assert c.post("/api/review", json={**body, "scenario": {"region": "Delhi", "it_capacity_mw": 15}}).status_code == 404
    assert c.post("/api/review", json={"scenario": body["scenario"]}).status_code == 422
    assert c.post("/api/review", json={"scenario": body["scenario"], "applicant_text": "x"}).status_code == 422
