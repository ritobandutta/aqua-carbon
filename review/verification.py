"""
Independent verification of a permit review. Pure and deterministic: used by the A2A verifier service and
unit-testable without ADK.

The verifier recomputes everything from the scenario. It checks that
  1. every claimed number really appears in the applicant's text (the model did not invent a claim),
  2. the verdict rows the caller reports equal what the engine computes,
  3. every unit-tagged number in the review traces to the engine, a modelled-range bound for a claimed
     metric, or a provenance-checked applicant figure.
Limit: only numbers that carry a recognised unit are inspected, and the verifier cannot tell whether the
review's wording is fair, only that its figures are real.
"""

import re
from typing import Dict, List
from agents.verifier_agent import VerifierAgent, _build_report
from engine.calculator import evaluate_scenario
from engine.claims import check_claim
from engine.models import CoolingType, ScenarioInput, VerificationCheckItem, VerificationReport
from .models import VerifyReviewRequest

_LABEL_FOR_METRIC = {
    "pue": "pue", "direct_water_ml": "water_ml", "facility_energy_mwh": "energy_mwh",
    "scope2_carbon_tonnes": "carbon_t", "operating_cost_inr_crores": "cost_cr",
}
_NUM = re.compile(r"(?<![0-9.])[0-9][0-9,]*(?:\.[0-9]+)?")


def _numbers_in(text: str) -> List[float]:
    out = []
    for m in _NUM.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def verify_review(req: VerifyReviewRequest) -> VerificationReport:
    checks: List[VerificationCheckItem] = []
    applicant_numbers = _numbers_in(req.applicant_text)
    extra: Dict[str, List[float]] = {}

    for c in req.claims:
        name = f"{c.cooling_type.value} {c.metric}"
        try:
            truth = check_claim(req.scenario, c.cooling_type, c.metric, c.claimed_value)
        except Exception as e:  # unknown metric or region: a failed check, never a crash
            checks.append(VerificationCheckItem(metric_name=f"Claim valid: {name}", claimed_value_in_brief=str(c.claimed_value),
                                                engine_calculated_value="n/a", matched=False, discrepancy_note=str(e)))
            continue

        if req.claims_source == "text":
            found = any(_close(c.claimed_value, n) for n in applicant_numbers)
            checks.append(VerificationCheckItem(
                metric_name=f"Claim appears in applicant text: {name}",
                claimed_value_in_brief=str(c.claimed_value), engine_calculated_value="present in applicant text" if found else "absent",
                matched=found,
                discrepancy_note=None if found else f"The figure {c.claimed_value} does not appear in the applicant's text, so the claim may have been invented.",
            ))
            if not found:
                continue  # an unproven claimed value must not be allowed into the review

        reported = next((r for r in req.reported_verdicts
                         if r.get("cooling_type") == c.cooling_type.value and r.get("metric") == c.metric
                         and _close(float(r.get("claimed_value", float("nan"))), c.claimed_value)), None)
        same = reported is not None and all(
            _close(float(reported.get(k, float("nan"))), getattr(truth, k))
            for k in ("modelled_low", "modelled_central", "modelled_high")
        ) and reported.get("verdict") == truth.verdict
        checks.append(VerificationCheckItem(
            metric_name=f"Tool result matches engine: {name}",
            claimed_value_in_brief=(reported or {}).get("verdict", "missing"), engine_calculated_value=truth.verdict,
            matched=same,
            discrepancy_note=None if same else "The reported verdict or modelled range differs from the engine's own computation (or is missing).",
        ))

        label = _LABEL_FOR_METRIC.get(c.metric)
        if label:
            extra.setdefault(label, []).extend([c.claimed_value, truth.modelled_low, truth.modelled_central, truth.modelled_high])

    if req.claims and not req.review_text.strip():
        checks.append(VerificationCheckItem(metric_name="Review text present", claimed_value_in_brief="empty",
                                            engine_calculated_value="non-empty", matched=False,
                                            discrepancy_note="Claims were checked but no review was written."))

    assessments = evaluate_scenario(ScenarioInput(
        region=req.scenario.region, it_capacity_mw=req.scenario.it_capacity_mw, season=req.scenario.season,
        workload_type=req.scenario.workload_type, grid_carbon_factor_kg_per_mwh=req.scenario.grid_carbon_factor_kg_per_mwh,
        selected_profiles=list(CoolingType)))
    checks.extend(VerifierAgent()._claim_checks(req.review_text, assessments, extra))
    if not checks:
        checks.append(VerificationCheckItem(metric_name="Nothing to verify", claimed_value_in_brief="", engine_calculated_value="",
                                            matched=True))
    return _build_report(checks)
