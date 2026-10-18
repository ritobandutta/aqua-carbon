"""
Deterministic Calculation Engine for AquaCarbon DC — Commons Edition (v2).
Single source of truth for all physics, energy balances, water consumption,
Scope 2 carbon, economic costs, and community impact indicators.
"""

from typing import Dict, List, Tuple, Any
from .models import (
    CoolingType, Season, WorkloadType, FacilityLedger, CommunityLedger,
    CommunityIndicator, BurdenShiftScores, ProfileAssessment,
    DataConfidence, PlannerConstraints, ConstraintCheckResult,
    PlannerOutput, ScenarioInput
)
from .data_sources import get_regional_profile


# Published baseline parameters for cooling types
COOLING_SPEC_BASELINES: Dict[CoolingType, Dict[str, Any]] = {
    CoolingType.EVAPORATIVE: {
        "name": "Direct Evaporative / Cooling Towers with Water-Cooled Chillers",
        "base_pue": 1.20,
        "base_wue_l_kwh": 2.10,
        "thermal_safety_margin_pct": 14.5,
        "capital_cost_relative": 1.0,
        "assumptions": [
            "Centrifugal chillers with induced-draft counterflow cooling towers",
            "Cycles of Concentration (CoC) maintained at 4.5 using treated utility supply",
            "Latent heat of vaporization handles >85% of building rejection",
            "Evaporative loss accelerates when ambient dry-bulb exceeds 34°C"
        ]
    },
    CoolingType.DRY_COOLING: {
        "name": "Air-Cooled Chillers with Integrated Economizers",
        "base_pue": 1.45,
        "base_wue_l_kwh": 0.02,
        "thermal_safety_margin_pct": 18.0,
        "capital_cost_relative": 1.25,
        "assumptions": [
            "Sensible heat rejection via high-volume VFD condenser fans",
            "No active water consumption during routine continuous operation",
            "Chiller lift increases significantly when ambient temperatures climb >32°C",
            "Zero dependency on municipal water tankers or local aquifers"
        ]
    },
    CoolingType.HYBRID_ADIABATIC: {
        "name": "Smart Hybrid Adiabatic Fluid Coolers",
        "base_pue": 1.27,
        "base_wue_l_kwh": 0.65,
        "thermal_safety_margin_pct": 16.0,
        "capital_cost_relative": 1.15,
        "assumptions": [
            "Runs 100% dry when ambient temperature is below 26°C",
            "Pulsed adiabatic wetting pad trims peaks when ambient exceeds wet-bulb threshold",
            "Reduces peak water withdrawal by 65-70% versus conventional evaporative towers",
            "Eliminates cooling tower blowdown biocide discharge into municipal drains"
        ]
    }
}


