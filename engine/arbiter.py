"""
24-Hour Arbiter & AI Dispatcher Engine
Inspired by FortyGuard's Agentic-Arbiter (Free-Cooling Hourly Scheduler)
and GCC 1st-Place Winner CooL-LLM (AI Workload & Thermal Loop Optimizer).

Models 24-hour diurnal ambient temperature curves and dynamically schedules:
1. Free-Cooling Air Economizer during cool night hours (chillers turned OFF).
2. Dry Chiller operation during mild morning hours.
3. CooL-LLM AI Batch Workload Shifting (-40% non-critical compute) + Adiabatic Misting during peak afternoon heat.
4. Substation Peak-Shaving during evening residential grid peaks.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from engine.models import ScenarioInput, Season, CoolingType
from engine.data_sources import get_regional_profile


class HourlyDispatchStep(BaseModel):
    hour: int
    time_label: str
    ambient_temp_c: float
    ambient_rh_pct: float
    cooling_mode: str
    mode_description: str
    it_load_mw: float
    facility_power_mw: float
    pue: float
    water_intake_m3_h: float
    grid_carbon_kg_h: float
    household_water_hours: float
    chiller_status: str


class ArbiterSimulationResult(BaseModel):
    scenario_title: str
    region: str
    season: str
    base_it_capacity_mw: float
    ai_flexibility_pct: float
    total_water_consumed_m3: float
    baseline_water_consumed_m3: float
    water_saved_liters: float
    water_savings_pct: float
    households_water_restored_days: float
    peak_grid_demand_mw: float
    baseline_peak_grid_demand_mw: float
    peak_grid_shaved_mw: float
    total_daily_energy_mwh: float
    total_daily_carbon_tonnes: float
    free_cooling_hours: int
    workload_shifted_mwh: float
    hourly_steps: List[HourlyDispatchStep]


def simulate_24h_arbiter(
    scenario: ScenarioInput,
    ai_flexibility_pct: float = 40.0
) -> ArbiterSimulationResult:
    """
    Simulates hour-by-hour 24-hour optimal thermal dispatch and AI batch shifting.
    """
    region_data = get_regional_profile(scenario.region)
    season_key = scenario.season.value if scenario.season.value in region_data["seasons"] else "annual_average"
    season_meta = region_data["seasons"].get(season_key, region_data["seasons"]["annual_average"])
    
    avg_temp = season_meta["ambient_dry_bulb_c"]
    avg_rh = season_meta["relative_humidity_pct"]
    base_it = scenario.it_capacity_mw
    
    # 24-hour diurnal temperature cycle offsets around mean
    # (Troughs at 5AM -5°C, peaks at 3PM +6°C)
    temp_offsets = [
        -4.0, -4.5, -4.8, -5.0, -5.2, -4.8, -3.5, -1.0,
        1.5,   3.5,  5.0,  5.8,  6.0,  5.8,  5.2,  4.0,
        2.5,   1.0, -0.5, -1.8, -2.5, -3.0, -3.5, -3.8
    ]

    hourly_steps: List[HourlyDispatchStep] = []
    
    total_water_m3 = 0.0
    baseline_water_m3 = 0.0
    max_facility_power = 0.0
    baseline_max_facility_power = base_it * 1.45  # Standard dry chiller peak
    total_energy_mwh = 0.0
    total_carbon_kg = 0.0
    free_cooling_hrs = 0
    shifted_mwh = 0.0
    
    grid_emission_factor = getattr(scenario, "grid_carbon_factor_kg_per_mwh", None) or region_data.get("grid_emission_factor_g_kwh", 710.0)

    for h in range(24):
        time_label = f"{h:02d}:00"
        t_ambient = round(avg_temp + temp_offsets[h], 1)
        # Relative humidity typically inversely correlates with temperature
        rh = max(20.0, min(95.0, round(avg_rh - (temp_offsets[h] * 2.5), 1)))

        # Baseline: Constant IT load with standard evaporative cooling
        base_hourly_water = (base_it * 1000.0 * 2.63) / 24.0 / 1000.0  # m3/h
        baseline_water_m3 += base_hourly_water

        # Arbiter + CooL-LLM Dynamic Logic:
        # 1. Night Economizer Mode (Temp < 24°C, approx 00:00 - 06:00 & 22:00 - 23:00)
        if t_ambient <= 24.0:
            cooling_mode = "Free-Cooling Economizer"
            mode_desc = "Outside air enthalpy sufficient; mechanical chillers powered OFF."
            chiller_status = "OFF (Bypassed)"
            pue = 1.10
            water_intake = 0.0  # Zero direct water
            # Resorb delayed AI batch compute if night
            it_load = base_it * (1.15 if (h >= 22 or h <= 4) else 1.0)
            free_cooling_hrs += 1

        # 2. Peak Heat & Grid Stress Hours (12:00 - 16:00, Temp > 30°C)
        elif 12 <= h <= 16:
            cooling_mode = "CooL-LLM AI Shift + Adiabatic Mist"
            mode_desc = f"Deferred {ai_flexibility_pct:.0f}% non-critical AI batch jobs; pulse-misting caps compressor lift."
            chiller_status = "Reduced Duty (Misting)"
            # Workload shifted away from peak heat
            shift_ratio = (100.0 - ai_flexibility_pct) / 100.0
            it_load = base_it * shift_ratio
            shifted_mwh += base_it * (ai_flexibility_pct / 100.0)
            pue = 1.24
            # Minimal adiabatic pulse misting
            water_intake = (it_load * 1000.0 * 0.85) / 24.0 / 1000.0

        # 3. Evening Residential Peak (18:00 - 21:00)
        elif 18 <= h <= 21:
            cooling_mode = "Substation Peak-Shave"
            mode_desc = "Grid peak strain mitigation; trimmed thermal margins to protect neighborhood feeders."
            chiller_status = "Variable Speed Partial"
            it_load = base_it * 0.90
            shifted_mwh += base_it * 0.10
            pue = 1.26
            water_intake = (it_load * 1000.0 * 0.40) / 24.0 / 1000.0

        # 4. Standard Daytime Mild Chiller (07:00 - 11:00 & 17:00)
        else:
            cooling_mode = "Dry Economizer Assisted"
            mode_desc = "Dry cooling fan coils with partial free-cooling assist."
            chiller_status = "Active Economizer"
            it_load = base_it
            pue = 1.28
            water_intake = 0.0

        facility_power = round(it_load * pue, 2)
        total_water_m3 += water_intake
        total_energy_mwh += facility_power
        total_carbon_kg += (facility_power * 1000.0 * (grid_emission_factor / 1000.0))
        max_facility_power = max(max_facility_power, facility_power)

        # Household water equivalent (135 LPCD * 4.2 = 567 L/day = 23.6 L/hour)
        hh_hours = round((water_intake * 1000.0) / 23.6, 1)

        hourly_steps.append(HourlyDispatchStep(
            hour=h,
            time_label=time_label,
            ambient_temp_c=t_ambient,
            ambient_rh_pct=rh,
            cooling_mode=cooling_mode,
            mode_description=mode_desc,
            it_load_mw=round(it_load, 2),
            facility_power_mw=facility_power,
            pue=round(pue, 2),
            water_intake_m3_h=round(water_intake, 2),
            grid_carbon_kg_h=round(facility_power * grid_emission_factor, 1),
            household_water_hours=hh_hours,
            chiller_status=chiller_status
        ))

    water_saved_l = max(0.0, (baseline_water_m3 - total_water_m3) * 1000.0)
    water_savings_pct = round((water_saved_l / (baseline_water_m3 * 1000.0)) * 100.0, 1) if baseline_water_m3 > 0 else 0.0
    hh_days_restored = round(water_saved_l / 567.0, 1)
    peak_shaved_mw = max(0.0, round(baseline_max_facility_power - max_facility_power, 2))

    return ArbiterSimulationResult(
        scenario_title=scenario.scenario_title,
        region=scenario.region,
        season=scenario.season.value,
        base_it_capacity_mw=base_it,
        ai_flexibility_pct=ai_flexibility_pct,
        total_water_consumed_m3=round(total_water_m3, 2),
        baseline_water_consumed_m3=round(baseline_water_m3, 2),
        water_saved_liters=round(water_saved_l, 0),
        water_savings_pct=water_savings_pct,
        households_water_restored_days=hh_days_restored,
        peak_grid_demand_mw=round(max_facility_power, 2),
        baseline_peak_grid_demand_mw=round(baseline_max_facility_power, 2),
        peak_grid_shaved_mw=peak_shaved_mw,
        total_daily_energy_mwh=round(total_energy_mwh, 2),
        total_daily_carbon_tonnes=round(total_carbon_kg / 1000.0, 2),
        free_cooling_hours=free_cooling_hrs,
        workload_shifted_mwh=round(shifted_mwh, 2),
        hourly_steps=hourly_steps
    )
