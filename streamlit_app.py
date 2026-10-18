"""
AquaCarbon DC: optional Streamlit view of the same engine the API uses.
Run with: streamlit run streamlit_app.py
All numbers come from engine.calculator, the single calculation engine.
"""

import pandas as pd
import streamlit as st

from engine.calculator import evaluate_scenario
from engine.data_sources import REGIONAL_PROFILES
from engine.models import ScenarioInput, Season, WorkloadType

st.set_page_config(page_title="AquaCarbon DC", page_icon="💧", layout="wide")
st.title("AquaCarbon DC — Commons Edition")
st.caption("Modelled potential impact with illustrative facility inputs. Not measured savings.")

st.sidebar.header("Scenario")
region = st.sidebar.selectbox("Region", sorted(REGIONAL_PROFILES), format_func=str.title)
season = st.sidebar.selectbox("Season", [s.value for s in Season], format_func=lambda v: v.replace("_", " ").title())
workload = st.sidebar.selectbox("Workload", [w.value for w in WorkloadType], format_func=lambda v: v.replace("_", " ").title())
it_load = st.sidebar.slider("IT capacity (MW)", 5.0, 60.0, 15.0, 2.5)
grid = st.sidebar.slider("Grid carbon (kg CO2/MWh)", 300.0, 900.0, 710.0, 10.0)

assessments = evaluate_scenario(ScenarioInput(
    region=region, season=Season(season), workload_type=WorkloadType(workload),
    it_capacity_mw=it_load, grid_carbon_factor_kg_per_mwh=grid,
))

st.subheader("Burden-shifting view (no combined score)")
st.dataframe(pd.DataFrame([
    {
        "Profile": a.cooling_name,
        "Water burden (0-100)": a.burden_scores.water_system_burden,
        "Power burden (0-100)": a.burden_scores.power_system_burden,
        "Carbon burden (0-100)": a.burden_scores.carbon_atmosphere_burden,
    }
    for a in assessments.values()
]).set_index("Profile"))

st.subheader("Facility ledger")
st.dataframe(pd.DataFrame([
    {
        "Profile": a.cooling_name,
        "PUE": a.facility_ledger.pue,
        "WUE (L/kWh)": a.facility_ledger.wue,
        "Energy (MWh/yr)": a.facility_ledger.total_facility_energy_mwh,
        "Direct water (ML/yr)": a.facility_ledger.direct_water_consumption_ml,
        "Scope 2 (tCO2e/yr)": a.facility_ledger.scope2_carbon_tonnes,
        "OpEx (INR Cr/yr)": a.facility_ledger.annual_operating_cost_inr_crores,
    }
    for a in assessments.values()
]).set_index("Profile"))

st.subheader("Community ledger")
rows = []
for a in assessments.values():
    cl = a.community_ledger
    for ind in (cl.water_headroom_share_pct, cl.substation_peak_demand_share_pct, cl.aquifer_stress_classification,
                cl.tanker_dependency_index, cl.grid_outage_risk_index, cl.grid_carbon_intensity):
        rows.append({
            "Profile": a.cooling_name, "Indicator": ind.name, "Value": ind.formatted_value,
            "Source": ind.source_label, "Resolution": ind.geographic_resolution,
            "Confidence": ind.confidence.value,
        })
st.dataframe(pd.DataFrame(rows))
