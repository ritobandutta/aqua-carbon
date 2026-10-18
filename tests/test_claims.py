"""Claim checking against the engine's modelled range."""

import pytest
from engine.calculator import evaluate_with_bands
from engine.claims import ClaimScenario, check_claim, CLAIMABLE_METRICS
from engine.models import CoolingType

SC = ClaimScenario(region="bengaluru", it_capacity_mw=15.0)
H = CoolingType.HYBRID_ADIABATIC


def _band(metric, cooling=H):
    return evaluate_with_bands(SC.to_scenario(cooling))[cooling.value][metric]


def test_central_value_is_within_range():
    b = _band("direct_water_ml")
    v = check_claim(SC, H, "direct_water_ml", b["central"])
    assert v.verdict == "within_modelled_range" and v.claim_vs_central_pct == 0.0


def test_claim_below_best_case_is_flagged():
    b = _band("direct_water_ml")
    v = check_claim(SC, H, "direct_water_ml", b["low"] * 0.5)
    assert v.verdict == "below_modelled_range" and v.claim_vs_central_pct < 0


def test_claim_above_worst_case_is_flagged():
    b = _band("direct_water_ml")
    assert check_claim(SC, H, "direct_water_ml", b["high"] * 2).verdict == "above_modelled_range"


def test_boundaries_are_inclusive():
    b = _band("pue")
    assert check_claim(SC, H, "pue", b["low"]).verdict == "within_modelled_range"
    assert check_claim(SC, H, "pue", b["high"]).verdict == "within_modelled_range"


def test_every_claimable_metric_resolves():
    for metric in CLAIMABLE_METRICS:
        v = check_claim(SC, CoolingType.EVAPORATIVE, metric, 1.0)
        assert v.modelled_low <= v.modelled_central <= v.modelled_high


def test_unknown_metric_and_region_raise():
    with pytest.raises(ValueError):
        check_claim(SC, H, "vibes", 1.0)
    from engine.data_sources import UnknownRegionError
    with pytest.raises(UnknownRegionError):
        check_claim(ClaimScenario(region="Delhi", it_capacity_mw=5), H, "pue", 1.2)


def test_every_verdict_carries_the_unverified_caveat():
    v = check_claim(SC, H, "pue", 1.2)
    assert v.inputs_status == "illustrative_unverified" and "not yet verified" in v.caveat


def test_verdict_depends_on_scenario():
    big = ClaimScenario(region="bengaluru", it_capacity_mw=45.0)
    claim = _band("direct_water_ml")["central"]
    assert check_claim(SC, H, "direct_water_ml", claim).verdict == "within_modelled_range"
    assert check_claim(big, H, "direct_water_ml", claim).verdict == "below_modelled_range"
