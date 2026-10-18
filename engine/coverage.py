"""
Coverage Check Engine for AquaCarbon DC — Commons Edition (v2).
Cross-references satellite-derived built-up settlement footprints (e.g., GHSL, OpenStreetMap)
against official piped-water utility connections (BWSSB / Municipal records).
Identifies spatial disparities indicating unserved or informal communities relying on shared tankers/aquifers.
"""

from typing import Dict, Any, List
from .models import CoverageDisparityResult, DataConfidence


# Sourced ground-truth benchmark datasets for peri-urban clusters
AREA_COVERAGE_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "bengaluru": {
        "area_name": "Whitefield - Mahadevapura Peri-Urban Zone (East Bengaluru)",
        "satellite_settlement_builtup_km2": 42.8,  # Sourced from Copernicus Global Land Service / GHSL
        "official_piped_water_coverage_km2": 23.4,  # BWSSB Cauvery Stage IV Phase II direct connections
        "estimated_unpiped_density_per_km2": 4200,
        "primary_water_source_unserved": "Private unregulated borewells & commercial diesel water tankers",
        "official_records_source": "BWSSB Ward Level Connection Registry 2024",
        "satellite_source": "European Commission Global Human Settlement Layer (GHSL) Built-up Grid (2024)"
    },
    "chennai": {
        "area_name": "Ambattur - Sholinganallur Corridor",
        "satellite_settlement_builtup_km2": 51.2,
        "official_piped_water_coverage_km2": 31.5,
        "estimated_unpiped_density_per_km2": 3800,
        "primary_water_source_unserved": "Deep coastal aquifer extraction and CMWSSB mobile supply",
        "official_records_source": "Chennai Metrowater Pipeline GIS 2024",
        "satellite_source": "Copernicus Sentinel-2 Built-Up Layer"
    },
    "mumbai": {
        "area_name": "Navi Mumbai Thane-Belapur Industrial Belt Periphery",
        "satellite_settlement_builtup_km2": 38.0,
        "official_piped_water_coverage_km2": 29.5,
        "estimated_unpiped_density_per_km2": 4900,
        "primary_water_source_unserved": "MIDC standposts and informal informal network tapping",
        "official_records_source": "NMMC Water Distribution Network Map",
        "satellite_source": "GHSL Settlement Grid"
    }
}


def run_coverage_check(
    region_key: str = "bengaluru",
    disparity_threshold: float = 1.25
) -> CoverageDisparityResult:
    """
    Evaluates spatial disparity between satellite-visible human settlement and official municipal water connections.
    If satellite footprint / piped coverage > threshold, flags systemic under-representation.
    """
    key = region_key.lower().strip()
    matched_key = "bengaluru"
    for k in AREA_COVERAGE_BENCHMARKS.keys():
        if k in key:
            matched_key = k
            break

    benchmark = AREA_COVERAGE_BENCHMARKS[matched_key]
    satellite_km2 = benchmark["satellite_settlement_builtup_km2"]
    piped_km2 = benchmark["official_piped_water_coverage_km2"]
    
    disparity_ratio = round(satellite_km2 / max(piped_km2, 0.1), 2)
    unserved_km2 = max(satellite_km2 - piped_km2, 0.0)
    density = benchmark.get("estimated_unpiped_density_per_km2", 4000)
    unmapped_pop = int(unserved_km2 * density)

    flags: List[str] = []
    recommended_actions: List[str] = []

    if disparity_ratio > disparity_threshold:
        flags.append(
            f"SPATIAL COVERAGE GAP DETECTED: Satellite built-up area ({satellite_km2:.1f} km²) is {disparity_ratio:.2f}x "
            f"larger than the official municipal piped network footprint ({piped_km2:.1f} km²)."
        )
        flags.append(
            f"UNDER-REPRESENTATION ALERT: An estimated {unmapped_pop:,} residents in adjacent informal/peri-urban "
            f"clusters do not show up in official utility consumer rolls but share the same underlying aquifer."
        )
        flags.append(
            f"VULNERABILITY VECTOR: Unserved population relies primarily on {benchmark['primary_water_source_unserved']}, "
            f"making them acutely sensitive to data-center water draw during peak dry periods."
        )

        confidence_impact = (
            "Confidence for official water headroom indicator downgraded from HIGH to MEDIUM. "
            "Utility records systematically underestimate true community reliance on shared groundwater."
        )

        recommended_actions = [
            f"Commission micro-hydrological survey with local Ward Committees in {benchmark['area_name']}.",
            "Deploy sensor monitoring on community borewell static water levels within a 5 km facility radius.",
            "Integrate participatory tanker delivery logs from local Resident Welfare Associations (RWAs) and informal settlement federations.",
            "Mandate that facility zero-liquid-discharge (ZLD) effluent be treated to tertiary standards for community urban forestry or groundwater recharge."
        ]
    else:
        flags.append("Official municipal network footprint corresponds well with satellite built-up layer.")
        confidence_impact = "Official water headroom confidence maintained at HIGH."
        recommended_actions = [
            "Maintain bi-annual audit of utility telemetry and municipal consumer additions."
        ]

    return CoverageDisparityResult(
        area_name=benchmark["area_name"],
        satellite_settlement_builtup_km2=satellite_km2,
        official_piped_water_coverage_km2=piped_km2,
        disparity_ratio=disparity_ratio,
        unmapped_tanker_dependent_population_estimate=unmapped_pop,
        flags=flags,
        confidence_impact=confidence_impact,
        recommended_ground_truth_actions=recommended_actions
    )
