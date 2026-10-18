"""Verifier as a separate service: recomputes ground truth itself and fails closed."""

import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from verifier_service.app import app as verifier_app
from agents.orchestrator import AgentOrchestrator
from agents.advisor_agent import AdvisorAgent
from engine.calculator import evaluate_scenario
from engine.models import ScenarioInput

S = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
vc = TestClient(verifier_app)


def _briefs():
    a = evaluate_scenario(S)
    adv = AdvisorAgent()
    return adv.generate_operator_brief(S, a), adv.generate_community_brief(S, a)


def test_service_passes_true_briefs_and_flags_tampered_ones():
    op, cm = _briefs()
    body = {"scenario": S.model_dump(mode="json"), "operator_brief": op, "community_brief": cm}
    assert vc.post("/verify/briefs", json=body).json()["status"] == "PASSED"
    body["operator_brief"] = op + "\nPUE of 0.95"
    assert vc.post("/verify/briefs", json=body).json()["status"] == "FLAGGED_MISMATCH"


def test_service_cannot_be_given_ground_truth():
    # The request schema has no field for engine numbers; extra keys are ignored.
    op, cm = _briefs()
    r = vc.post("/verify/briefs", json={"scenario": S.model_dump(mode="json"), "operator_brief": op + "\nPUE of 0.95",
                                        "community_brief": cm, "assessments": {"fake": 1}, "ground_truth": {"pue": 0.95}})
    assert r.json()["status"] == "FLAGGED_MISMATCH"


def test_orchestrator_uses_remote_verifier_when_configured(monkeypatch):
    monkeypatch.setenv("VERIFIER_URL", "http://verifier.test")
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout, headers=None: vc.post(url.replace("http://verifier.test", ""), json=json, headers=headers))
    out = AgentOrchestrator().process_scenario(S)
    assert out["verifier_mode"] == "remote"
    assert out["verification"]["status"] == "PASSED"


def test_remote_verifier_down_fails_closed(monkeypatch):
    monkeypatch.setenv("VERIFIER_URL", "http://127.0.0.1:9")  # nothing listens here
    out = AgentOrchestrator().process_scenario(S)
    assert out["verification"]["status"] == "FLAGGED_MISMATCH"
    assert out["verification"]["signature"].startswith("UNVERIFIED")


def test_default_mode_is_in_process(monkeypatch):
    monkeypatch.delenv("VERIFIER_URL", raising=False)
    assert AgentOrchestrator().process_scenario(S)["verifier_mode"] == "in_process"


def test_google_auth_mode_attaches_bearer_token(monkeypatch):
    from agents.verifier_client import VerifierClient
    monkeypatch.setenv("VERIFIER_URL", "http://verifier.test")
    monkeypatch.setenv("VERIFIER_AUTH", "google")
    import google.oauth2.id_token as idt
    seen = {}
    monkeypatch.setattr(idt, "fetch_id_token", lambda req, aud: seen.setdefault("aud", aud) and "tok")
    assert VerifierClient()._headers() == {"Authorization": "Bearer tok"}
    assert seen["aud"] == "http://verifier.test"


def test_no_auth_headers_by_default(monkeypatch):
    from agents.verifier_client import VerifierClient
    monkeypatch.delenv("VERIFIER_AUTH", raising=False)
    assert VerifierClient()._headers() == {}
