"""
Data models and schemas for AquaCarbon DC — Commons Edition (v2).
Provides strongly typed contracts for scenarios, facility ledgers,
community ledgers, burden shifting, and verification results.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CoolingType(str, Enum):
    EVAPORATIVE = "evaporative"  # Direct Evaporative / Cooling Towers + Water-Cooled Chillers
    DRY_COOLING = "dry_cooling"  # Air-Cooled Chillers with Economizers
    HYBRID_ADIABATIC = "hybrid_adiabatic"  # Smart Trim Adiabatic + Dry Coolers


class Season(str, Enum):
    ANNUAL_AVERAGE = "annual_average"
    DRY_SUMMER = "dry_summer"
    MONSOON = "monsoon"
    WINTER = "winter"


class WorkloadType(str, Enum):
    STATIC_INFERENCE = "static_inference"  # 24/7 flat critical inference
    AI_TRAINING_FLEXIBLE = "ai_training_flexible"  # AI batch training/fine-tuning shifted off afternoon heat peak


class WaterStressLevel(str, Enum):
    LOW = "Low (<10%)"
    MEDIUM_HIGH = "Medium-High (20-40%)"
    HIGH = "High (40-80%)"
    EXTREMELY_HIGH = "Extremely High (>80%)"


class AquiferStatus(str, Enum):
    SAFE = "Safe"
    SEMI_CRITICAL = "Semi-Critical"
    CRITICAL = "Critical"
    OVER_EXPLOITED = "Over-Exploited"


class DataConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class FacilityLedger(BaseModel):
    cooling_type: CoolingType
    cooling_name: str
    it_capacity_mw: float
    annual_it_energy_mwh: float
    pue: float
    wue: float  # Liters / kWh IT load
    total_facility_energy_mwh: float
    cooling_energy_mwh: float
    direct_water_consumption_ml: float  # Megaliters (10^6 liters or 1000 m3)
    direct_water_consumption_m3: float
    daily_water_intake_m3: float
    scope2_carbon_tonnes: float  # tCO2e
    annual_operating_cost_inr_crores: float  # INR Crores (1 Cr = 10 Million INR)
    annual_operating_cost_usd_millions: float
    electricity_cost_inr_crores: float
    water_cost_inr_crores: float
    thermal_safety_margin_pct: float
    assumptions: List[str]


class CommunityIndicator(BaseModel):
    name: str
    value: Optional[float] = None
    unit: str
    formatted_value: str
    source_label: str
    geographic_resolution: str
    confidence: DataConfidence
    explanation: str


class CommunityLedger(BaseModel):
    region_name: str
    site_location: str
    water_headroom_share_pct: CommunityIndicator
    household_water_equivalent_count: CommunityIndicator
    aquifer_stress_classification: CommunityIndicator
    substation_peak_demand_share_pct: CommunityIndicator
    grid_carbon_intensity: CommunityIndicator
    grid_outage_risk_index: CommunityIndicator
    tanker_dependency_index: CommunityIndicator
    municipal_water_rationing_status: CommunityIndicator
    notes: List[str]


class BurdenShiftScores(BaseModel):
    water_system_burden: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 score of stress on local water systems")
    power_system_burden: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 score of stress on electrical grid")
    carbon_atmosphere_burden: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 score of carbon impact")


class ProfileAssessment(BaseModel):
    cooling_type: CoolingType
    cooling_name: str
    facility_ledger: FacilityLedger
    community_ledger: CommunityLedger
    burden_scores: BurdenShiftScores


class CoverageDisparityResult(BaseModel):
    area_name: str
    satellite_settlement_builtup_km2: float
    official_piped_water_coverage_km2: float
    disparity_ratio: float
    unmapped_tanker_dependent_population_estimate: int
    flags: List[str]
    confidence_impact: str
    recommended_ground_truth_actions: List[str]


class PlannerConstraints(BaseModel):
    max_cooling_cost_inr_crores: Optional[float] = None
    max_pue: Optional[float] = None
    max_annual_water_ml: Optional[float] = None
    max_water_headroom_share_pct: Optional[float] = None
    max_grid_peak_share_pct: Optional[float] = None
    min_data_confidence: Optional[DataConfidence] = None


class ConstraintCheckResult(BaseModel):
    cooling_type: CoolingType
    cooling_name: str
    is_feasible: bool
    violations: List[str]
    satisfactions: List[str]
    nearest_tradeoff: Optional[str] = None


class PlannerOutput(BaseModel):
    constraints_applied: PlannerConstraints
    feasible_configurations: List[ProfileAssessment]
    infeasible_configurations: List[ConstraintCheckResult]
    refusal_reason: Optional[str] = None
    summary_verdict: str


class VerificationCheckItem(BaseModel):
    metric_name: str
    claimed_value_in_brief: str
    engine_calculated_value: str
    matched: bool
    discrepancy_note: Optional[str] = None


class VerificationReport(BaseModel):
    status: str  # "PASSED" or "FLAGGED_MISMATCH"
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[VerificationCheckItem]
    signature: str
    verification_timestamp: str


class GeneratedBriefs(BaseModel):
    operator_brief_markdown: str
    community_brief_markdown: str
    verification_report: VerificationReport


class ScenarioInput(BaseModel):
    scenario_id: str = "bengaluru_whitefield_15mw"
    scenario_title: str = "Bengaluru Whitefield Hyperscale Facility"
    region: str = "Bengaluru, Karnataka, India"
    it_capacity_mw: float = 15.0
    season: Season = Season.ANNUAL_AVERAGE
    workload_type: WorkloadType = WorkloadType.STATIC_INFERENCE
    grid_carbon_factor_kg_per_mwh: float = 710.0  # National Southern Regional Grid average gCO2/kWh
    local_substation_capacity_mw: float = 60.0
    utility_water_headroom_ml_per_year: float = 250.0  # BWSSB industrial allocation buffer
    selected_profiles: List[CoolingType] = [
        CoolingType.EVAPORATIVE,
        CoolingType.DRY_COOLING,
        CoolingType.HYBRID_ADIABATIC
    ]
    constraints: Optional[PlannerConstraints] = None
