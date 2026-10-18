# AquaCarbon DC — Commons Edition (v2)
## Specification & Architecture Document

### 1. Executive Summary & Vision
**AquaCarbon DC (Commons Edition)** is an integrated, agentic, and confidence-aware platform that evaluates data-center cooling choices through two complementary lenses:
1. **The Facility Ledger**: Computing energy consumption, Power Usage Effectiveness (PUE), direct water consumption, Water Usage Effectiveness (WUE), carbon emissions (Scope 2), and operating costs for data-center operators.
2. **The Community Ledger**: Computing local water headroom depletion, regional aquifer stress context, grid reliability and substation peak burden, community vulnerability indices, and explicit data confidence scores.

The platform bridges the gap with:
- **Burden-Shifting Matrix**: Showing how cooling decisions relocate burden across Water, Power, and Carbon without arbitrary collapsed scores.
- **Independent Verifier Agent**: A dedicated agent checking every number and claim in generated briefs against the deterministic calculation engine, eliminating LLM hallucinations.
- **Coverage Check**: Comparing satellite-derived settlement footprints against official piped-water infrastructure to flag uncounted, tanker-dependent communities.
- **Constraint-Aware Planner**: Searching cooling configurations against both facility limits (budget, PUE, thermal headroom) and community limits (headroom %, grid peak %), returning honest refusals when no configuration meets all constraints.
- **Time-Varying What-Ifs**: Dynamic recalculations across dry hot summer vs. humid monsoon seasons and evolving grid carbon factors.

---

### 2. Core Architectural Principles
1. **Deterministic Engine as Single Source of Truth**:
   - The numerical engine computes all physics, thermodynamics, water balance, and carbon totals.
   - LLMs *never* invent, hallucinate, or recalculate physical constants, weather parameters, or cooling metrics.
2. **Dual-Audience Outputs**:
   - Technical Operator Brief (cooling tower cycles of concentration, dry-bulb/wet-bulb trade-offs, O&M costs).
   - Plain-Language Community Brief (daily water intake in terms of household equivalents, grid peak overlap, questions for public hearings).
3. **Honest Data Gaps**:
   - Missing data is rendered explicitly as `UNAVAILABLE` with low confidence scores, never imputed invisibly.
4. **Cloud Run Zero-Instance Readiness**:
   - Ultra-fast container startup (<1s), stateless, sub-millisecond calculation engine, parameterizable secrets via environment variables.

---

### 3. Cooling Profiles & Deterministic Formulation

Based on published industry benchmarks (e.g., Karimi et al. 2022, ASHRAE TC 9.9, WRI India):

#### Profile A: Evaporative Cooling (Direct Evaporative / Cooling Towers with Water-Cooled Chillers)
- **Cooling Mechanism**: Heat rejected through latent heat of vaporization of water.
- **PUE**: Low (~1.18 - 1.25) because fans and water pumps require relatively low electricity.
- **Direct Water Consumption (WUE)**: High (~1.8 - 2.5 L/kWh IT load).
- **Burden**: Low power & lower direct carbon, but high burden on municipal and groundwater supplies. Vulnerable in dry summer seasons with high ambient dry-bulb.

#### Profile B: Dry Cooling (Air-Cooled Chillers with Economizers)
- **Cooling Mechanism**: Heat rejected through sensible heat exchange directly into ambient air using heavy chiller compressor cycles and high-flow air fans.
- **PUE**: Higher (~1.38 - 1.55) due to continuous compressor work in hot climates.
- **Direct Water Consumption (WUE)**: Near zero (0.00 - 0.05 L/kWh).
- **Burden**: Zero local water burden, but pushes massive burdens onto the electric grid, substation peak capacity, and Scope 2 carbon emissions.

#### Profile C: Hybrid Adiabatic Cooling (Smart Trim Evaporative + Dry Cooler)
- **Cooling Mechanism**: Operates dry during cooler ambient hours; uses minimal adiabatic misting/trim water only during peak ambient temperatures above wet-bulb threshold (e.g. >28°C).
- **PUE**: Moderate (~1.25 - 1.32).
- **Direct Water Consumption (WUE)**: Moderate (~0.5 - 0.9 L/kWh).
- **Burden**: Balanced compromise, reducing peak water withdrawal by 65% compared to evaporative, while avoiding the 25%+ power penalty of pure dry cooling.

---

### 4. Mathematical Engine Specification

