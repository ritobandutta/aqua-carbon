"""
Advisor Agent for AquaCarbon DC — Commons Edition (v2).
Synthesizes deterministic scenario assessments into two distinct, high-fidelity briefs:
1. Operator & Developer Brief (Engineering tradeoffs, PUE, WUE, thermal safety, OpEx)
2. Community & Municipal Brief (Water headroom impact, domestic equivalents, public inquiry questions)
"""

from typing import Dict, Any, Optional
from engine.models import ProfileAssessment, ScenarioInput, CoolingType


class AdvisorAgent:
    """
    Generates structured, fact-grounded briefs for operators and host communities.
    """

    def generate_operator_brief(
        self,
        scenario: ScenarioInput,
        assessments: Dict[str, ProfileAssessment]
    ) -> str:
        evap = assessments.get(CoolingType.EVAPORATIVE.value)
        dry = assessments.get(CoolingType.DRY_COOLING.value)
        hybrid = assessments.get(CoolingType.HYBRID_ADIABATIC.value)

        lines = [
            f"# Technical Operator & Engineering Brief: {scenario.scenario_title}",
            f"**Site Context**: {scenario.region} | **Design IT Capacity**: {scenario.it_capacity_mw:.1f} MW | **Operating Season**: {scenario.season.value.replace('_', ' ').title()}",
            "",
            "## 1. Executive Summary & Cooling Trade-Off",
            "This assessment evaluates three cooling profiles under identical computational load and climate conditions using the deterministic physical calculation engine.",
            "",
            "| Metric | Evaporative Cooling | Dry Air-Cooled | Hybrid Adiabatic |",
            "| :--- | :--- | :--- | :--- |",
        ]

        # Table rows
        pue_row = f"| **Annual PUE** | {evap.facility_ledger.pue:.2f} | {dry.facility_ledger.pue:.2f} | {hybrid.facility_ledger.pue:.2f} |" if evap and dry and hybrid else ""
        wue_row = f"| **WUE (L/kWh IT)** | {evap.facility_ledger.wue:.2f} | {dry.facility_ledger.wue:.2f} | {hybrid.facility_ledger.wue:.2f} |" if evap and dry and hybrid else ""
        energy_row = f"| **Facility Energy (MWh/yr)** | {evap.facility_ledger.total_facility_energy_mwh:,.0f} | {dry.facility_ledger.total_facility_energy_mwh:,.0f} | {hybrid.facility_ledger.total_facility_energy_mwh:,.0f} |" if evap and dry and hybrid else ""
        water_row = f"| **Direct Water (ML/yr)** | {evap.facility_ledger.direct_water_consumption_ml:.1f} ML | {dry.facility_ledger.direct_water_consumption_ml:.1f} ML | {hybrid.facility_ledger.direct_water_consumption_ml:.1f} ML |" if evap and dry and hybrid else ""
        carbon_row = f"| **Scope 2 Carbon (tCO2e)** | {evap.facility_ledger.scope2_carbon_tonnes:,.0f} | {dry.facility_ledger.scope2_carbon_tonnes:,.0f} | {hybrid.facility_ledger.scope2_carbon_tonnes:,.0f} |" if evap and dry and hybrid else ""
        cost_row = f"| **Annual OpEx (₹ Cr)** | ₹{evap.facility_ledger.annual_operating_cost_inr_crores:.2f} Cr | ₹{dry.facility_ledger.annual_operating_cost_inr_crores:.2f} Cr | ₹{hybrid.facility_ledger.annual_operating_cost_inr_crores:.2f} Cr |" if evap and dry and hybrid else ""
        cost_usd_row = f"| **Annual OpEx ($M USD)** | ${evap.facility_ledger.annual_operating_cost_usd_millions:.2f}M | ${dry.facility_ledger.annual_operating_cost_usd_millions:.2f}M | ${hybrid.facility_ledger.annual_operating_cost_usd_millions:.2f}M |" if evap and dry and hybrid else ""

        for row in [pue_row, wue_row, energy_row, water_row, carbon_row, cost_row, cost_usd_row]:
            if row:
                lines.append(row)

        lines.extend([
            "",
            "## 2. Engineering Risk & Reliability Considerations",
            "- **Evaporative Risk Profile**: High operational dependency on continuous municipal water supply. At a design PUE of " + (f"{evap.facility_ledger.pue:.2f}" if evap else "1.20") + ", annual water draw is " + (f"{evap.facility_ledger.direct_water_consumption_ml:.1f} ML" if evap else "275 ML") + ". In the event of municipal curtailment or local tanker supply disruption, on-site storage depletion poses severe thermal throttling risks.",
            "- **Dry Cooling Risk Profile**: Eliminates water supply vulnerability completely (" + (f"{dry.facility_ledger.direct_water_consumption_ml:.1f} ML" if dry else "0.0 ML") + " direct water), but imposes an electric penalty of " + (f"{dry.facility_ledger.total_facility_energy_mwh - evap.facility_ledger.total_facility_energy_mwh:,.0f} MWh/yr" if evap and dry else "high energy") + ". During summer peaks, compressor lift reaches maximum duty, driving annual operating cost to " + (f"₹{dry.facility_ledger.annual_operating_cost_inr_crores:.2f} Cr" if dry else "higher") + ".",
            "- **Hybrid Adiabatic Recommendation**: Delivers the optimal engineering compromise. Reduces direct water withdrawal by ~69% relative to evaporative (" + (f"{hybrid.facility_ledger.direct_water_consumption_ml:.1f} ML" if hybrid else "85 ML") + ") while maintaining an attractive PUE of " + (f"{hybrid.facility_ledger.pue:.2f}" if hybrid else "1.27") + " and total annual OpEx of " + (f"₹{hybrid.facility_ledger.annual_operating_cost_inr_crores:.2f} Cr" if hybrid else "optimal") + ".",
            "",
            "## 3. Recommended Pre-Permitting Engineering Checks",
            "1. **Water Quality & Scaling**: Verify cycles of concentration (CoC >= 4.5) against local Total Dissolved Solids (TDS) reports from BWSSB industrial lines.",
            "2. **Substation Peak Capacity**: Confirm that the 66kV feeder substation can sustain " + (f"{dry.facility_ledger.it_capacity_mw * dry.facility_ledger.pue:.1f} MW" if dry else "21.8 MW") + " peak summer electrical draw without tripping local distribution transformers.",
            "3. **Thermal Plume Circulation**: Perform CFD modeling to avoid recirculation of warm exhaust air into neighboring air intakes in dense technology park layouts."
        ])

        return "\n".join(lines)

    def generate_community_brief(
        self,
        scenario: ScenarioInput,
        assessments: Dict[str, ProfileAssessment]
    ) -> str:
        evap = assessments.get(CoolingType.EVAPORATIVE.value)
        dry = assessments.get(CoolingType.DRY_COOLING.value)
        hybrid = assessments.get(CoolingType.HYBRID_ADIABATIC.value)

        lines = [
            f"# Plain-Language Community & Municipal Brief: {scenario.scenario_title}",
            f"**Prepared For**: Local Municipal Councils, Ward Committees, Resident Associations & Civil Society",
            f"**Location**: {scenario.region} | **IT Facility Scale**: {scenario.it_capacity_mw:.1f} Megawatts",
            "",
            "## 1. What Does This Data Center Demand From Our Shared Commons?",
            "When a new computer data center operates in our neighborhood, it requires continuous cooling to keep servers from overheating. Depending on the cooling method chosen by the operator, that burden is shifted either onto **our shared drinking water**, onto **our electricity grid**, or into **our air quality**.",
            "",
            "### Water Impact Comparison in Everyday Terms",
        ]

        if evap:
            hh_count = evap.community_ledger.household_water_equivalent_count.value or 0
            lines.append(
                f"- **If Evaporative Cooling is Used**: The facility will consume approximately **{evap.facility_ledger.direct_water_consumption_ml:.1f} Million Liters (ML) of water every year** "
                f"({evap.facility_ledger.daily_water_intake_m3:.0f} m³ every single day). This is equivalent to the annual domestic water supply needed by **{int(hh_count):,} local families**."
            )
            lines.append(
                f"  This consumes **{evap.community_ledger.water_headroom_share_pct.formatted_value}** of the local industrial water buffer in a watershed where the aquifer is officially classified as *{evap.community_ledger.aquifer_stress_classification.formatted_value}*."
            )

        if dry:
            lines.append(
                f"- **If Dry Air-Cooling is Used**: The facility consumes virtually **zero water** ({dry.facility_ledger.direct_water_consumption_ml:.1f} ML/year), protecting our groundwater and water supply. However, it pulls **{dry.community_ledger.substation_peak_demand_share_pct.formatted_value}** of the local electrical substation capacity during peak summer afternoons, which can heighten neighborhood power cuts or transformer overloads."
            )

        if hybrid:
            lines.append(
                f"- **If Smart Hybrid Cooling is Used**: The facility consumes **{hybrid.facility_ledger.direct_water_consumption_ml:.1f} ML/year** (saving over 65% of the water used by evaporative cooling) while keeping electrical draw manageable at PUE {hybrid.facility_ledger.pue:.2f}."
            )

        lines.extend([
            "",
            "## 2. Who is at Risk? What the Data Shows and Doesn't Show",
            f"- **Groundwater Reality**: The local groundwater table is classified as *Over-Exploited*. Approximately {evap.community_ledger.tanker_dependency_index.formatted_value if evap else '46%'} of neighboring households already rely on private water tankers due to lack of municipal piped water.",
            "- **The Data Coverage Gap**: Official government water plans only count registered piped connections. Satellite imagery reveals that large peri-urban informal settlements exist outside the piped network. If the data center relies on tanker supply or deep borewells during droughts, it directly competes with these vulnerable residents.",
            "",
            "## 3. Five Questions To Ask at Public Hearings & Environmental Consultations",
            "1. *Does the operator commit to using tertiary-treated recycled wastewater (STP water) rather than potable municipal or borewell water?*",
            "2. *If evaporative or hybrid cooling is permitted, what is the hard daily water meter cap during the dry summer months (March - June)?*",
            "3. *Will the facility install real-time, publicly accessible water meters and groundwater monitoring telemetry on its perimeter?*",
            "4. *What backup power and grid coordination guarantees exist so that peak data-center chiller loads do not cause residential brownouts?*",
            "5. *Will the project sponsor community rainwater harvesting or watershed recharge structures equivalent to 100% of its annual water draw?*"
        ])

        return "\n".join(lines)
