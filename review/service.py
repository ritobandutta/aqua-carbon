"""
Permit-review pipeline. Uses all three protocols for distinct jobs:

  ADK   runs the agents (claim extractor, reviewer) and the A2A client.
  MCP   exposes the deterministic engine as typed tools; the reviewer agent calls them.
  A2A   carries the finished review to an independent verifier that recomputes the numbers itself.

Rule kept from the rest of the project: the model never produces a number. It extracts claims (which the
verifier proves appear in the applicant's text) and calls tools. All figures come from the engine.

Modes
  structured  claims are supplied; MCP tools are called directly, no model involved.
  agentic     only applicant text is supplied; a Gemini-backed ADK agent extracts the claims, then an ADK
              agent with the MCP toolset checks each one.

Verification is remote (A2A) when A2A_VERIFIER_URL is set and FAILS CLOSED if it cannot be reached; otherwise it runs in-process
and the response says so.
"""

import json
import os
import sys
import warnings
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from engine.claims import CLAIMABLE_METRICS
from engine.data_sources import resolve_region_key
from engine.models import VerificationReport
from .models import ClaimInput, ReviewRequest, ReviewResponse, VerifyReviewRequest
from .rendering import render_review
from .verification import verify_review

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
NOTICE = ("Modelled values use illustrative, unverified inputs. Results are prompts for questions, not findings. "
          "Any real decision needs qualified engineering review.")


class ReviewError(Exception):
    """A problem the caller can fix (bad input, no model available). The API maps it to HTTP 422."""


class ExtractedClaims(BaseModel):
    claims: List[ClaimInput]


EXTRACT_INSTRUCTION = f"""You extract numeric commitments from a data-center permit application.
Return only claims the applicant states explicitly, with the figure written in the metric's own unit.
cooling_type is one of: evaporative, dry_cooling, hybrid_adiabatic.
metric and unit: pue (ratio), wue_l_per_kwh (L/kWh), direct_water_ml (ML per year), facility_energy_mwh (MWh per year),
scope2_carbon_tonnes (tCO2e per year), operating_cost_inr_crores (INR crore per year).
Rules: copy the number exactly as written. Do NOT convert units, estimate, infer or average. If a figure is not stated in the
metric's own unit, leave it out. If a claim names no cooling system and only one is described, use that one; otherwise leave it out.
If there are no such claims return an empty list."""


def _scenario_args(req: ReviewRequest, c: ClaimInput) -> Dict[str, Any]:
    return {"region": req.scenario.region, "it_capacity_mw": req.scenario.it_capacity_mw,
            "cooling_type": c.cooling_type.value, "metric": c.metric, "claimed_value": c.claimed_value,
            "season": req.scenario.season.value}


def _parse_tool_result(response: Any) -> Optional[dict]:
    """Pulls the verdict row out of an MCP tool result in either shape ADK/MCP may produce."""
    if not isinstance(response, dict):
        return None
    for key in ("structuredContent", "structured_content"):
        if isinstance(response.get(key), dict) and "verdict" in response[key]:
            return response[key]
    for item in response.get("content", []) or []:
        text = item.get("text") if isinstance(item, dict) else None
        if text:
            try:
                row = json.loads(text)
                if isinstance(row, dict) and "verdict" in row:
                    return row
            except json.JSONDecodeError:
                pass
    return None


