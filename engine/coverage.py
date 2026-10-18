"""
Coverage Check Engine for AquaCarbon DC — Commons Edition (v2).
Cross-references satellite-derived built-up settlement footprints (e.g., GHSL, OpenStreetMap)
against official piped-water utility connections (BWSSB / Municipal records).
Identifies spatial disparities indicating unserved or informal communities relying on shared tankers/aquifers.
"""

from typing import Dict, Any, List
from .models import CoverageDisparityResult, DataConfidence
from .data_sources import resolve_region_key


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
    matched_key = resolve_region_key(region_key)

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


COVERAGE_AFFECTED = ("water_headroom_share_pct", "household_water_equivalent_count")


def apply_coverage_to_assessments(assessments, coverage: CoverageDisparityResult, threshold: float = 1.25) -> bool:
    """If the coverage check found a gap, lower the confidence of the indicators that rely on official
    connection records by one level (floor LOW) and say why in the indicator's explanation.
    Mutates the ledgers in place. Returns True if anything was downgraded. Area-level only."""
    if coverage.disparity_ratio <= threshold:
        return False
    order = [DataConfidence.LOW, DataConfidence.MEDIUM, DataConfidence.HIGH]
    changed = False
    for a in assessments.values():
        for field in COVERAGE_AFFECTED:
            ind = getattr(a.community_ledger, field)
            if ind.confidence in (DataConfidence.HIGH, DataConfidence.MEDIUM):
                ind.confidence = order[order.index(ind.confidence) - 1]
                changed = True
            if "Coverage check" not in ind.explanation:
                ind.explanation += (
                    f" Coverage check: satellite built-up area is {coverage.disparity_ratio:.2f}x the official piped "
                    f"footprint, so official records likely under-represent people who rely on the shared system."
                )
    return changed