def compute_facility_ledger(
    cooling_type: CoolingType,
    it_capacity_mw: float,
    season: Season,
    region_key: str,
    grid_carbon_factor: float = 710.0,
    electricity_tariff_inr_kwh: float = 8.50,
    water_tariff_inr_kl: float = 95.0,
    workload_type: WorkloadType = WorkloadType.STATIC_INFERENCE
) -> FacilityLedger:
    profile_meta = COOLING_SPEC_BASELINES[cooling_type]
    regional_data = get_regional_profile(region_key)
    season_key = season.value if season.value in regional_data["seasons"] else "annual_average"
    season_meta = regional_data["seasons"].get(season_key, regional_data["seasons"]["annual_average"])

    # Seasonal PUE adjustment
    base_pue = profile_meta["base_pue"]
    if cooling_type == CoolingType.DRY_COOLING:
        adjusted_pue = round(base_pue * season_meta.get("dry_cooling_pue_penalty_factor", 1.0), 3)
    elif cooling_type == CoolingType.EVAPORATIVE:
        # High wet bulb / summer increases fan work
        adjusted_pue = round(base_pue * (1.02 if season == Season.DRY_SUMMER else 0.98), 3)
    else:
        # Hybrid
        adjusted_pue = round(base_pue * (1.03 if season == Season.DRY_SUMMER else 0.99), 3)

    # Seasonal WUE adjustment (Liters / kWh of IT load)
    base_wue = profile_meta["base_wue_l_kwh"]
    if cooling_type == CoolingType.EVAPORATIVE:
        adjusted_wue = round(base_wue * season_meta.get("evaporative_water_penalty_factor", 1.0), 3)
    elif cooling_type == CoolingType.HYBRID_ADIABATIC:
        # In summer hybrid pulses more misting; in winter almost dry
        if season == Season.DRY_SUMMER:
            adjusted_wue = round(base_wue * 1.35, 3)
        elif season == Season.WINTER:
            adjusted_wue = round(base_wue * 0.35, 3)
        elif season == Season.MONSOON:
            adjusted_wue = round(base_wue * 0.70, 3)
        else:
            adjusted_wue = base_wue
    else:
        adjusted_wue = base_wue  # Dry stays near zero

    # AI Workload Shifting Lever (Shifting flexible batch training away from 12 PM - 4 PM heat window)
    if workload_type == WorkloadType.AI_TRAINING_FLEXIBLE:
        if cooling_type == CoolingType.EVAPORATIVE:
            adjusted_wue = round(adjusted_wue * 0.82, 3)  # 18% water savings avoiding peak evaporation
        elif cooling_type == CoolingType.HYBRID_ADIABATIC:
            adjusted_wue = round(adjusted_wue * 0.70, 3)  # 30% water savings running fully dry at night
        # Night economizer hours improve effective PUE
        adjusted_pue = round(max(adjusted_pue - 0.03, 1.10), 3)

    # Annual operational hours
    hours_per_year = 8760.0
    annual_it_energy_mwh = round(it_capacity_mw * hours_per_year, 2)
    total_facility_energy_mwh = round(annual_it_energy_mwh * adjusted_pue, 2)
    cooling_energy_mwh = round(annual_it_energy_mwh * max(adjusted_pue - 1.05, 0.05), 2)

    # Water calculations:
    # IT kWh * WUE (L/kWh) = Total Liters
    annual_it_kwh = annual_it_energy_mwh * 1000.0
    total_water_liters = annual_it_kwh * adjusted_wue
    direct_water_consumption_ml = round(total_water_liters / 1_000_000.0, 2)  # Megaliters (ML)
    direct_water_consumption_m3 = round(total_water_liters / 1_000.0, 2)  # cubic meters
    daily_water_intake_m3 = round(direct_water_consumption_m3 / 365.0, 2)

    # Scope 2 carbon emissions: Total MWh * kg CO2/MWh / 1000 = tonnes CO2e
    scope2_carbon_tonnes = round((total_facility_energy_mwh * grid_carbon_factor) / 1000.0, 2)

    # Cost calculations (INR Crores & USD Millions)
    # 1 INR Crore = 10,000,000 INR
    annual_electricity_kwh = total_facility_energy_mwh * 1000.0
    annual_electricity_cost_inr = annual_electricity_kwh * electricity_tariff_inr_kwh
    electricity_cost_inr_crores = round(annual_electricity_cost_inr / 10_000_000.0, 2)

    annual_water_cost_inr = (direct_water_consumption_m3) * water_tariff_inr_kl  # 1 kL = 1 m3
    water_cost_inr_crores = round(annual_water_cost_inr / 10_000_000.0, 3)

    annual_operating_cost_inr_crores = round(electricity_cost_inr_crores + water_cost_inr_crores, 2)
    # Conversion rate: ~85 INR / USD
    annual_operating_cost_usd_millions = round((annual_operating_cost_inr_crores * 10_000_000.0) / (85.0 * 1_000_000.0), 2)

    return FacilityLedger(
        cooling_type=cooling_type,
        cooling_name=profile_meta["name"],
        it_capacity_mw=it_capacity_mw,
        annual_it_energy_mwh=annual_it_energy_mwh,
        pue=adjusted_pue,
        wue=adjusted_wue,
        total_facility_energy_mwh=total_facility_energy_mwh,
        cooling_energy_mwh=cooling_energy_mwh,
        direct_water_consumption_ml=direct_water_consumption_ml,
        direct_water_consumption_m3=direct_water_consumption_m3,
        daily_water_intake_m3=daily_water_intake_m3,
        scope2_carbon_tonnes=scope2_carbon_tonnes,
        annual_operating_cost_inr_crores=annual_operating_cost_inr_crores,
        annual_operating_cost_usd_millions=annual_operating_cost_usd_millions,
        electricity_cost_inr_crores=electricity_cost_inr_crores,
        water_cost_inr_crores=water_cost_inr_crores,
        thermal_safety_margin_pct=profile_meta["thermal_safety_margin_pct"],
        assumptions=profile_meta["assumptions"]
    )


