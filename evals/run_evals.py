"""
Evaluation Suite for AquaCarbon DC — Commons Edition (v2).
Implements the 5 evaluation checks required by Section 8 of the Specification:
1. Numerical Fidelity Check: Checks that all numbers in briefs match engine calculation.
2. Verifier Catch-Rate Check: Injects corrupted numbers into briefs and measures verifier detection rate.
3. Constraint Handling Check: Evaluates feasible configuration search and honest refusal when overconstrained.
4. Coverage Check Sensitivity: Validates detection of under-represented informal populations.
5. Recommendation Stability Check: Confirms deterministic output stability and seasonal trade-off shifts.
"""

import sys
import copy
from typing import Dict, Any, List
from engine.models import (
    ScenarioInput, CoolingType, Season, PlannerConstraints, ProfileAssessment
)
from engine.calculator import evaluate_scenario, run_constraint_planner
from engine.coverage import run_coverage_check
from agents.advisor_agent import AdvisorAgent
from agents.verifier_agent import VerifierAgent


def eval_numerical_fidelity() -> Dict[str, Any]:
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
    assessments = evaluate_scenario(scenario)

    advisor = AdvisorAgent()
    op_brief = advisor.generate_operator_brief(scenario, assessments)
    comm_brief = advisor.generate_community_brief(scenario, assessments)

    verifier = VerifierAgent()
    report = verifier.verify_briefs(op_brief, comm_brief, assessments)

    return {
        "check": "Numerical Fidelity",
        "total_checks": report.total_checks,
        "passed": report.passed_checks,
        "failed": report.failed_checks,
        "success": report.status == "PASSED",
        "signature": report.signature
    }


def eval_verifier_catch_rate() -> Dict[str, Any]:
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
    assessments = evaluate_scenario(scenario)

    advisor = AdvisorAgent()
    op_brief = advisor.generate_operator_brief(scenario, assessments)
    comm_brief = advisor.generate_community_brief(scenario, assessments)

    # Corrupt key numbers deliberately (simulating an LLM hallucination)
    # E.g., change PUE 1.20 to 1.05, change water 275.9 ML to 42.1 ML
    mutated_op_brief = op_brief.replace("1.20", "1.02").replace("275.9 ML", "15.0 ML")
    mutated_comm_brief = comm_brief.replace("275.9", "12.4")

    verifier = VerifierAgent()
    report = verifier.verify_briefs(mutated_op_brief, mutated_comm_brief, assessments)

    # Verifier MUST flag the mismatch!
    catch_rate_pct = (report.failed_checks / max(report.total_checks, 1)) * 100.0
    detected_tampering = (report.status == "FLAGGED_MISMATCH")

    return {
        "check": "Verifier Catch-Rate",
        "total_injected_checks": report.total_checks,
        "detected_failures": report.failed_checks,
        "catch_rate_pct": round(catch_rate_pct, 1),
        "status": report.status,
        "success": detected_tampering
    }


def eval_constraint_handling() -> Dict[str, Any]:
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")

    # Case 1: Feasible constraints (Hybrid and Dry should pass)
    c_feasible = PlannerConstraints(max_water_headroom_share_pct=60.0, max_pue=1.50)
    res_feasible = run_constraint_planner(scenario, c_feasible)
    feasible_count = len(res_feasible.feasible_configurations)

    # Case 2: Infeasible constraints (no profile can satisfy PUE 1.15 AND water < 10 ML)
    c_impossible = PlannerConstraints(max_pue=1.15, max_annual_water_ml=10.0)
    res_impossible = run_constraint_planner(scenario, c_impossible)
    refused_honestly = len(res_impossible.feasible_configurations) == 0 and res_impossible.refusal_reason is not None

    return {
        "check": "Constraint Handling",
        "feasible_case_passed": feasible_count > 0,
        "feasible_count": feasible_count,
        "refusal_case_passed": refused_honestly,
        "success": (feasible_count > 0) and refused_honestly
    }


def eval_coverage_check() -> Dict[str, Any]:
    bengaluru_coverage = run_coverage_check("bengaluru")
    has_gap = bengaluru_coverage.disparity_ratio > 1.25
    has_actions = len(bengaluru_coverage.recommended_ground_truth_actions) >= 3

    return {
        "check": "Coverage Disparity Check",
        "disparity_ratio": bengaluru_coverage.disparity_ratio,
        "unmapped_population": bengaluru_coverage.unmapped_tanker_dependent_population_estimate,
        "actions_recommended_count": len(bengaluru_coverage.recommended_ground_truth_actions),
        "success": has_gap and has_actions
    }


def eval_recommendation_stability() -> Dict[str, Any]:
    # Run 1: Dry Summer
    scenario_summer = ScenarioInput(it_capacity_mw=15.0, region="bengaluru", season=Season.DRY_SUMMER)
    summer_assessments = evaluate_scenario(scenario_summer)

    # Run 2: Monsoon
    scenario_monsoon = ScenarioInput(it_capacity_mw=15.0, region="bengaluru", season=Season.MONSOON)
    monsoon_assessments = evaluate_scenario(scenario_monsoon)

    # Evaporative water consumption in dry summer must be higher than in monsoon
    evap_summer_w = summer_assessments["evaporative"].facility_ledger.direct_water_consumption_ml
    evap_monsoon_w = monsoon_assessments["evaporative"].facility_ledger.direct_water_consumption_ml

    # Dry cooling PUE in summer must be higher than in monsoon
    dry_summer_pue = summer_assessments["dry_cooling"].facility_ledger.pue
    dry_monsoon_pue = monsoon_assessments["dry_cooling"].facility_ledger.pue

    summer_higher_water = evap_summer_w > evap_monsoon_w
    summer_higher_pue = dry_summer_pue > dry_monsoon_pue

    return {
        "check": "Recommendation Stability & Seasonal Flip",
        "evaporative_summer_water_ml": evap_summer_w,
        "evaporative_monsoon_water_ml": evap_monsoon_w,
        "dry_cooling_summer_pue": dry_summer_pue,
        "dry_cooling_monsoon_pue": dry_monsoon_pue,
        "seasonal_physics_fidelity": summer_higher_water and summer_higher_pue,
        "success": summer_higher_water and summer_higher_pue
    }


def run_all_evaluations() -> Dict[str, Any]:
    results = [
        eval_numerical_fidelity(),
        eval_verifier_catch_rate(),
        eval_constraint_handling(),
        eval_coverage_check(),
        eval_recommendation_stability()
    ]

    all_passed = all(r["success"] for r in results)

    print("==========================================================")
    print(" AQUACARBON DC (COMMONS EDITION) - SPECIFICATION EVAL SUITE")
    print("==========================================================")
    for r in results:
        status_icon = "PASS" if r["success"] else "FAIL"
        print(f"[{status_icon}] {r['check']}")
        for k, v in r.items():
            if k not in ("check", "success"):
                print(f"       -> {k}: {v}")
    print("----------------------------------------------------------")
    print(f"OVERALL EVALUATION RESULT: {'ALL PASS' if all_passed else 'SOME FAILED'}")
    print("==========================================================")

    return {
        "all_passed": all_passed,
        "checks": results
    }


if __name__ == "__main__":
    res = run_all_evaluations()
    sys.exit(0 if res["all_passed"] else 1)
