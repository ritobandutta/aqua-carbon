"""
Context Agent for AquaCarbon DC — Commons Edition (v2).
Provides grounded geospatial, climatic, hydrological, and grid provenance.
"""

from typing import Dict, Any
from engine.data_sources import get_regional_profile, REGIONAL_PROFILES


class ContextAgent:
    """
    Supplies validated contextual data with provenance citations.
    """

    def get_context(self, region_key: str = "bengaluru") -> Dict[str, Any]:
        return get_regional_profile(region_key)

    def list_available_regions(self) -> Dict[str, str]:
        return {k: v["region_name"] for k, v in REGIONAL_PROFILES.items()}