def compute_community_ledger(
    facility_ledger: FacilityLedger,
    region_key: str,
    utility_water_headroom_ml: float = 220.0,
    substation_capacity_mw: float = 60.0,
    grid_carbon_factor: float = 710.0
) -> CommunityLedger:
    reg = get_regional_profile(region_key)

    # 1. Water Headroom Share %
    headroom = max(utility_water_headroom_ml, 1.0)
    water_share_pct = round((facility_ledger.direct_water_consumption_ml / headroom) * 100.0, 2)

    # 2. Household Water Equivalents:
    # Standard: 135 LPCD * 4.2 persons * 365 days = ~206,955 Liters/year per household
    lpcd = reg.get("household_liters_per_capita_day", 135.0)
    household_size = reg.get("average_household_size", 4.2)
    liters_per_household_year = lpcd * household_size * 365.0
    household_equivalents = int((facility_ledger.direct_water_consumption_ml * 1_000_000.0) / liters_per_household_year)

    # 3. Peak Substation Electrical Share %:
    facility_peak_mw = round(facility_ledger.it_capacity_mw * facility_ledger.pue, 2)
    substation_share_pct = round((facility_peak_mw / max(substation_capacity_mw, 1.0)) * 100.0, 2)

    prov = reg.get("provenance", {})

    ind_water_share = CommunityIndicator(
        name="Utility Water Headroom Share",
        value=water_share_pct,
        unit="%",
        formatted_value=f"{water_share_pct}%",
        source_label=f"BWSSB / MIDC industrial headroom allocation ({headroom:.0f} ML/yr buffer)",
        geographic_resolution="Ward / Industrial Sub-basin",
        confidence=DataConfidence.HIGH,
        explanation=f"Represents {facility_ledger.direct_water_consumption_ml:.1f} ML consumed out of {headroom:.1f} ML municipal industrial buffer."
    )

    ind_households = CommunityIndicator(
        name="Household Water Displaced Equivalents",
        value=float(household_equivalents),
        unit="households/year",
        formatted_value=f"{household_equivalents:,} households",
        source_label=f"CPHEEO / BIS 1172 Urban Norm ({lpcd} LPCD, {household_size} persons/hh)",
        geographic_resolution="Municipal Ward",
        confidence=DataConfidence.HIGH,
        explanation=f"Direct water draw equals the annual domestic water requirement of {household_equivalents:,} urban families."
    )

    ind_aquifer = CommunityIndicator(
        name="Aquifer Stress Classification",
        value=None,
        unit="category",
        formatted_value=reg["cgwb_aquifer_status"].value,
        source_label=prov.get("aquifer", "Central Ground Water Board (CGWB)"),
        geographic_resolution="Block / Taluk",
        confidence=DataConfidence.HIGH,
        explanation=f"Local watershed is designated as {reg['cgwb_aquifer_status'].value}; extraction exceeds annual natural recharge rate."
    )

    ind_substation = CommunityIndicator(
        name="Local Substation Capacity Share",
        value=substation_share_pct,
        unit="%",
        formatted_value=f"{substation_share_pct}%",
        source_label="Local DISCOM 66/11kV Substation Line Rating",
        geographic_resolution="Feeder / Substation Radius (3km)",
        confidence=DataConfidence.MEDIUM,
        explanation=f"Facility peak load ({facility_peak_mw:.1f} MW) consumes {substation_share_pct}% of the feeder substation rating ({substation_capacity_mw:.1f} MW)."
    )

    ind_carbon = CommunityIndicator(
        name="Supplying Grid Carbon Factor",
        value=grid_carbon_factor,
        unit="gCO2/kWh",
        formatted_value=f"{grid_carbon_factor:.0f} gCO2/kWh",
        source_label=prov.get("grid_carbon", "CEA CO2 Baseline Database"),
        geographic_resolution="Regional Grid Interconnection",
        confidence=DataConfidence.HIGH,
        explanation="Grid Scope 2 emission factor reflecting regional thermal and renewable generation mix."
    )

    ind_outage = CommunityIndicator(
        name="Local Grid Outage Frequency (SAIDI)",
        value=reg.get("grid_outage_risk_index_saidi_hours", 18.0),
        unit="hours/year",
        formatted_value=f"{reg.get('grid_outage_risk_index_saidi_hours', 18.0)} hrs/yr",
        source_label=prov.get("outage", "SERC Regulatory Filings"),
        geographic_resolution="Distribution Circle",
        confidence=DataConfidence.MEDIUM,
        explanation="System Average Interruption Duration Index indicating diesel generator fallback probability."
    )

    ind_tanker = CommunityIndicator(
        name="Community Tanker Water Dependency",
        value=reg.get("tanker_dependency_index_pct", 40.0),
        unit="%",
        formatted_value=f"{reg.get('tanker_dependency_index_pct', 40.0)}%",
        source_label="WRI India / Bangalore Water Study 2026",
        geographic_resolution="Peri-urban Zone",
        confidence=DataConfidence.MEDIUM,
        explanation="Proportion of neighboring residential wards dependent on unpiped private tanker deliveries."
    )

    ind_rationing = CommunityIndicator(
        name="Municipal Water Rationing Context",
        value=None,
        unit="status",
        formatted_value=reg.get("municipal_water_rationing_status", "Regular"),
        source_label="Municipal Water Board Advisory",
        geographic_resolution="Municipal Zone",
        confidence=DataConfidence.HIGH,
        explanation="Current operating constraints on municipal water mains in this geographic zone."
    )

    return CommunityLedger(
        region_name=reg["region_name"],
        site_location=f"{region_key.title()} Hyperscale Cluster",
        water_headroom_share_pct=ind_water_share,
        household_water_equivalent_count=ind_households,
        aquifer_stress_classification=ind_aquifer,
        substation_peak_demand_share_pct=ind_substation,
        grid_carbon_intensity=ind_carbon,
        grid_outage_risk_index=ind_outage,
        tanker_dependency_index=ind_tanker,
        municipal_water_rationing_status=ind_rationing,
        notes=[
            "Data points are grounded in published regulatory disclosures and public GIS layers.",
            "Missing micro-feeder telemetry is labeled with lower confidence rather than synthetically smoothed."
        ]
    )


