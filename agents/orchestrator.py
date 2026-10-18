"""
Multi-Agent Orchestrator for AquaCarbon DC — Commons Edition (v2).
Coordinates Intake, Context, Deterministic Engine, Planner, Advisor,
Coverage Check, and Independent Verifier Agents.
Supports Gemini AI calls when GEMINI_API_KEY is available, with a deterministic
grounded fallback for offline / high-concurrency environments. Every investigator
answer, whichever source produced it, passes the verifier before it is returned.
"""

import os
import hashlib
import json
from typing import Dict, Any, Optional
from engine.models import (
    ScenarioInput, ProfileAssessment, CoverageDisparityResult,
    PlannerConstraints, PlannerOutput, GeneratedBriefs, VerificationReport
)
from engine.calculator import evaluate_scenario, run_constraint_planner
from engine.data_sources import VALUE_STATUS
from engine.coverage import run_coverage_check, apply_coverage_to_assessments
from .context_agent import ContextAgent
from .advisor_agent import AdvisorAgent
from .verifier_agent import VerifierAgent
from .planner_agent import PlannerAgent

# Confirm availability against current Gemini model IDs before deploying (docs/OPEN_QUESTIONS.md).
ENGINE_VERSION = "2.1.0"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class AgentOrchestrator:
    """
    Central coordinator following the ADK and Genkit agentic pattern.
    """

    def __init__(self):
        self.context_agent = ContextAgent()
        self.advisor_agent = AdvisorAgent()
        self.verifier_agent = VerifierAgent()
        self.planner_agent = PlannerAgent()

    def process_scenario(
        self,
        scenario: ScenarioInput
    ) -> Dict[str, Any]:
        """
        Executes end-to-end agentic workflow:
        1. Context retrieval
        2. Deterministic calculations (Facility & Community Ledgers, Burden Scores)
        3. Coverage check for under-represented populations
        4. Constraint planning (if constraints provided)
        5. Dual brief generation (Operator & Community)
        6. Independent verification and signing
        """
        # 1. Environmental Context
        region_context = self.context_agent.get_context(scenario.region)

        # 2. Deterministic Calculations
        assessments = evaluate_scenario(scenario)

        # 3. Coverage Check
        coverage_result = run_coverage_check(scenario.region)
        apply_coverage_to_assessments(assessments, coverage_result)

        # 4. Constraint Planning
        planner_result: Optional[PlannerOutput] = None
        if scenario.constraints:
            planner_result = self.planner_agent.plan_configurations(scenario, scenario.constraints)

        # 5. Brief Generation
        operator_brief = self.advisor_agent.generate_operator_brief(scenario, assessments)
        community_brief = self.advisor_agent.generate_community_brief(scenario, assessments)

        # 6. Independent Verification Trust Boundary
        verification_report = self.verifier_agent.verify_briefs(
            operator_brief=operator_brief,
            community_brief=community_brief,
            assessments=assessments
        )

        briefs = GeneratedBriefs(
            operator_brief_markdown=operator_brief,
            community_brief_markdown=community_brief,
            verification_report=verification_report
        )

        return {
            "run_id": self._run_id(scenario),
            "engine_version": ENGINE_VERSION,
            "scenario": scenario.model_dump(),
            "region_context": region_context,
            "assessments": {k: v.model_dump() for k, v in assessments.items()},
            "coverage_check": coverage_result.model_dump(),
            "planner_output": planner_result.model_dump() if planner_result else None,
            "briefs": briefs.model_dump(),
            "verification": verification_report.model_dump()
        }

    @staticmethod
    def _run_id(scenario: ScenarioInput) -> str:
        """Same inputs, engine version and data provenance give the same id."""
        payload = json.dumps(
            {"scenario": scenario.model_dump(mode="json"), "engine": ENGINE_VERSION, "status": VALUE_STATUS},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Returns Gemini's text, or None if no key is set or the call fails."""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[Notice] Live Gemini API call failed ({e}); using deterministic templates.")
        return None

    @staticmethod
    def _investigation_prompt(
        query: str,
        scenario: ScenarioInput,
        assessments: Dict[str, ProfileAssessment]
    ) -> str:
        lines = [
            "You are the AquaCarbon DC Investigator Agent powered by Gemini.",
            f"The user asked: '{query}'",
            "",
            "GROUND TRUTH DETERMINISTIC METRICS:",
            f"- IT Capacity: {scenario.it_capacity_mw:.1f} MW in {scenario.region.title()} ({scenario.season.value})",
        ]
        for key, a in assessments.items():
            fl, cl = a.facility_ledger, a.community_ledger
            lines.append(
                f"- {a.cooling_name}: PUE={fl.pue:.2f}, WUE={fl.wue:.2f} L/kWh, "
                f"Water={fl.direct_water_consumption_ml:.1f} ML/yr, "
                f"OpEx=INR {fl.annual_operating_cost_inr_crores:.2f} Cr, "
                f"Water Headroom Depletion={cl.water_headroom_share_pct.formatted_value}, "
                f"Substation Peak Load={cl.substation_peak_demand_share_pct.formatted_value}"
            )
        lines += [
            "",
            "TASK: Provide a professional, deep-dive thermodynamic, economic, and community water impact explanation.",
            "STRICT INSTRUCTION: Ground your answer strictly in the exact numbers above. "
            "Do not invent or compute any other statistic.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _deterministic_explanation(
        query: str,
        scenario: ScenarioInput,
        assessments: Dict[str, ProfileAssessment]
    ) -> str:
        evap = assessments.get("evaporative")
        dry = assessments.get("dry_cooling")
        hybrid = assessments.get("hybrid_adiabatic")
        q_lower = query.lower()
        asks_why = any(w in q_lower for w in ("why", "trade-off", "difference", "strain"))

        if asks_why and evap and dry:
            penalty = dry.facility_ledger.total_facility_energy_mwh - evap.facility_ledger.total_facility_energy_mwh
            text = (
                f"### Deterministic Analysis of Cooling Burden Shift\n\n"
                f"1. **Thermodynamics of Latent vs. Sensible Heat**:\n"
                f"   - **Evaporative Cooling** rejects heat through water evaporation (~2,260 kJ/kg latent heat of vaporization). "
                f"     This requires minimal electrical compressor work, achieving a lean PUE of **{evap.facility_ledger.pue:.2f}**, "
                f"     but directly consumes **{evap.facility_ledger.direct_water_consumption_ml:.1f} ML of water annually** "
                f"     ({evap.facility_ledger.daily_water_intake_m3:.0f} m³/day).\n"
                f"   - **Dry Cooling** rejects heat sensibly into the air using fans and mechanical chillers. "
                f"     Because air has a much lower heat capacity than water (1.005 kJ/kg·K vs 4.184 kJ/kg·K), chillers must work harder, "
                f"     pushing PUE to **{dry.facility_ledger.pue:.2f}** and increasing annual electrical consumption to "
                f"     **{dry.facility_ledger.total_facility_energy_mwh:,.0f} MWh** (a **{penalty:,.0f} MWh power penalty**).\n\n"
                f"2. **Community Impact Shift**:\n"
                f"   - Evaporative cooling consumes **{evap.community_ledger.water_headroom_share_pct.formatted_value}** of local municipal water headroom "
                f"     in an aquifer designated as *{evap.community_ledger.aquifer_stress_classification.formatted_value}*.\n"
                f"   - Dry cooling nearly eliminates water use (**{dry.facility_ledger.direct_water_consumption_ml:.1f} ML/yr**) but consumes "
                f"     **{dry.community_ledger.substation_peak_demand_share_pct.formatted_value}** of the local feeder substation "
                f"     capacity, which raises grid-reliability concerns at summer peak."
            )
            if hybrid:
                saved = evap.facility_ledger.direct_water_consumption_ml - hybrid.facility_ledger.direct_water_consumption_ml
                text += (
                    f"\n\n3. **The Hybrid Option**:\n"
                    f"   - Hybrid Adiabatic cooling saves **{saved:.1f} ML of water** relative to evaporative "
                    f"     with a PUE of **{hybrid.facility_ledger.pue:.2f}**."
                )
            return text

        lines = [f"Based on the engine calculations for {scenario.region} at {scenario.it_capacity_mw:.1f} MW capacity:"]
        for a in assessments.values():
            fl = a.facility_ledger
            lines.append(
                f"- {a.cooling_name}: PUE {fl.pue:.2f}, Water {fl.direct_water_consumption_ml:.1f} ML, "
                f"OpEx INR {fl.annual_operating_cost_inr_crores:.2f} Cr."
            )
        lines.append("All figures above come from the deterministic engine.")
        return "\n".join(lines)

    async def answer_investigation_query(
        self,
        query: str,
        scenario: ScenarioInput,
        assessments: Dict[str, ProfileAssessment]
    ) -> Dict[str, Any]:
        """
        Answers user deep-dive queries (e.g., 'Why does evaporative cooling save water but strain the grid?').
        Gemini drafts the answer when available. The verifier then checks every unit-tagged number
        against the engine. A draft that fails is blocked and replaced by the deterministic answer.
        """
        source = "deterministic_template"
        gemini_blocked = False

        draft = self._call_gemini(self._investigation_prompt(query, scenario, assessments))
        explanation = None
        if draft:
            if self.verifier_agent.verify_text(draft, assessments).status == "PASSED":
                explanation = draft
                source = "gemini"
            else:
                gemini_blocked = True

        if explanation is None:
            explanation = self._deterministic_explanation(query, scenario, assessments)

        report = self.verifier_agent.verify_text(explanation, assessments)

        return {
            "query": query,
            "explanation_markdown": explanation,
            "source": source,
            "gemini_draft_blocked": gemini_blocked,
            "verification_status": report.status,
            "verification_checks": report.total_checks,
            "verification_signature": report.signature
        }
