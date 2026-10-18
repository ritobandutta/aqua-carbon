"""
Verifier and investigator regression tests.
Covers: per-metric tamper detection, fabricated claims, deterministic signatures,
and the investigator fallback path when no Gemini key is configured.
"""

import asyncio
import pytest
from engine.models import ScenarioInput, Season, WorkloadType
from engine.calculator import evaluate_scenario
from agents.advisor_agent import AdvisorAgent
from agents.verifier_agent import VerifierAgent, extract_claims
from agents.orchestrator import AgentOrchestrator

SCENARIOS = [
    ScenarioInput(it_capacity_mw=15.0, region="bengaluru"),
    ScenarioInput(it_capacity_mw=35.0, region="bengaluru", season=Season.DRY_SUMMER),
    ScenarioInput(it_capacity_mw=8.0, region="chennai", season=Season.MONSOON),
    ScenarioInput(it_capacity_mw=20.0, region="mumbai", workload_type=WorkloadType.AI_TRAINING_FLEXIBLE),
]


def _briefs(scenario):
    a = evaluate_scenario(scenario)
    adv = AdvisorAgent()
    return a, adv.generate_operator_brief(scenario, a), adv.generate_community_brief(scenario, a)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_untampered_briefs_pass_in_every_scenario(scenario):
    a, op, cm = _briefs(scenario)
    report = VerifierAgent().verify_briefs(op, cm, a)
    assert report.status == "PASSED", [c.discrepancy_note for c in report.checks if not c.matched]


def test_every_single_metric_corruption_is_caught():
    s = SCENARIOS[0]
    a, op, cm = _briefs(s)
    v = VerifierAgent()
    for key, asm in a.items():
        fl = asm.facility_ledger
        for original in (
            f"{fl.pue:.2f}",
            f"{fl.direct_water_consumption_ml:.1f}",
            f"{fl.scope2_carbon_tonnes:,.0f}",
            f"{fl.annual_operating_cost_inr_crores:.2f}",
        ):
            raw = float(original.replace(",", ""))
            corrupted = f"{raw * 1.15:.2f}"
            op2, cm2 = op.replace(original, corrupted), cm.replace(original, corrupted)
            if (op2, cm2) == (op, cm):
                continue
            assert v.verify_briefs(op2, cm2, a).status != "PASSED", f"missed {key}: {original}->{corrupted}"


def test_fabricated_extra_claim_is_flagged():
    a, op, cm = _briefs(SCENARIOS[0])
    fake = op + "\n\nDry cooling actually achieves PUE of 0.95 using 1.0 ML of water and 2 MWh."
    assert VerifierAgent().verify_briefs(fake, cm, a).status == "FLAGGED_MISMATCH"


def test_signature_is_deterministic_and_tracks_status():
    a, op, cm = _briefs(SCENARIOS[0])
    v = VerifierAgent()
    r1, r2 = v.verify_briefs(op, cm, a), v.verify_briefs(op, cm, a)
    assert r1.signature == r2.signature
    bad = v.verify_briefs(op + "\nPUE of 0.95", cm, a)
    assert bad.signature != r1.signature and bad.signature.startswith("FLAGGED")


def test_extract_claims_ignores_unit_less_numbers():
    assert extract_claims("Phase 3 of 5 in 2026 with 12 people") == []


def test_investigator_works_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = SCENARIOS[0]
    a = evaluate_scenario(s)
    for q in ("why does dry cooling strain the grid?", "give me a summary"):
        r = asyncio.run(AgentOrchestrator().answer_investigation_query(q, s, a))
        assert r["source"] == "deterministic_template"
        assert r["verification_status"] == "PASSED"
        assert r["explanation_markdown"]


def test_investigator_blocks_a_hallucinating_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    s = SCENARIOS[0]
    a = evaluate_scenario(s)
    orch = AgentOrchestrator()
    monkeypatch.setattr(orch, "_call_gemini", lambda prompt: "Evaporative cooling reaches a PUE of 0.99 and uses 3.0 ML.")
    r = asyncio.run(orch.answer_investigation_query("why?", s, a))
    assert r["gemini_draft_blocked"] is True
    assert r["source"] == "deterministic_template"
    assert r["verification_status"] == "PASSED"


def test_investigator_accepts_a_faithful_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    s = SCENARIOS[0]
    a = evaluate_scenario(s)
    orch = AgentOrchestrator()
    pue = a["evaporative"].facility_ledger.pue
    monkeypatch.setattr(orch, "_call_gemini", lambda prompt: f"Evaporative cooling runs at a PUE of {pue:.2f}.")
    r = asyncio.run(orch.answer_investigation_query("why?", s, a))
    assert r["source"] == "gemini" and r["gemini_draft_blocked"] is False
