"""
Tests for 24-Hour Arbiter & AI Dispatcher Engine
Inspired by FortyGuard Agentic-Arbiter & CooL-LLM
"""

import pytest
from engine.models import ScenarioInput, Season
from engine.arbiter import simulate_24h_arbiter, ArbiterSimulationResult
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_simulate_24h_arbiter_deterministic():
    # Annual average has cool nights (< 25C) -> activates free cooling
    scenario_annual = ScenarioInput(
        scenario_title="Bengaluru 15MW Arbiter Annual",
        region="bengaluru",
        season=Season.ANNUAL_AVERAGE,
        it_capacity_mw=15.0
    )
    result_annual = simulate_24h_arbiter(scenario_annual, ai_flexibility_pct=40.0)

    assert isinstance(result_annual, ArbiterSimulationResult)
    assert len(result_annual.hourly_steps) == 24
    assert result_annual.free_cooling_hours > 0
    assert result_annual.water_saved_liters > 0
    assert result_annual.households_water_restored_days > 0
    assert result_annual.peak_grid_shaved_mw > 0
    assert result_annual.workload_shifted_mwh > 0

    # Dry summer has hot nights (> 30C) -> economizer correctly shifts to dry chiller
    scenario_summer = ScenarioInput(
        scenario_title="Bengaluru 15MW Arbiter Summer",
        region="bengaluru",
        season=Season.DRY_SUMMER,
        it_capacity_mw=15.0
    )
    result_summer = simulate_24h_arbiter(scenario_summer, ai_flexibility_pct=40.0)
    assert result_summer.free_cooling_hours == 0
    assert result_summer.water_saved_liters > 0


def test_arbiter_api_endpoint():
    payload = {
        "scenario": {
            "scenario_title": "API Arbiter Test",
            "region": "bengaluru",
            "season": "annual_average",
            "it_capacity_mw": 20.0
        },
        "ai_flexibility_pct": 30.0
    }
    response = client.post("/api/arbiter/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "hourly_steps" in data
    assert len(data["hourly_steps"]) == 24
    assert data["water_savings_pct"] > 0
    assert data["peak_grid_shaved_mw"] >= 0
