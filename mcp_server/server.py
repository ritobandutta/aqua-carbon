"""
AquaCarbon engine as an MCP server. Typed tools over the deterministic engine, so an agent (or any MCP
client) can ask for numbers without ever producing them. Nothing here calls an LLM.

Run:  python -m mcp_server.server            (streamable HTTP on 127.0.0.1:8200/mcp)
      python -m mcp_server.server --stdio    (stdio transport)
"""

import os
import sys
from typing import Dict, List
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from engine.calculator import evaluate_scenario, evaluate_with_bands
from engine.claims import CLAIMABLE_METRICS, ClaimScenario, check_claim
from engine.data_sources import REGIONAL_PROFILES, UnknownRegionError, resolve_region_key
from engine.models import CoolingType, ScenarioInput, Season, WorkloadType

mcp = MCPServer(
    "aquacarbon-engine",
    instructions=(
        "Deterministic calculation engine for data-center cooling. Every number comes from these tools. "
        "All facility inputs are illustrative and regional values are unverified unless a result says otherwise."
    ),
)

def _guarded(fn):
    """Turn expected input errors (bad region, unknown enum or metric) into ToolError so the calling agent
    sees a readable message instead of a logged server crash."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except UnknownRegionError as e:
            raise ToolError(str(e)) from e
        except (ValueError, KeyError) as e:
            raise ToolError(
                f"Invalid input: {e}. cooling_type is one of {[c.value for c in CoolingType]}, "
                f"season one of {[x.value for x in Season]}, metric one of {sorted(CLAIMABLE_METRICS)}."
            ) from e
    return wrapper


_SOURCES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sources.yaml")


@mcp.tool()
def list_regions() -> List[Dict[str, str]]:
    """List supported regions and their ids. Use an id exactly as returned."""
    return [{"id": k, "name": v["region_name"], "state": v["state"]} for k, v in REGIONAL_PROFILES.items()]


@mcp.tool()
@_guarded
def modelled_range(region: str, it_capacity_mw: float, cooling_type: str, metric: str, season: str = "annual_average") -> dict:
    """Modelled low / central / high for one metric of one cooling profile.
    cooling_type: evaporative | dry_cooling | hybrid_adiabatic.
    metric: pue | wue_l_per_kwh | direct_water_ml | facility_energy_mwh | scope2_carbon_tonnes | operating_cost_inr_crores.
    Ranges are sensitivity ranges around unverified inputs, not confidence intervals."""
    sc = ScenarioInput(region=region, it_capacity_mw=it_capacity_mw, season=Season(season), selected_profiles=[CoolingType(cooling_type)])
    band = evaluate_with_bands(sc)[cooling_type][metric]
    label, unit = CLAIMABLE_METRICS[metric]
    return {"region": resolve_region_key(region), "cooling_type": cooling_type, "metric": metric, "label": label, "unit": unit, **band}


@mcp.tool()
@_guarded
def check_applicant_claim(region: str, it_capacity_mw: float, cooling_type: str, metric: str, claimed_value: float,
                          season: str = "annual_average") -> dict:
    """Compare an applicant's stated figure with the modelled range. Verdict is within_modelled_range,
    below_modelled_range (more favourable than the model's best case, ask for evidence) or above_modelled_range.
    A verdict is a prompt for questions, never a finding of fault."""
    sc = ClaimScenario(region=region, it_capacity_mw=it_capacity_mw, season=Season(season))
    return check_claim(sc, CoolingType(cooling_type), metric, claimed_value).model_dump(mode="json")


@mcp.tool()
@_guarded
def compare_profiles(region: str, it_capacity_mw: float, season: str = "annual_average") -> dict:
    """Facility figures for all three profiles side by side (central case), plus the water, power and carbon burden
    scores. There is deliberately no combined score."""
    a = evaluate_scenario(ScenarioInput(region=region, it_capacity_mw=it_capacity_mw, season=Season(season)))
    out = {}
    for key, asm in a.items():
        f = asm.facility_ledger
        out[key] = {
            "pue": f.pue, "wue_l_per_kwh": f.wue, "direct_water_ml": f.direct_water_consumption_ml,
            "facility_energy_mwh": f.total_facility_energy_mwh, "scope2_carbon_tonnes": f.scope2_carbon_tonnes,
            "operating_cost_inr_crores": f.annual_operating_cost_inr_crores,
            "burden": asm.burden_scores.model_dump(),
        }
    return {"region": resolve_region_key(region), "it_capacity_mw": it_capacity_mw, "season": season, "profiles": out}


@mcp.resource("aquacarbon://sources")
def sources() -> str:
    """The provenance registry (data/sources.yaml): what each input is based on and whether it is verified."""
    with open(_SOURCES_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def build_http_app():
    """Streamable-HTTP app with DNS-rebinding protection ON. The SDK only trusts localhost Host headers by default,
    so a containerised deployment must allow-list the name other services use (for example MCP_ALLOWED_HOSTS=mcp:*).
    Protection is never switched off."""
    from mcp.server.transport_security import TransportSecuritySettings
    extra = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    origins = [o.strip() for o in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    return mcp.streamable_http_app(transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *extra],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*", *origins],
    ))


def main() -> None:
    if "--stdio" in sys.argv:
        mcp.run("stdio")
    else:
        import uvicorn
        uvicorn.run(build_http_app(), host=os.getenv("MCP_HOST", "127.0.0.1"), port=int(os.getenv("MCP_PORT", "8200")))


if __name__ == "__main__":
    main()