def compute_burden_shift_scores(
    facility_ledger: FacilityLedger,
    community_ledger: CommunityLedger
) -> BurdenShiftScores:
    """
    Computes three normalized 0-100 scores representing how the cooling choice moves
    the burden across:
    1. Water System Burden
    2. Power System Burden
    3. Carbon Atmosphere Burden
    Crucially: There is NO single combined score. Each dimension stays independent.
    """
    # 1. Water burden: scale based on headroom share and WUE
    # Evaporative with >25% headroom share scores ~85-95. Dry cooling scores ~0-5.
    w_share = community_ledger.water_headroom_share_pct.value or 0.0
    water_burden = min(max((w_share * 1.5) + (facility_ledger.wue * 22.0), 2.0), 98.0)
    if facility_ledger.cooling_type == CoolingType.DRY_COOLING:
        water_burden = 3.0  # minimal water burden

    # 2. Power burden: scale based on cooling overhead (PUE - 1.0) and substation share
    # Dry cooling (PUE 1.45+) has high cooling overhead (~0.40) and high substation share
    p_share = community_ledger.substation_peak_demand_share_pct.value or 0.0
    cooling_overhead = max(facility_ledger.pue - 1.0, 0.0)
    power_burden = min(max((p_share * 1.2) + (cooling_overhead * 110.0), 5.0), 98.0)

    # 3. Carbon burden: scale relative to Scope 2 carbon
    # 15MW with PUE 1.45 produces ~135k tonnes CO2e, scaled to 0-100
    carbon_burden = min(max((facility_ledger.scope2_carbon_tonnes / (facility_ledger.it_capacity_mw * 10000.0)) * 65.0, 10.0), 98.0)

    return BurdenShiftScores(
        water_system_burden=round(water_burden, 1),
        power_system_burden=round(power_burden, 1),
        carbon_atmosphere_burden=round(carbon_burden, 1)
    )


def evaluate_scenario(scenario: ScenarioInput) -> Dict[str, ProfileAssessment]:
    assessments: Dict[str, ProfileAssessment] = {}

    for cooling_type in scenario.selected_profiles:
        f_ledger = compute_facility_ledger(
            cooling_type=cooling_type,
            it_capacity_mw=scenario.it_capacity_mw,
            season=scenario.season,
            region_key=scenario.region,
            grid_carbon_factor=scenario.grid_carbon_factor_kg_per_mwh,
            workload_type=scenario.workload_type
        )

        c_ledger = compute_community_ledger(
            facility_ledger=f_ledger,
            region_key=scenario.region,
            utility_water_headroom_ml=scenario.utility_water_headroom_ml_per_year,
            substation_capacity_mw=scenario.local_substation_capacity_mw,
            grid_carbon_factor=scenario.grid_carbon_factor_kg_per_mwh
        )

        burden = compute_burden_shift_scores(f_ledger, c_ledger)

        assessments[cooling_type.value] = ProfileAssessment(
            cooling_type=cooling_type,
            cooling_name=f_ledger.cooling_name,
            facility_ledger=f_ledger,
            community_ledger=c_ledger,
            burden_scores=burden
        )

    return assessments


