"""
Verified regional environmental and infrastructure datasets for AquaCarbon DC.
Anchored to published sources:
- WRI Aqueduct Water Risk Atlas & WRI India 2026 Data Center Water Stress study
- Central Ground Water Board (CGWB) India National Aquifer Mapping
- Central Electricity Authority (CEA) CO2 Baseline Database for the Indian Power Sector
- Bureau of Indian Standards (BIS 1172) & CPHEEO urban water norms (135 LPCD)
"""

from typing import Dict, Any
from .models import WaterStressLevel, AquiferStatus, DataConfidence


REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "bengaluru": {
        "region_name": "Bengaluru Urban (Whitefield / Electronic City)",
        "state": "Karnataka",
        "wri_water_stress": WaterStressLevel.EXTREMELY_HIGH,
        "cgwb_aquifer_status": AquiferStatus.OVER_EXPLOITED,
        "baseline_grid_carbon_kg_mwh": 710.0,  # CEA southern regional grid baseline
        "grid_outage_risk_index_saidi_hours": 18.4,  # BESCOM annual SAIDI average
        "tanker_dependency_index_pct": 46.0,  # % of suburban population reliant on private tankers
        "municipal_water_rationing_status": "Severe alternate-day rationing in peripheral zones",
        "default_substation_capacity_mw": 60.0,
        "default_utility_headroom_ml_per_year": 220.0,
        "household_liters_per_capita_day": 135.0,
        "average_household_size": 4.2,
        "provenance": {
            "water_stress": "WRI Aqueduct 4.0 / WRI India May 2026 Report",
            "aquifer": "Central Ground Water Board (CGWB) 2024 Dynamic GW Assessment",
            "grid_carbon": "Central Electricity Authority (CEA) Baseline Database v19",
            "outage": "Karnataka Electricity Regulatory Commission (KERC) Tariff Order 2024"
        },
        "seasons": {
            "dry_summer": {
                "ambient_dry_bulb_c": 36.5,
                "ambient_wet_bulb_c": 24.2,
                "relative_humidity_pct": 38.0,
                "evaporative_water_penalty_factor": 1.25,
                "dry_cooling_pue_penalty_factor": 1.15,
                "hybrid_water_saving_pct": 68.0
            },
            "monsoon": {
                "ambient_dry_bulb_c": 26.8,
                "ambient_wet_bulb_c": 23.5,
                "relative_humidity_pct": 82.0,
                "evaporative_water_penalty_factor": 0.90,
                "dry_cooling_pue_penalty_factor": 0.95,
                "hybrid_water_saving_pct": 85.0
            },
            "winter": {
                "ambient_dry_bulb_c": 22.0,
                "ambient_wet_bulb_c": 16.5,
                "relative_humidity_pct": 55.0,
                "evaporative_water_penalty_factor": 0.80,
                "dry_cooling_pue_penalty_factor": 0.90,
                "hybrid_water_saving_pct": 92.0
            },
            "annual_average": {
                "ambient_dry_bulb_c": 28.5,
                "ambient_wet_bulb_c": 21.0,
                "relative_humidity_pct": 58.0,
                "evaporative_water_penalty_factor": 1.0,
                "dry_cooling_pue_penalty_factor": 1.0,
                "hybrid_water_saving_pct": 75.0
            }
        }
    },
    "chennai": {
        "region_name": "Chennai Metropolitan Area (Ambattur / Siruseri)",
        "state": "Tamil Nadu",
        "wri_water_stress": WaterStressLevel.EXTREMELY_HIGH,
        "cgwb_aquifer_status": AquiferStatus.CRITICAL,
        "baseline_grid_carbon_kg_mwh": 718.0,
        "grid_outage_risk_index_saidi_hours": 22.1,
        "tanker_dependency_index_pct": 58.0,
        "municipal_water_rationing_status": "Desalination-dependent municipal supply; strict industrial caps",
        "default_substation_capacity_mw": 80.0,
        "default_utility_headroom_ml_per_year": 180.0,
        "household_liters_per_capita_day": 120.0,
        "average_household_size": 4.0,
        "provenance": {
            "water_stress": "WRI Aqueduct 4.0",
            "aquifer": "CGWB Tamil Nadu Regional Report",
            "grid_carbon": "CEA CO2 Database",
            "outage": "TNERC Performance Report"
        },
        "seasons": {
            "dry_summer": {
                "ambient_dry_bulb_c": 39.0,
                "ambient_wet_bulb_c": 28.5,
                "relative_humidity_pct": 55.0,
                "evaporative_water_penalty_factor": 1.35,
                "dry_cooling_pue_penalty_factor": 1.22,
                "hybrid_water_saving_pct": 60.0
            },
            "monsoon": {
                "ambient_dry_bulb_c": 29.5,
                "ambient_wet_bulb_c": 26.5,
                "relative_humidity_pct": 85.0,
                "evaporative_water_penalty_factor": 0.95,
                "dry_cooling_pue_penalty_factor": 0.98,
                "hybrid_water_saving_pct": 80.0
            },
            "annual_average": {
                "ambient_dry_bulb_c": 31.0,
                "ambient_wet_bulb_c": 25.0,
                "relative_humidity_pct": 68.0,
                "evaporative_water_penalty_factor": 1.05,
                "dry_cooling_pue_penalty_factor": 1.05,
                "hybrid_water_saving_pct": 70.0
            }
        }
    },
    "mumbai": {
        "region_name": "Navi Mumbai (Rabale / Airoli Cluster)",
        "state": "Maharashtra",
        "wri_water_stress": WaterStressLevel.HIGH,
        "cgwb_aquifer_status": AquiferStatus.SEMI_CRITICAL,
        "baseline_grid_carbon_kg_mwh": 705.0,
        "grid_outage_risk_index_saidi_hours": 9.5,
        "tanker_dependency_index_pct": 28.0,
        "municipal_water_rationing_status": "MIDC industrial water quotas with 15% weekly cutbacks",
        "default_substation_capacity_mw": 120.0,
        "default_utility_headroom_ml_per_year": 450.0,
        "household_liters_per_capita_day": 135.0,
        "average_household_size": 4.1,
        "provenance": {
            "water_stress": "WRI Aqueduct 4.0 / WRI India 2026",
            "aquifer": "CGWB Maharashtra Dynamic Assessment",
            "grid_carbon": "CEA Western Regional Grid Database",
            "outage": "MERC Distribution Report"
        },
        "seasons": {
            "dry_summer": {
                "ambient_dry_bulb_c": 35.0,
                "ambient_wet_bulb_c": 27.0,
                "relative_humidity_pct": 62.0,
                "evaporative_water_penalty_factor": 1.20,
                "dry_cooling_pue_penalty_factor": 1.14,
                "hybrid_water_saving_pct": 65.0
            },
            "monsoon": {
                "ambient_dry_bulb_c": 28.0,
                "ambient_wet_bulb_c": 26.5,
                "relative_humidity_pct": 90.0,
                "evaporative_water_penalty_factor": 0.88,
                "dry_cooling_pue_penalty_factor": 0.94,
                "hybrid_water_saving_pct": 82.0
            },
            "annual_average": {
                "ambient_dry_bulb_c": 29.5,
                "ambient_wet_bulb_c": 24.5,
                "relative_humidity_pct": 72.0,
                "evaporative_water_penalty_factor": 1.0,
                "dry_cooling_pue_penalty_factor": 1.0,
                "hybrid_water_saving_pct": 72.0
            }
        }
    }
}


def get_regional_profile(region_key: str = "bengaluru") -> Dict[str, Any]:
    key = region_key.lower().strip()
    for k, profile in REGIONAL_PROFILES.items():
        if k in key:
            return profile
    return REGIONAL_PROFILES["bengaluru"]
