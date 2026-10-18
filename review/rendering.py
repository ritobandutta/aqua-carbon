"""Deterministic review text built only from verdict rows returned by the engine (via MCP)."""

from typing import Dict, List

_LABEL = {"pue": "", "wue_l_per_kwh": " L/kWh", "direct_water_ml": " ML", "facility_energy_mwh": " MWh",
          "scope2_carbon_tonnes": " tCO2e", "operating_cost_inr_crores": " INR Cr"}
_NAME = {"evaporative": "Evaporative cooling", "dry_cooling": "Dry (air-cooled) cooling",
         "hybrid_adiabatic": "Hybrid adiabatic cooling"}


def fmt(metric: str, value: float) -> str:
    """Printed precision is chosen so the verifier's rounding tolerance always accepts it."""
    if metric in ("pue", "wue_l_per_kwh", "operating_cost_inr_crores"):
        return f"{value:.2f}{_LABEL[metric]}"
    if metric == "direct_water_ml":
        return f"{value:.1f}{_LABEL[metric]}"
    return f"{value:,.0f}{_LABEL[metric]}"


def render_review(scenario_line: str, verdicts: List[Dict]) -> str:
    lines = [
        "## Claim check against the modelled range",
        f"_{scenario_line}. Modelled values use illustrative, unverified inputs, so each result is a prompt for "
        "questions, not a finding that the applicant is wrong._",
        "",
        "| Profile | Metric | Applicant states | Modelled range | Result |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for v in verdicts:
        m = v["metric"]
        result = {"within_modelled_range": "within range",
                  "below_modelled_range": "below modelled best case",
                  "above_modelled_range": "above modelled worst case"}[v["verdict"]]
        lines.append(
            f"| {_NAME.get(v['cooling_type'], v['cooling_type'])} | {v['label']} | {fmt(m, v['claimed_value'])} | "
            f"{fmt(m, v['modelled_low'])} to {fmt(m, v['modelled_high'])} | {result} |"
        )
    lines += ["", "## Questions for the applicant"]
    asked = 0
    for v in verdicts:
        m, who = v["metric"], _NAME.get(v["cooling_type"], v["cooling_type"]).lower()
        if v["verdict"] == "below_modelled_range":
            lines.append(
                f"- The stated {v['label'].lower()} for {who} is {fmt(m, v['claimed_value'])}, below the modelled best case of "
                f"{fmt(m, v['modelled_low'])}. Which design assumptions (for example water source, cycles of concentration, "
                f"operating hours, climate data) produce that figure, and can they be shown?"
            )
            asked += 1
        elif v["verdict"] == "above_modelled_range":
            lines.append(
                f"- The stated {v['label'].lower()} for {who} is {fmt(m, v['claimed_value'])}, above the modelled worst case of "
                f"{fmt(m, v['modelled_high'])}. Is this a deliberate safety margin, and what limit is the permit being sought for?"
            )
            asked += 1
    if not asked:
        lines.append("- All stated figures fall within the modelled range. Ask how each will be metered and reported once operating.")
    lines += [
        "- Will water use, energy use and grid demand be metered and published, and who audits the meters?",
        "- Which water source will supply the cooling system in a dry summer, and what happens to neighbouring supply if it is curtailed?",
    ]
    return "\n".join(lines)