Given:
- $P_{\text{IT}}$: IT Workload Power (MW)
- $H$: Annual operating hours (8,760 hours)
- $E_{\text{IT}} = P_{\text{IT}} \times H$: Annual IT Energy (MWh)
- $\text{PUE}$: Power Usage Effectiveness ($P_{\text{Total}} / P_{\text{IT}}$)
- $E_{\text{Total}} = E_{\text{IT}} \times \text{PUE}$: Total Facility Electricity (MWh)
- $E_{\text{Cooling}} = E_{\text{IT}} \times (\text{PUE} - 1.05)$: Cooling Electricity (MWh, assuming 0.05 for lights/losses)
- $\text{WUE}$: Water Usage Effectiveness (L/kWh of IT load)
- $W_{\text{Direct}} = E_{\text{IT}} \times \text{WUE} \times 1000$ (Liters) / $10^6$ (Megaliters or $m^3 \times 10^{-3}$)
- $C_{\text{Grid}}$: Grid Carbon Intensity (kg CO2e / MWh or g CO2e / kWh)
- $\text{Carbon}_{\text{Total}} = (E_{\text{Total}} \times C_{\text{Grid}}) / 1000$ (Metric Tonnes CO2e)
- $T_{\text{Electricity}}$: Electricity Tariff ($/kWh or INR/kWh)
- $T_{\text{Water}}$: Commercial Water Tariff ($/m³ or INR/kL)
- $\text{Cost}_{\text{Total}} = (E_{\text{Total}} \times 1000 \times T_{\text{Electricity}}) + (W_{\text{Direct}} \times 1000 \times T_{\text{Water}})$

#### Community Indicators
- **Local Water Headroom**: Utility allocation or sustainable aquifer recharge budget $W_{\text{Headroom}}$ (ML/yr).
- **Water Headroom Impact %**: $(W_{\text{Direct}} / W_{\text{Headroom}}) \times 100$
- **Household Water Equivalent**: $W_{\text{Direct}} / (\text{Household LPCD} \times 365 \times \text{Household Size})$
  - Bengaluru standard: 135 Liters per capita per day (LPCD), 4.2 members per household = ~207,000 L / household / year.
- **Local Substation Peak Impact %**: $(P_{\text{Peak, Facility}} / P_{\text{Substation Capacity}}) \times 100$
- **Aquifer Stress Classification**: Sourced from Central Ground Water Board (CGWB) & WRI Aqueduct (e.g. Over-Exploited / Critical / Semi-Critical / Safe).
- **Grid Outage & Reliability Index**: SAIDI / SAIFI indices for the local DISCOM (e.g., BESCOM in Bengaluru).

---

### 5. Multi-Agent System Architecture

1. **Intake Agent**: Accepts natural language queries (e.g., "We are planning a 15 MW data center in Whitefield Bengaluru with high summer heat") and parses into a typed scenario configuration.
2. **Context Agent**: Provides verified climate profiles (dry-bulb, wet-bulb, humidity), water stress data, grid emission factors, and local utility headroom.
3. **Calculation Engine (Deterministic Core)**: Calculates facility ledgers, community ledgers, and burden matrices.
4. **Planner Agent**: Evaluates facility constraints ($\text{PUE} \le 1.30, \text{Cost} \le X$) vs community constraints ($\text{Water Headroom Share} \le 15\%, \text{Grid Increase} \le 8\%$). Yields feasible sets or explicit constraint violation diagnostics.
5. **Community Impact & Coverage Agent**: Computes vulnerable population metrics and runs the coverage disparity check (Census vs Satellite footprint).
6. **Advisor Agent**: Generates structured operator and community briefs using strict prompt anchoring.
7. **Verifier Agent (Independent Trust Boundary)**: Inspects the generated briefs against the raw calculation engine output. Verifies:
   - Does every reported PUE, MWh, ML water, tCO2, and cost match within $\pm 0.1\%$?
   - Are there unsupported claims or ungrounded statistics?
   - Signs an immutable verification badge (`PASSED` / `REJECTED`) with specific diff audit trails.

---

### 6. Verification and Testing Plan
As defined in Section 8 of the specification:
1. **Numerical Fidelity Test**: Validates that all numbers referenced in briefs correspond exactly to deterministic engine outputs.
2. **Verifier Catch-Rate Test**: Injects perturbed numbers into briefs and validates that the Verifier Agent flags every injected discrepancy (one corrupted metric at a time, plus a fabricated claim).
3. **Constraint Planner Test**: Checks feasible vs. infeasible constraint boundaries.
4. **Coverage Disparity Test**: Verifies flagging of unserved informal settlements when spatial footprint exceeds piped census records.
5. **Recommendation Stability Test**: Confirms deterministic reproducibility under identical inputs and predictable flipping under changed environmental inputs (e.g., Dry Summer vs. Wet Monsoon).
