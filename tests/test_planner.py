"""Constraint planner: feasibility, honest refusal, and that refusal text is derived from the data."""

from engine.models import ScenarioInput, PlannerConstraints, DataConfidence
from engine.calculator import run_constraint_planner

S = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")


def test_feasible_set_is_returned():
    r = run_constraint_planner(S, PlannerConstraints(max_pue=1.5, max_water_headroom_share_pct=60.0))
    assert len(r.feasible_configurations) == 2
    assert r.refusal_reason is None


def test_refuses_when_nothing_is_feasible_and_names_the_binding_constraint():
    r = run_constraint_planner(S, PlannerConstraints(max_cooling_cost_inr_crores=1.0))
    assert r.feasible_configurations == []
    assert "operating cost" in r.refusal_reason
    assert all("operating cost" in i.nearest_tradeoff for i in r.infeasible_configurations)


def test_refusal_text_changes_with_the_constraints():
    cost = run_constraint_planner(S, PlannerConstraints(max_cooling_cost_inr_crores=1.0)).refusal_reason
    pue = run_constraint_planner(S, PlannerConstraints(max_pue=1.15, max_annual_water_ml=10.0)).refusal_reason
    assert cost != pue


def test_closest_profile_has_smallest_worst_case_overshoot():
    r = run_constraint_planner(S, PlannerConstraints(max_pue=1.15, max_annual_water_ml=10.0))
    # Dry cooling misses PUE by ~26%; evaporative misses water by thousands of percent.
    assert "Air-Cooled" in r.refusal_reason


def test_min_data_confidence_is_enforced():
    r = run_constraint_planner(S, PlannerConstraints(min_data_confidence=DataConfidence.HIGH))
    assert r.feasible_configurations == []
    assert "data confidence" in r.refusal_reason
    ok = run_constraint_planner(S, PlannerConstraints(min_data_confidence=DataConfidence.MEDIUM))
    assert len(ok.feasible_configurations) == 3


def test_no_constraints_means_everything_is_feasible():
    assert len(run_constraint_planner(S, PlannerConstraints()).feasible_configurations) == 3