class ReviewService:
    def __init__(self, model: Any = None):
        self.model = model  # a model id string or an ADK BaseLlm; None means "use Gemini if a key exists"

    # ---- configuration -------------------------------------------------------------------------------
    @property
    def mcp_url(self) -> str:
        return os.getenv("MCP_URL", "").rstrip("/")

    @property
    def a2a_url(self) -> str:
        return os.getenv("A2A_VERIFIER_URL", "").rstrip("/")

    def _have_llm(self) -> bool:
        return self.model is not None or bool(os.getenv("GEMINI_API_KEY")) or \
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes")

    def _model(self) -> Any:
        return self.model if self.model is not None else GEMINI_MODEL

    # ---- ADK helpers -----------------------------------------------------------------------------------
    @staticmethod
    async def _run(agent: Any, user_text: str) -> List[Any]:
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        runner = InMemoryRunner(agent=agent, app_name=agent.name)
        session = await runner.session_service.create_session(app_name=agent.name, user_id="review")
        msg = types.Content(role="user", parts=[types.Part(text=user_text)])
        return [ev async for ev in runner.run_async(user_id="review", session_id=session.id, new_message=msg)]

    @staticmethod
    def _final_text(events: List[Any]) -> str:
        text = ""
        for ev in events:
            for p in (ev.content.parts if ev.content else []):
                if getattr(p, "text", None):
                    text = p.text
        return text

    # ---- step 1 (agentic only): extract claims ---------------------------------------------------------
    async def _extract_claims(self, req: ReviewRequest) -> List[ClaimInput]:
        from google.adk.agents import LlmAgent
        agent = LlmAgent(name="claim_extractor", model=self._model(), instruction=EXTRACT_INSTRUCTION,
                         output_schema=ExtractedClaims)
        events = await self._run(agent, req.applicant_text)
        try:
            return ExtractedClaims.model_validate_json(self._final_text(events)).claims
        except Exception as e:
            raise ReviewError(f"The model did not return usable claims ({type(e).__name__}). Supply structured claims instead.") from e

    # ---- step 2: check claims through MCP --------------------------------------------------------------
    async def _check_structured(self, req: ReviewRequest, claims: List[ClaimInput]) -> List[dict]:
        from mcp.client.client import Client
        if self.mcp_url:
            client = Client(f"{self.mcp_url}/mcp")
        else:
            from mcp_server.server import mcp
            client = Client(mcp)
        rows = []
        async with client as c:
            for claim in claims:
                r = await c.call_tool("check_applicant_claim", _scenario_args(req, claim))
                if r.is_error:
                    raise ReviewError(r.content[0].text if r.content else "MCP tool error")
                row = _parse_tool_result({"content": [{"text": r.content[0].text}]})
                if row is None:
                    raise ReviewError("MCP tool returned an unreadable result")
                rows.append(row)
        return rows

    async def _check_agentic(self, req: ReviewRequest, claims: List[ClaimInput]) -> List[dict]:
        from google.adk.agents import LlmAgent
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams, StreamableHTTPConnectionParams
        from mcp import StdioServerParameters
        if self.mcp_url:
            params = StreamableHTTPConnectionParams(url=f"{self.mcp_url}/mcp")
        else:  # no server configured: launch the MCP server as a subprocess over stdio
            params = StdioConnectionParams(server_params=StdioServerParameters(
                command=sys.executable, args=["-m", "mcp_server.server", "--stdio"], cwd=ROOT), timeout=30.0)
        toolset = McpToolset(connection_params=params, tool_filter=["check_applicant_claim"])
        calls = [_scenario_args(req, c) for c in claims]
        agent = LlmAgent(
            name="claim_reviewer", model=self._model(), tools=[toolset],
            instruction=("For EACH item in the JSON list the user sends, call check_applicant_claim exactly once with exactly "
                         "those arguments. Never change a value. Do not write any numbers yourself. When every call is "
                         "done, reply with the single word: done."))
        try:
            events = await self._run(agent, json.dumps(calls))
        finally:
            await toolset.close()
        rows, seen = [], set()
        for ev in events:
            for p in (ev.content.parts if ev.content else []):
                fr = getattr(p, "function_response", None)
                if fr and fr.name == "check_applicant_claim":
                    row = _parse_tool_result(fr.response)
                    if row:
                        key = (row["cooling_type"], row["metric"], row["claimed_value"])
                        if key not in seen:
                            seen.add(key)
                            rows.append(row)
        return rows

    # ---- step 3: independent verification (A2A) ---------------------------------------------------------
    async def _verify(self, vreq: VerifyReviewRequest) -> tuple[VerificationReport, str]:
        if not self.a2a_url:
            return verify_review(vreq), "in_process"
        from agents.verifier_client import _unreachable
        try:
            from google.adk.a2a.agent._remote_a2a_agent import RemoteA2aAgent
            remote = RemoteA2aAgent(name="remote_review_verifier",
                                    agent_card=f"{self.a2a_url}/.well-known/agent-card.json", timeout=15.0)
            try:
                events = await self._run(remote, vreq.model_dump_json())
            finally:
                await remote.cleanup()
            return VerificationReport.model_validate_json(self._final_text(events)), "a2a_remote"
        except Exception as e:
            return _unreachable(type(e).__name__), "a2a_remote"

    # ---- entry point -------------------------------------------------------------------------------------
    async def review(self, req: ReviewRequest) -> ReviewResponse:
        resolve_region_key(req.scenario.region)  # unknown region -> UnknownRegionError -> HTTP 404
        for c in req.claims:
            if c.metric not in CLAIMABLE_METRICS:
                raise ReviewError(f"Unknown metric '{c.metric}'. Claimable metrics: {', '.join(sorted(CLAIMABLE_METRICS))}.")

        if req.claims:
            mode, claims, source = "structured", list(req.claims), "structured"
        elif req.applicant_text.strip():
            if not self._have_llm():
                raise ReviewError("Reading claims from free text needs a model (set GEMINI_API_KEY). "
                                  "Or supply structured claims in the 'claims' field.")
            mode, claims, source = "agentic", await self._extract_claims(req), "text"
        else:
            raise ReviewError("Provide either structured 'claims' or 'applicant_text'.")

        prov = {"mcp": self.mcp_url or ("stdio_subprocess" if mode == "agentic" else "in_memory"),
                "a2a_verifier": self.a2a_url or "in_process"}
        if not claims:
            return ReviewResponse(status="no_claims", mode=mode, review_source="none", provenance=prov,
                                  notice="No figure stated in the metric's own unit was found. Nothing to check. " + NOTICE)

        rows = await (self._check_agentic(req, claims) if mode == "agentic" else self._check_structured(req, claims))
        scenario_line = f"{req.scenario.region.title()}, {req.scenario.it_capacity_mw:g} MW IT load, {req.scenario.season.value.replace('_', ' ')}"
        review_text = render_review(scenario_line, rows) if rows else ""

        report, vmode = await self._verify(VerifyReviewRequest(
            scenario=req.scenario, claims_source=source, applicant_text=req.applicant_text, claims=claims,
            reported_verdicts=rows, review_text=review_text))
        prov["verification"] = vmode
        ok = report.status == "PASSED"
        return ReviewResponse(
            status="verified" if ok else "blocked_unverified", mode=mode,
            review_source="template" if ok else "none", claims=claims,
            verdicts=rows if ok else [], review_markdown=review_text if ok else "",
            verification=report, provenance=prov,
            notice=NOTICE if ok else "Blocked: the independent verifier did not confirm this review, so it is withheld. " + NOTICE)
