"""
Unit tests for AquaCarbon DC deterministic calculation engine.
Validates numerical fidelity, thermodynamics, PUE/WUE relationships,
carbon footprinting, and constraint planner logic.
"""

import pytest
from engine.models import CoolingType, Season, ScenarioInput, PlannerConstraints
from engine.calculator import (
    compute_facility_ledger, compute_community_ledger,
    compute_burden_shift_scores, evaluate_scenario, run_constraint_planner
)
from engine.coverage import run_coverage_check


def test_evaporative_cooling_calculations():
    fl = compute_facility_ledger(
        cooling_type=CoolingType.EVAPORATIVE,
        it_capacity_mw=15.0,
        season=Season.ANNUAL_AVERAGE,
        region_key="bengaluru",
        grid_carbon_factor=710.0
    )
    # 15 MW * 8760 h = 131,400 MWh IT energy
    assert fl.annual_it_energy_mwh == 131400.0
    assert 1.15 <= fl.pue <= 1.25
    assert fl.wue >= 1.8
    assert fl.direct_water_consumption_ml > 200.0  # High water draw
    assert fl.direct_water_consumption_m3 == round(fl.direct_water_consumption_ml * 1000.0, 2)
    assert fl.total_facility_energy_mwh == round(131400.0 * fl.pue, 2)


def test_dry_cooling_zero_water_tradeoff():
    fl = compute_facility_ledger(
        cooling_type=CoolingType.DRY_COOLING,
        it_capacity_mw=15.0,
        season=Season.ANNUAL_AVERAGE,
        region_key="bengaluru",
        grid_carbon_factor=710.0
    )
    assert fl.wue <= 0.05
    assert fl.direct_water_consumption_ml < 10.0  # Minimal water
    assert fl.pue >= 1.40  # Higher PUE penalty
    assert fl.annual_operating_cost_inr_crores > 0


def test_hybrid_adiabatic_compromise():
    fl_evap = compute_facility_ledger(CoolingType.EVAPORATIVE, 15.0, Season.ANNUAL_AVERAGE, "bengaluru")
    fl_dry = compute_facility_ledger(CoolingType.DRY_COOLING, 15.0, Season.ANNUAL_AVERAGE, "bengaluru")
    fl_hybrid = compute_facility_ledger(CoolingType.HYBRID_ADIABATIC, 15.0, Season.ANNUAL_AVERAGE, "bengaluru")

    # Hybrid water must be significantly lower than evaporative
    assert fl_hybrid.direct_water_consumption_ml < (fl_evap.direct_water_consumption_ml * 0.40)
    # Hybrid PUE must be lower than dry cooling
    assert fl_hybrid.pue < fl_dry.pue


def test_community_ledger_indicators():
    fl = compute_facility_ledger(CoolingType.EVAPORATIVE, 15.0, Season.ANNUAL_AVERAGE, "bengaluru")
    cl = compute_community_ledger(fl, "bengaluru", utility_water_headroom_ml=220.0, substation_capacity_mw=60.0)

    assert cl.water_headroom_share_pct.value is not None
    assert cl.water_headroom_share_pct.value > 100.0  # Consumes entire headroom buffer!
    assert cl.household_water_equivalent_count.value is not None
    assert cl.household_water_equivalent_count.value > 1000  # Feeds thousands of families
    assert "Over-Exploited" in cl.aquifer_stress_classification.formatted_value


def test_burden_shifting_scores_tradeoff():
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
    assessments = evaluate_scenario(scenario)

    evap_burden = assessments[CoolingType.EVAPORATIVE.value].burden_scores
    dry_burden = assessments[CoolingType.DRY_COOLING.value].burden_scores

    # Evaporative has high water burden, lower power burden
    assert evap_burden.water_system_burden > dry_burden.water_system_burden
    # Dry cooling has high power and carbon burden, minimal water burden
    assert dry_burden.power_system_burden > evap_burden.power_system_burden
    assert dry_burden.water_system_burden <= 5.0


def test_constraint_planner_feasible_and_infeasible():
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")

    # Strict water headroom ceiling (< 20%): Evaporative must fail, Dry must pass
    constraints_strict_water = PlannerConstraints(
        max_water_headroom_share_pct=20.0,
        max_pue=1.60
    )
    result = run_constraint_planner(scenario, constraints_strict_water)
    feasible_types = [c.cooling_type for c in result.feasible_configurations]
    assert CoolingType.DRY_COOLING in feasible_types
    assert CoolingType.EVAPORATIVE not in feasible_types

    # Impossible constraints: PUE < 1.15 AND water < 5 ML
    constraints_impossible = PlannerConstraints(
        max_pue=1.15,
        max_annual_water_ml=5.0
    )
    res_impossible = run_constraint_planner(scenario, constraints_impossible)
    assert len(res_impossible.feasible_configurations) == 0
    assert res_impossible.refusal_reason is not None
    assert "No recommendation is made" in res_impossible.refusal_reason
    assert "binding constraint" in res_impossible.refusal_reason


def test_coverage_disparity_check():
    result = run_coverage_check("bengaluru")
    assert result.disparity_ratio > 1.25
    assert result.unmapped_tanker_dependent_population_estimate > 10000
    assert len(result.flags) >= 2
    assert len(result.recommended_ground_truth_actions) > 0