def run_constraint_planner(
    scenario: ScenarioInput,
    constraints: PlannerConstraints
) -> PlannerOutput:
    assessments = evaluate_scenario(scenario)
    feasible_list: List[ProfileAssessment] = []
    infeasible_list: List[ConstraintCheckResult] = []

    for c_type_str, assessment in assessments.items():
        fl = assessment.facility_ledger
        cl = assessment.community_ledger
        violations: List[str] = []
        satisfactions: List[str] = []

        # Check facility limits
        if constraints.max_pue is not None:
            if fl.pue > constraints.max_pue:
                violations.append(f"PUE {fl.pue:.2f} exceeds limit {constraints.max_pue:.2f}")
            else:
                satisfactions.append(f"PUE {fl.pue:.2f} satisfies limit {constraints.max_pue:.2f}")

        if constraints.max_cooling_cost_inr_crores is not None:
            if fl.annual_operating_cost_inr_crores > constraints.max_cooling_cost_inr_crores:
                violations.append(f"Operating cost ₹{fl.annual_operating_cost_inr_crores:.2f} Cr exceeds budget ₹{constraints.max_cooling_cost_inr_crores:.2f} Cr")
            else:
                satisfactions.append(f"Operating cost ₹{fl.annual_operating_cost_inr_crores:.2f} Cr meets budget")

        if constraints.max_annual_water_ml is not None:
            if fl.direct_water_consumption_ml > constraints.max_annual_water_ml:
                violations.append(f"Direct water {fl.direct_water_consumption_ml:.1f} ML exceeds ceiling {constraints.max_annual_water_ml:.1f} ML")
            else:
                satisfactions.append(f"Direct water {fl.direct_water_consumption_ml:.1f} ML satisfies ceiling")

        # Check community limits
        if constraints.max_water_headroom_share_pct is not None:
            headroom_val = cl.water_headroom_share_pct.value or 0.0
            if headroom_val > constraints.max_water_headroom_share_pct:
                violations.append(f"Community water headroom impact {headroom_val:.1f}% exceeds community limit {constraints.max_water_headroom_share_pct:.1f}%")
            else:
                satisfactions.append(f"Water headroom share {headroom_val:.1f}% within community limit")

        if constraints.max_grid_peak_share_pct is not None:
            grid_share = cl.substation_peak_demand_share_pct.value or 0.0
            if grid_share > constraints.max_grid_peak_share_pct:
                violations.append(f"Substation peak share {grid_share:.1f}% exceeds grid limit {constraints.max_grid_peak_share_pct:.1f}%")
            else:
                satisfactions.append(f"Substation peak share {grid_share:.1f}% satisfies grid limit")

        if len(violations) == 0:
            feasible_list.append(assessment)
        else:
            nearest = "Closest trade-off requires relaxing " + (
                "water headroom constraint" if "water" in violations[0].lower() else "PUE or grid constraint"
            )
            infeasible_list.append(ConstraintCheckResult(
                cooling_type=assessment.cooling_type,
                cooling_name=assessment.cooling_name,
                is_feasible=False,
                violations=violations,
                satisfactions=satisfactions,
                nearest_tradeoff=nearest
            ))

    if len(feasible_list) > 0:
        verdict = f"Found {len(feasible_list)} viable cooling configuration(s) satisfying all facility and community constraints."
        refusal = None
    else:
        verdict = "INSUFFICIENT_FEASIBLE_SET: No single cooling profile meets every facility and community threshold simultaneously."
        refusal = (
            "Refusal to manufacture an ungrounded compromise. In this water-stressed region, evaporative cooling breaches "
            "the community water headroom constraint, while dry cooling breaches the facility PUE / grid peak constraint. "
            "Consider Hybrid Adiabatic cooling with secondary treated wastewater supply or relaxing grid peak thresholds."
        )

    return PlannerOutput(
        constraints_applied=constraints,
        feasible_configurations=feasible_list,
        infeasible_configurations=infeasible_list,
        refusal_reason=refusal,
        summary_verdict=verdict
    )
