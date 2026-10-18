"""
Claim checking for permit review. Pure and deterministic: no I/O, no LLM.

An applicant states a figure ("hybrid cooling will use 40 ML of water a year"). We compare it with the
engine's modelled low / central / high range for the same scenario and profile. All claimable metrics are
"lower is better", so a claim BELOW the modelled range is more favourable than the model's best case and
deserves evidence, while a claim ABOVE the range is more conservative than the model.

This is a prompt for questions, not a finding of fault: the model's inputs are illustrative until
docs/DATA_SOURCES.md says otherwise, and every verdict carries that caveat.
"""

from typing import Dict, Literal, Optional, Tuple
from pydantic import BaseModel, Field
from .calculator import evaluate_with_bands, evaluate_scenario
from .data_sources import VALUE_STATUS
from .models import CoolingType, ScenarioInput, Season, WorkloadType

# metric id -> (human label, unit)
CLAIMABLE_METRICS: Dict[str, Tuple[str, str]] = {
    "pue": ("Power Usage Effectiveness", ""),
    "wue_l_per_kwh": ("Water Usage Effectiveness", "L/kWh"),
    "direct_water_ml": ("Annual direct water use", "ML"),
    "facility_energy_mwh": ("Annual facility energy", "MWh"),
    "scope2_carbon_tonnes": ("Annual Scope 2 carbon", "tCO2e"),
    "operating_cost_inr_crores": ("Annual operating cost", "INR Cr"),
}

Verdict = Literal["within_modelled_range", "below_modelled_range", "above_modelled_range"]

CAVEAT = (
    "Modelled values use inputs that are not yet verified against official sources, so this verdict is a prompt "
    "for questions, not a finding that the applicant is wrong."
)


class ClaimScenario(BaseModel):
    region: str
    it_capacity_mw: float = Field(gt=0)
    season: Season = Season.ANNUAL_AVERAGE
    workload_type: WorkloadType = WorkloadType.STATIC_INFERENCE
    grid_carbon_factor_kg_per_mwh: float = 710.0

    def to_scenario(self, cooling: CoolingType) -> ScenarioInput:
        return ScenarioInput(
            region=self.region, it_capacity_mw=self.it_capacity_mw, season=self.season,
            workload_type=self.workload_type, grid_carbon_factor_kg_per_mwh=self.grid_carbon_factor_kg_per_mwh,
            selected_profiles=[cooling],
        )


class ClaimVerdict(BaseModel):
    cooling_type: CoolingType
    metric: str
    label: str
    unit: str
    claimed_value: float
    modelled_low: float
    modelled_central: float
    modelled_high: float
    verdict: Verdict
    claim_vs_central_pct: Optional[float]
    inputs_status: Literal["illustrative_unverified", "published"]
    caveat: str = CAVEAT


def _inputs_status() -> str:
    return "published" if VALUE_STATUS and all(v == "published" for v in VALUE_STATUS.values()) else "illustrative_unverified"


def check_claim(scenario: ClaimScenario, cooling_type: CoolingType, metric: str, claimed_value: float) -> ClaimVerdict:
    if metric not in CLAIMABLE_METRICS:
        raise ValueError(f"Unknown metric '{metric}'. Claimable metrics: {', '.join(sorted(CLAIMABLE_METRICS))}.")
    sc = scenario.to_scenario(cooling_type)
    band = evaluate_with_bands(sc)[cooling_type.value][metric]
    low, central, high = band["low"], band["central"], band["high"]
    eps = 1e-9 * max(abs(high), 1.0)
    verdict: Verdict = (
        "below_modelled_range" if claimed_value < low - eps
        else "above_modelled_range" if claimed_value > high + eps
        else "within_modelled_range"
    )
    label, unit = CLAIMABLE_METRICS[metric]
    return ClaimVerdict(
        cooling_type=cooling_type, metric=metric, label=label, unit=unit, claimed_value=claimed_value,
        modelled_low=low, modelled_central=central, modelled_high=high, verdict=verdict,
        claim_vs_central_pct=None if central == 0 else round((claimed_value - central) / central * 100.0, 1),
        inputs_status=_inputs_status(),  # type: ignore[arg-type]
    )
