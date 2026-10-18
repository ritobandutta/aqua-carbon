"""Sensitivity bands and a physics sanity bound on evaporative water use."""

import pytest
from engine.calculator import evaluate_scenario, evaluate_with_bands, compute_facility_ledger
from engine.models import ScenarioInput, CoolingType, Season

S = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")


def test_bands_bracket_the_central_value_and_are_ordered():
    bands = evaluate_with_bands(S)
    central = evaluate_scenario(S)
    for profile, metrics in bands.items():
        fl = central[profile].facility_ledger
        assert metrics["direct_water_ml"]["central"] == fl.direct_water_consumption_ml
        assert metrics["scope2_carbon_tonnes"]["central"] == fl.scope2_carbon_tonnes
        for m in metrics.values():
            assert m["low"] <= m["central"] <= m["high"]


def test_band_width_tracks_the_sensitivity_inputs():
    b = evaluate_with_bands(S)["evaporative"]["direct_water_ml"]
    assert b["high"] / b["central"] == pytest.approx(1.25, abs=0.01)


def test_evaporative_wue_is_physically_possible():
    """Bounds from first principles, per kWh of IT energy.
    Evaporation: 3.6 MJ / latent heat (2.26 MJ/kg hot water to 2.43 MJ/kg at 25 C) = 1.48-1.59 L per kWh of heat.
    Heat at the tower is IT heat plus chiller compressor work, about 1.0-1.15 x IT energy.
    Blowdown adds 1/(CoC - 1) of evaporation (CoC 3 to 6).
    Floor: 60% of heat leaves by evaporation, CoC 6, no compressor term.
    Ceiling: all heat evaporates, compressor term 1.15, CoC 3."""
    floor = 3.6 / 2.43 * 0.6 * (1 + 1 / (6 - 1))
    ceiling = 3.6 / 2.26 * 1.15 * (1 + 1 / (3 - 1))
    assert 1.0 < floor < ceiling < 3.0
    for season in Season:
        wue = compute_facility_ledger(CoolingType.EVAPORATIVE, 15.0, season, "bengaluru").wue
        assert floor <= wue <= ceiling, (season, wue, floor, ceiling)


def test_annual_evaporative_wue_is_near_the_physical_maximum_at_design_coc():
    """Documents a finding rather than a pass/fail of the physics: at the engine's stated CoC of 4.5 the ceiling
    (all heat evaporates, full compressor load) is 2.36 L/kWh, and the engine's annual figure is 2.10 -
    about 89% of that ceiling, so the engine assumes nearly all heat leaves by evaporation."""
    ceiling_at_4_5 = 3.6 / 2.26 * 1.15 * (1 + 1 / (4.5 - 1))
    wue = compute_facility_ledger(CoolingType.EVAPORATIVE, 15.0, Season.ANNUAL_AVERAGE, "bengaluru").wue
    assert wue <= ceiling_at_4_5
    assert wue / ceiling_at_4_5 > 0.85


def test_dry_cooling_uses_almost_no_water():
    assert compute_facility_ledger(CoolingType.DRY_COOLING, 15.0, Season.DRY_SUMMER, "bengaluru").wue < 0.1
