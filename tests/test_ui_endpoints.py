"""
End-to-end integration and UI element verification test suite.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

# In-process client: no live server and no fixed port needed.
client = TestClient(app)


def test_html_ui_components_exist():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    required_ids = [
        "preset-selector",
        "season-selector",
        "workload-selector",
        "capacity-slider",
        "grid-slider",
        "btn-recalculate",
        "burden-grid",
        "facility-ledger-cards",
        "community-ledger-cards",
        "coverage-layout",
        "btn-run-planner",
        "planner-results",
        "investigate-input",
        "btn-ask-gemini",
        "investigator-output",
        "btn-tamper-demo",
        "btn-copy-brief",
        "brief-markdown-content",
        "btn-run-evals",
        "evals-modal",
        "modal-eval-body",
        "btn-close-modal"
    ]

    for rid in required_ids:
        assert f'id="{rid}"' in html, f"Missing required UI DOM element: {rid}"


def test_api_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["cloud_run_ready"] is True


def test_api_recalculate_scenario_flow():
    payload = {
        "scenario_id": "bengaluru_15mw",
        "scenario_title": "Bengaluru 15MW",
        "region": "bengaluru",
        "it_capacity_mw": 15.0,
        "season": "annual_average",
        "workload_type": "static_inference",
        "grid_carbon_factor_kg_per_mwh": 710.0,
        "selected_profiles": ["evaporative", "dry_cooling", "hybrid_adiabatic"]
    }
    r = client.post("/api/scenario/evaluate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["assessments"]) == 3
    assert data["verification"]["status"] == "PASSED"

    # Test dynamic scaling to 35 MW
    payload["it_capacity_mw"] = 35.0
    r35 = client.post("/api/scenario/evaluate", json=payload)
    assert r35.status_code == 200
    assert r35.json()["assessments"]["evaporative"]["facility_ledger"]["it_capacity_mw"] == 35.0


def test_api_coverage_check_flow():
    r = client.get("/api/coverage-check/bengaluru")
    assert r.status_code == 200
    cov = r.json()
    assert cov["disparity_ratio"] == 1.83
    assert cov["unmapped_tanker_dependent_population_estimate"] > 80000


def test_api_planner_flow():
    scenario = {
        "scenario_id": "bengaluru_15mw",
        "scenario_title": "Bengaluru 15MW",
        "region": "bengaluru",
        "it_capacity_mw": 15.0,
        "season": "annual_average",
        "workload_type": "static_inference",
        "grid_carbon_factor_kg_per_mwh": 710.0,
        "selected_profiles": ["evaporative", "dry_cooling", "hybrid_adiabatic"]
    }
    payload = {
        "scenario": scenario,
        "constraints": {"max_pue": 1.50, "max_water_headroom_share_pct": 60.0}
    }
    r = client.post("/api/scenario/planner", json=payload)
    assert r.status_code == 200
    assert len(r.json()["feasible_configurations"]) > 0


def test_api_tamper_demo_flow():
    r = client.get("/api/evals/tamper-demo")
    assert r.status_code == 200
    tdata = r.json()
    assert tdata["action_taken"] == "BLOCKED_PUBLICATION"
    assert tdata["result"]["status"] == "FLAGGED_MISMATCH"


def test_api_evals_flow():
    r = client.get("/api/evals/run")
    assert r.status_code == 200
    assert r.json()["all_passed"] is True
