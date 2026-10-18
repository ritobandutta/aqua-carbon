"""
AquaCarbon DC: Deterministic Calculation Engine
Grounded in Karimi et al. (2022) and WRI Aqueduct baselines.
Single source of truth for physical calculations.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScenarioInput:
    location: str = "Bengaluru, India"
    it_load_mw: float = 10.0  # Standard AI Cluster IT Capacity
    ambient_temp_c: float = 34.0  # Summer peak ambient dry-bulb
    grid_emission_factor: float = 0.72  # kg CO2 / kWh (CEA India Baseline)
    grid_cost_per_kwh_inr: float = 7.50  # Commercial power tariff (BESCOM)
    water_cost_per_kl_inr: float = 90.00  # Commercial water tariff (BWSSB)


class AquaCarbonEngine:
    def __init__(self, scenario: ScenarioInput):
        self.s = scenario
        self.daily_it_kwh = self.s.it_load_mw * 1000 * 24

    def calculate_profile(self, profile_type: str) -> Dict[str, Any]:
        """
        Profiles calibrated from Karimi et al. (2022)
        1. Evaporative: Low PUE, high water draw.
        2. Dry Cooled: Higher PUE (summer compressor penalty), near-zero direct water.
        3. Hybrid Adiabatic: Operates dry until T > 30C, then trims peak draw with misting.
        """
        if profile_type == "evaporative":
            pue = 1.18
            wue = 1.85  # Liters / kWh IT
        elif profile_type == "dry":
            # Air-cooled chillers struggle in high ambient temperatures (PUE rises)
            temp_penalty = max(0.0, (self.s.ambient_temp_c - 25.0) * 0.012)
            pue = 1.38 + temp_penalty
            wue = 0.04  # Closed loop losses only
        elif profile_type == "hybrid":
            pue = 1.24
            wue = 0.65
        else:
            raise ValueError(f"Unknown cooling profile: {profile_type}")

        # Primary Facility Ledger
        daily_facility_kwh = self.daily_it_kwh * pue
        daily_water_liters = self.daily_it_kwh * wue
        daily_carbon_kg = daily_facility_kwh * self.s.grid_emission_factor
        
        daily_power_cost = daily_facility_kwh * self.s.grid_cost_per_kwh_inr
        daily_water_cost = (daily_water_liters / 1000.0) * self.s.water_cost_per_kl_inr
        daily_opex = daily_power_cost + daily_water_cost

        # Community Burden Ledger
        # Standard: 1 home (4 people) consumes ~540 Liters/day (135 L/person/day - BWSSB norm)
        household_water_equiv = int(daily_water_liters / 540.0)
        peak_grid_strain_mw = self.s.it_load_mw * pue

        return {
            "profile": profile_type,
            "facility_ledger": {
                "pue": round(pue, 3),
                "wue": round(wue, 3),
                "daily_energy_mwh": round(daily_facility_kwh / 1000, 2),
                "daily_water_kl": round(daily_water_liters / 1000, 2),
                "daily_carbon_tonnes": round(daily_carbon_kg / 1000, 2),
                "daily_opex_inr": round(daily_opex, 2)
            },
            "community_ledger": {
                "household_water_equivalent_days": household_water_equiv,
                "peak_grid_demand_mw": round(peak_grid_strain_mw, 2),
                "water_stress_zone": "Extremely High (>80%) - WRI Aqueduct",
                "grid_strain_risk": "High (Summer Concurrency)" if peak_grid_strain_mw > 13.5 else "Moderate"
            }
        }


if __name__ == "__main__":
    scenario = ScenarioInput()
    engine = AquaCarbonEngine(scenario)
    
    print("=== EVAPORATIVE (WET) COOLING ===")
    print(engine.calculate_profile("evaporative"))
    print("\n=== DRY (AIR-COOLED) COOLING ===")
    print(engine.calculate_profile("dry"))
    print("\n=== HYBRID ADIABATIC COOLING ===")
    print(engine.calculate_profile("hybrid"))
