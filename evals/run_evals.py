"""
Evaluation Suite for AquaCarbon DC — Commons Edition (v2).
Implements the evaluation checks required by Section 8 (plus stability, seeded-gap, flip and latency) of the Specification:
1. Numerical Fidelity Check: Checks that all numbers in briefs match engine calculation.
2. Verifier Catch-Rate Check: Injects corrupted numbers into briefs and measures verifier detection rate.
3. Constraint Handling Check: Evaluates feasible configuration search and honest refusal when overconstrained.
4. Coverage Check Sensitivity: Validates detection of under-represented informal populations.
5. Recommendation Stability Check: Confirms deterministic output stability and seasonal trade-off shifts.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import copy
import json
import time
from typing import Dict, Any, List
from engine.models import (
    ScenarioInput, CoolingType, Season, PlannerConstraints, ProfileAssessment
)
from engine.calculator import evaluate_scenario, run_constraint_planner
from engine.coverage import run_coverage_check, AREA_COVERAGE_BENCHMARKS
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

    # Catch rate is measured per injected error: corrupt ONE engine value at a time (+15%),
    # re-verify, and count how many of those single corruptions the verifier blocks.
    injected = 0
    caught = 0
    misses: List[str] = []
    for key, asm in assessments.items():
        fl, cl = asm.facility_ledger, asm.community_ledger
        targets = {
            "PUE": f"{fl.pue:.2f}",
            "water_ml": f"{fl.direct_water_consumption_ml:.1f}",
            "carbon_t": f"{fl.scope2_carbon_tonnes:,.0f}",
            "cost_cr": f"{fl.annual_operating_cost_inr_crores:.2f}",
        }
        if cl.water_headroom_share_pct.value is not None:
            targets["headroom_pct"] = f"{cl.water_headroom_share_pct.value:.1f}"
        for metric, original in targets.items():
            raw = float(original.replace(",", ""))
            corrupted = f"{raw * 1.15:.2f}" if metric in ("PUE", "cost_cr") else f"{raw * 1.15:.1f}"
            op_c, cm_c = op_brief.replace(original, corrupted), comm_brief.replace(original, corrupted)
            if op_c == op_brief and cm_c == comm_brief:
                continue  # value not printed in these briefs, nothing to corrupt
            injected += 1
            if verifier.verify_briefs(op_c, cm_c, assessments).status != "PASSED":
                caught += 1
            else:
                misses.append(f"{key}:{metric}")

    # Also inject a fabricated claim while leaving every true number intact.
    fabricated = op_brief + "\n\nNote: dry cooling achieves PUE of 0.95 using 1.0 ML of water."
    injected += 1
    if verifier.verify_briefs(fabricated, comm_brief, assessments).status != "PASSED":
        caught += 1
    else:
        misses.append("fabricated_claim")

    catch_rate_pct = (caught / max(injected, 1)) * 100.0

    return {
        "check": "Verifier Catch-Rate",
        "total_injected_checks": injected,
        "detected_failures": caught,
        "catch_rate_pct": round(catch_rate_pct, 1),
        "missed": misses,
        "status": report.status,  # status for the combined multi-metric tamper
        "success": report.status == "FLAGGED_MISMATCH" and caught == injected
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


def eval_repeat_run_stability() -> Dict[str, Any]:
    """Same inputs must give byte-identical engine output and an identical verifier digest."""
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
    dumps, digests = set(), set()
    for _ in range(5):
        a = evaluate_scenario(scenario)
        dumps.add(json.dumps({k: v.model_dump(mode="json") for k, v in a.items()}, sort_keys=True))
        adv = AdvisorAgent()
        rep = VerifierAgent().verify_briefs(adv.generate_operator_brief(scenario, a), adv.generate_community_brief(scenario, a), a)
        digests.add(rep.signature)
    ok = len(dumps) == 1 and len(digests) == 1
    return {"check": "Repeat-Run Stability", "runs": 5, "distinct_outputs": len(dumps),
            "distinct_digests": len(digests), "success": ok}


def eval_coverage_seeded_gap() -> Dict[str, Any]:
    """Seed a known gap by shrinking the official footprint in a copy of the data, and a no-gap control.
    The check must flag the seeded gap and must not flag the control. Needs no real ground truth."""
    key = "bengaluru"
    original = copy.deepcopy(AREA_COVERAGE_BENCHMARKS[key])
    try:
        AREA_COVERAGE_BENCHMARKS[key]["official_piped_water_coverage_km2"] = AREA_COVERAGE_BENCHMARKS[key]["satellite_settlement_builtup_km2"]
        control = run_coverage_check(key)
        AREA_COVERAGE_BENCHMARKS[key]["official_piped_water_coverage_km2"] = AREA_COVERAGE_BENCHMARKS[key]["satellite_settlement_builtup_km2"] * 0.4
        seeded = run_coverage_check(key)
    finally:
        AREA_COVERAGE_BENCHMARKS[key] = original
    control_clean = control.disparity_ratio <= 1.25 and control.unmapped_tanker_dependent_population_estimate == 0
    seeded_flagged = seeded.disparity_ratio > 1.25 and seeded.unmapped_tanker_dependent_population_estimate > 0
    return {"check": "Coverage Seeded-Gap Detection", "control_disparity": control.disparity_ratio,
            "seeded_disparity": seeded.disparity_ratio, "control_clean": control_clean,
            "seeded_flagged": seeded_flagged, "success": control_clean and seeded_flagged}


def eval_recommendation_flip() -> Dict[str, Any]:
    """With one fixed community water limit, the feasible set must change when the season changes,
    and the planner must say which profiles flipped. Fails if the recommendation never moves."""
    c = PlannerConstraints(max_water_headroom_share_pct=100.0)
    sets = {}
    for season in (Season.WINTER, Season.DRY_SUMMER):
        r = run_constraint_planner(ScenarioInput(it_capacity_mw=15.0, region="bengaluru", season=season), c)
        sets[season.value] = sorted(a.cooling_type.value for a in r.feasible_configurations)
    flipped = sets["winter"] != sets["dry_summer"]
    return {"check": "Recommendation Flip With Season", "winter_feasible": sets["winter"],
            "dry_summer_feasible": sets["dry_summer"], "flipped": flipped, "success": flipped}


def eval_latency() -> Dict[str, Any]:
    """Own footprint: wall time of one full deterministic analysis (no LLM call)."""
    from agents.orchestrator import AgentOrchestrator
    orch = AgentOrchestrator()
    scenario = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
    t = []
    for _ in range(10):
        t0 = time.perf_counter(); orch.process_scenario(scenario); t.append((time.perf_counter() - t0) * 1000)
    t.sort()
    return {"check": "Deterministic Pipeline Latency", "median_ms": round(t[len(t)//2], 2),
            "p95_ms": round(t[int(len(t)*0.95) - 1], 2), "llm_tokens": 0, "success": t[len(t)//2] < 500}


def run_all_evaluations() -> Dict[str, Any]:
    results = [
        eval_numerical_fidelity(),
        eval_verifier_catch_rate(),
        eval_constraint_handling(),
        eval_coverage_check(),
        eval_recommendation_stability(),
        eval_repeat_run_stability(),
        eval_coverage_seeded_gap(),
        eval_recommendation_flip(),
        eval_latency()
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
