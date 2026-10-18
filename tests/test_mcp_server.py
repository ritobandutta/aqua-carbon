"""MCP server tools, exercised through a real MCP client (in-memory transport)."""

import asyncio
import json
import pytest

pytest.importorskip("mcp")

from mcp.client.client import Client
from mcp_server.server import mcp


def call(name, args):
    async def go():
        async with Client(mcp) as c:
            return await c.call_tool(name, args)
    return asyncio.run(go())


def test_tools_are_listed():
    async def go():
        async with Client(mcp) as c:
            return [t.name for t in (await c.list_tools()).tools]
    assert {"list_regions", "modelled_range", "check_applicant_claim", "compare_profiles"} <= set(asyncio.run(go()))


def test_check_applicant_claim_returns_the_engine_verdict():
    r = call("check_applicant_claim", {"region": "bengaluru", "it_capacity_mw": 15.0, "cooling_type": "hybrid_adiabatic",
                                       "metric": "direct_water_ml", "claimed_value": 40.0})
    assert not r.is_error
    row = json.loads(r.content[0].text)
    assert row["verdict"] == "below_modelled_range" and row["inputs_status"] == "illustrative_unverified"


def test_bad_inputs_are_readable_tool_errors_not_crashes():
    for args in ({"region": "Delhi", "cooling_type": "evaporative", "metric": "pue"},
                 {"region": "bengaluru", "cooling_type": "steam", "metric": "pue"},
                 {"region": "bengaluru", "cooling_type": "evaporative", "metric": "vibes"}):
        r = call("check_applicant_claim", {"it_capacity_mw": 15.0, "claimed_value": 1.1, **args})
        assert r.is_error and "Error executing tool" in r.content[0].text


def test_compare_profiles_has_no_combined_score():
    r = call("compare_profiles", {"region": "mumbai", "it_capacity_mw": 20.0})
    data = json.loads(r.content[0].text)
    assert set(data["profiles"]) == {"evaporative", "dry_cooling", "hybrid_adiabatic"}
    for prof in data["profiles"].values():
        assert set(prof["burden"]) == {"water_system_burden", "power_system_burden", "carbon_atmosphere_burden"}


def test_sources_resource_is_readable():
    async def go():
        async with Client(mcp) as c:
            return (await c.read_resource("aquacarbon://sources")).contents[0].text
    assert "Provenance registry" in asyncio.run(go())


def _init_status(app, host):
    from starlette.testclient import TestClient
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
    with TestClient(app, base_url=f"http://{host}") as c:
        return c.post("/mcp", json=body, headers={"accept": "application/json, text/event-stream"}).status_code


def test_dns_rebinding_protection_stays_on_and_allow_list_is_configurable(monkeypatch):
    from mcp_server.server import build_http_app
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert _init_status(build_http_app(), "mcp:8200") == 421            # unknown service name is refused
    assert _init_status(build_http_app(), "evil.example:8200") == 421
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp:*")
    assert _init_status(build_http_app(), "mcp:8200") != 421            # allow-listed name works
    assert _init_status(build_http_app(), "evil.example:8200") == 421   # everything else is still refused
