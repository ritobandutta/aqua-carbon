"""Unknown regions must fail loudly instead of silently falling back to Bengaluru."""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from engine.calculator import evaluate_scenario
from engine.data_sources import resolve_region_key, UnknownRegionError
from engine.models import ScenarioInput, DataConfidence

client = TestClient(app)


def test_free_text_region_resolves():
    assert resolve_region_key("Bengaluru, Karnataka, India") == "bengaluru"
    assert resolve_region_key("Navi Mumbai") == "mumbai"


def test_unknown_region_raises():
    with pytest.raises(UnknownRegionError):
        resolve_region_key("Delhi")
    with pytest.raises(UnknownRegionError):
        evaluate_scenario(ScenarioInput(region="Delhi"))


def test_api_returns_404_for_unknown_region():
    for path in ("/api/context/delhi", "/api/coverage-check/delhi"):
        r = client.get(path)
        assert r.status_code == 404 and "Supported regions" in r.json()["detail"]
    r = client.post("/api/scenario/evaluate", json={"region": "Delhi"})
    assert r.status_code == 404


def test_untraced_values_are_low_confidence_and_labelled_illustrative():
    a = evaluate_scenario(ScenarioInput(region="bengaluru"))["evaporative"].community_ledger
    for ind in (a.aquifer_stress_classification, a.grid_carbon_intensity, a.tanker_dependency_index,
                a.water_headroom_share_pct, a.substation_peak_demand_share_pct, a.grid_outage_risk_index):
        assert ind.confidence == DataConfidence.LOW
        assert "illustrative" in ind.source_label.lower()
