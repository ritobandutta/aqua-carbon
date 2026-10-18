"""Coverage check changes indicator confidence; run_id is reproducible."""

from fastapi.testclient import TestClient
from api.main import app
from engine.calculator import evaluate_scenario
from engine.coverage import run_coverage_check, apply_coverage_to_assessments
from engine.models import ScenarioInput, DataConfidence
from engine import data_sources

client = TestClient(app)


def test_coverage_gap_lowers_dependent_indicators(monkeypatch):
    # Pretend the headroom value was verified (HIGH) so a downgrade is observable.
    monkeypatch.setitem(data_sources.VALUE_STATUS, "water_headroom", "published")
    s = ScenarioInput(region="bengaluru")
    a = evaluate_scenario(s)
    before = a["evaporative"].community_ledger.water_headroom_share_pct.confidence
    assert before == DataConfidence.MEDIUM
    assert apply_coverage_to_assessments(a, run_coverage_check("bengaluru")) is True
    ind = a["evaporative"].community_ledger.water_headroom_share_pct
    assert ind.confidence == DataConfidence.LOW and "Coverage check" in ind.explanation


def test_no_gap_leaves_confidence_alone():
    a = evaluate_scenario(ScenarioInput(region="bengaluru"))
    cov = run_coverage_check("bengaluru")
    cov.disparity_ratio = 1.0
    assert apply_coverage_to_assessments(a, cov) is False


def test_run_id_is_reproducible_and_input_sensitive():
    body = {"region": "bengaluru", "it_capacity_mw": 15.0}
    r1, r2 = client.post("/api/scenario/evaluate", json=body).json(), client.post("/api/scenario/evaluate", json=body).json()
    assert r1["run_id"] == r2["run_id"] and len(r1["run_id"]) == 16
    r3 = client.post("/api/scenario/evaluate", json={**body, "it_capacity_mw": 20.0}).json()
    assert r3["run_id"] != r1["run_id"]
