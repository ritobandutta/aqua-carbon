"""Pure verification logic for permit reviews (no ADK needed)."""

import pytest
from engine.claims import ClaimScenario, check_claim
from engine.models import CoolingType
from review.models import ClaimInput, VerifyReviewRequest
from review.rendering import render_review
from review.verification import verify_review

SC = ClaimScenario(region="bengaluru", it_capacity_mw=15.0)
H = CoolingType.HYBRID_ADIABATIC
TEXT = "The hybrid adiabatic system will use 40 ML of water per year at a PUE of 1.2."


def _req(claimed=40.0, text=TEXT, source="text", review=None, verdicts=None, metric="direct_water_ml"):
    v = check_claim(SC, H, metric, claimed).model_dump(mode="json")
    rows = [v] if verdicts is None else verdicts
    return VerifyReviewRequest(scenario=SC, claims_source=source, applicant_text=text,
                               claims=[ClaimInput(cooling_type=H, metric=metric, claimed_value=claimed)],
                               reported_verdicts=rows, review_text=render_review("Bengaluru 15 MW", rows) if review is None else review)


def test_honest_review_passes():
    r = verify_review(_req())
    assert r.status == "PASSED", [c.discrepancy_note for c in r.checks if not c.matched]


def test_invented_claim_value_is_rejected():
    r = verify_review(_req(claimed=33.0))   # 33 is not in the applicant text
    assert r.status == "FLAGGED_MISMATCH"
    assert any("Claim appears in applicant text" in c.metric_name and not c.matched for c in r.checks)


def test_structured_claims_need_no_text_provenance():
    assert verify_review(_req(text="", source="structured")).status == "PASSED"


def test_tampered_tool_result_is_caught():
    rows = [check_claim(SC, H, "direct_water_ml", 40.0).model_dump(mode="json")]
    rows[0]["verdict"] = "within_modelled_range"            # truth is below_modelled_range
    assert verify_review(_req(verdicts=rows)).status == "FLAGGED_MISMATCH"
    rows[0]["verdict"] = "below_modelled_range"; rows[0]["modelled_low"] = 10.0
    assert verify_review(_req(verdicts=rows)).status == "FLAGGED_MISMATCH"


def test_missing_tool_result_is_caught():
    assert verify_review(_req(verdicts=[])).status == "FLAGGED_MISMATCH"


def test_fabricated_figure_in_review_is_caught():
    review = render_review("x", [check_claim(SC, H, "direct_water_ml", 40.0).model_dump(mode="json")])
    bad = verify_review(_req(review=review + "\nIndependent studies show 12 ML is typical."))
    assert bad.status == "FLAGGED_MISMATCH"
    assert any("12" in (c.discrepancy_note or "") for c in bad.checks)


def test_review_may_quote_the_applicant_and_range_bounds():
    r = verify_review(_req(review="The applicant states 40.0 ML. The modelled best case is 64.1 ML."))
    assert r.status == "PASSED"


def test_applicant_number_not_in_claims_cannot_be_smuggled_in():
    # 40 is claimed and proven; 99 ML appears in the applicant text but was never made a claim.
    r = verify_review(_req(text=TEXT + " Also 99 ML elsewhere.", review="Applicant also says 99.0 ML."))
    assert r.status == "FLAGGED_MISMATCH"


def test_empty_review_with_claims_is_rejected():
    assert verify_review(_req(review="   ")).status == "FLAGGED_MISMATCH"


def test_invalid_metric_is_a_failed_check_not_a_crash():
    req = _req(); req.claims[0].metric = "vibes"
    assert verify_review(req).status == "FLAGGED_MISMATCH"


@pytest.mark.parametrize("metric,val", [("pue", 1.1), ("direct_water_ml", 250.0), ("facility_energy_mwh", 150000.0),
                                        ("scope2_carbon_tonnes", 100000.0), ("operating_cost_inr_crores", 120.0)])
def test_rendered_review_passes_for_every_metric(metric, val):
    assert verify_review(_req(claimed=val, text=f"We commit to {val}.", metric=metric)).status == "PASSED"
