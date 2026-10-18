# AquaCarbon DC — Google Cloud AI Builder Cup Pitch Deck
**Prescribed Submission Template Format (14 Slides)**
**Track:** Sustainability & Social Impact

---

## Slide 1: Team Details
* **Team Name:** AquaCarbon DC
* **Team Leader Name:** Ritoban Dutta
* **Problem Statement:** AI Builder Cup (Sustainability & Social Impact) — Mitigating the hidden environmental and social burden of hyperscale AI data-center cooling on urban water aquifers and regional power grids.

---

## Slide 2: Template Instructions Note
*(Skip / Delete this placeholder slide in final submission)*

---

## Slide 3: Brief About the Idea
* **The Problem:** Modern AI compute clusters consume up to 40% of their power on thermal heat rejection. In water-scarce regions like Bengaluru (aquifer stage: 142% over-exploited), hyperscalers achieve low PUE (1.18) by secretly evaporating over 1,000,000 Liters of drinking water daily.
* **The Core Innovation:** AquaCarbon DC introduces a **Dual-Ledger Platform**. It couples the **Facility Ledger** (operator cost, PUE, WUE, OpEx) directly to the **Community Ledger** (aquifer depletion, domestic household equivalents, substation peak share), exposing burden-shifting trade-offs before data centers are permitted or built.

---

## Slide 4: Opportunities
* **How is it different from existing solutions?**
  * Existing cooling tools (e.g., CooL-LLM, Agentic-Arbiter, FLUIX) optimize *only* for internal operator energy bills.
  * AquaCarbon DC is the first to solve the **integration gap**: simultaneously calculating physical facility thermodynamics and local community water equity.
* **How will it solve the problem?**
  * Replaces unverified greenwashing with a deterministic thermodynamic engine grounded in ASHRAE TC 9.9 and Karimi et al. (2022).
  * Implements an independent adversarial Verifier Agent that guarantees zero hallucinations.
* **Unique Selling Proposition (USP):**
  * **Coupled Dual Ledgers** + **Satellite Spatial Equity Check** (detecting 1.83x unpiped populations) + **24-Hour Diurnal AI Workload Arbiter**.

---

## Slide 5: List of Features Offered by the Solution
1. **The Burden-Shifting Matrix:** 3-dimensional normalized trade-off visualizer across Water, Power, and Carbon.
2. **Coupled Dual Ledgers:** Side-by-side real-time calculation of corporate OpEx vs. domestic household water equivalents.
3. **Satellite Coverage Disparity Check:** Cross-references Copernicus GHSL satellite footprints with municipal GIS pipe rolls to identify 81,480 unpiped residents.
4. **Constraint-Aware Planner:** Evaluates multi-dimensional boundaries with honest refusal rather than hallucinated compromises.
5. **24-Hour Diurnal Arbiter & AI Dispatcher:** Dynamically schedules free-cooling night air economizers (chillers OFF) and shifts 40% AI batch training away from peak heat.
6. **Agentic Investigator & Live Tamper Guardrail:** Conversational Gemini interface verified by an independent auditor that intercepts altered figures live.

---

## Slide 6: Process Flow & Use-Case Diagram
```
[User Input: Site, IT Load (MW), Season, Flexibility]
                        │
                        ▼
           [DETERMINISTIC PHYSICS ENGINE]
      (ASHRAE Heat Balance & Karimi et al. Equations)
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
  Facility Ledger               Community Ledger
(PUE, WUE, Power, OpEx)     (Headroom %, Household Days, Peak Strain)
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
          [GEMINI ADVISOR AGENT (PRO)]
   (Synthesizes Operator & Community Briefs)
                        │
                        ▼
       [INDEPENDENT VERIFIER AUDITOR (FLASH)]
    (Audits 15 Numerical Outputs against Engine)
          │                            │
   [If Tampered/Mutated]         [If Verified]
          ▼                            ▼
   BLOCKED PUBLICATION         ISSUES CRYPTOGRAPHIC
   (Flagged Mismatch Alert)    VERIFIED_AUDIT_SHA256 BADGE
```

---

## Slide 7: Wireframes / Mock Diagrams
*(Include high-resolution UI screenshots from the running prototype at http://127.0.0.1:8000)*:
1. **The Dual-Ledger Dashboard:** 3 side-by-side cooling profiles with color-coded conflict scores.
2. **24-Hour Thermal Arbiter Timeline:** 24-step color strip showing Night Economizer, Dry Chiller, and CooL-LLM AI Shift modes.
3. **Live Tamper Block Guardrail:** Visual demonstration of the Verifier Agent intercepting a -15% mutated metric.

---

## Slide 8: Architecture Diagram of the Proposed Solution
```
┌────────────────────────────────────────────────────────────────────────┐
│                   FIREBASE HOSTING & SPA FRONTEND                      │
│        (HTML5, Vanilla CSS Design System, Responsive Client JS)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS REST / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                  GOOGLE CLOUD RUN (FastAPI Microservice)                │
│                                                                        │
│  ┌───────────────────────────┐         ┌────────────────────────────┐  │
│  │   Deterministic Engine    │         │     Multi-Agent Layer      │  │
│  │  • ASHRAE Heat Balance    │◄───────►│  • Context Agent (GIS/WRI) │  │
│  │  • Karimi et al. (2022)   │         │  • Advisor Agent (Gemini)  │  │
│  │  • 24h Diurnal Arbiter    │         │  • Verifier Auditor Flash  │  │
│  └───────────────────────────┘         └────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│            DATA & STORAGE: FIRESTORE & VERTEX AI PLATFORM               │
│   (Scenario Runs, Provenance Logs, Cryptographic Audit Signatures)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Slide 9: Technologies Used in the Solution
* **Google Generative AI:** Gemini 2.5 Flash & Pro on Vertex AI, Google Agent Development Kit (ADK) pattern.
* **Serverless Compute:** Google Cloud Run (Docker containerized, scale-to-zero, <200MB, sub-second boot).
* **Application Framework:** FastAPI, Uvicorn, Pydantic v2.
* **Client Layer & Database:** Firebase Hosting, Cloud Firestore (for scenario telemetry & audit provenance).
* **Scientific Reference Datasets:** WRI Aqueduct 4.0, Central Ground Water Board (CGWB 2024), CEA Grid Database v19, Copernicus GHSL Satellite Layer.

---

## Slide 10: Estimated Implementation Cost
* **Cloud Run Compute:** ₹0 / month (Fully operational within Cloud Run monthly free tier; downscales to zero instances).
* **Gemini Verification:** ~₹0.005 per scenario evaluation using Gemini 2.5 Flash.
* **Firebase & Firestore:** ₹0 / month (Free tier covers up to 50k reads/day).
* **Total Operating Footprint:** Less than ₹150 / month for 5,000 automated municipal data-center assessments.

---

## Slide 11: Snapshots of the Prototype
1. **Burden-Shifting Matrix:** Evaporative (Water 98/100) vs. Dry (Power 93/100) vs. Hybrid (Balanced 66/100).
2. **24-Hour Hourly Dispatch Schedule:** Hourly temperature, cooling mode, and AI batch load-shift table.
3. **Coverage Disparity Check:** 1.83x ratio chart and 81,480 unpiped tanker-dependent residents.

---

## Slide 12: Prototype Performance Report / Benchmarking
* **Automated Unit & Integration Test Suite:** **40/40 Tests Passing (100% green)** in 1.49s.
* **Section 8 Specification Evaluation Suite (5/5 Benchmarks Passed):**
  1. *Numerical Fidelity:* 15/15 calculated metrics matched between engine and briefs (SHA-256 signed).
  2. *Verifier Catch-Rate:* Injected -15% numerical mutations caught with 100% interception rate.
  3. *Constraint Handling:* Validated feasible configurations and honest refusal on overconstrained inputs.
  4. *Coverage Sensitivity:* 1.83x spatial disparity reliably flagged.
  5. *Recommendation Stability:* Verified seasonal flip between dry summer and monsoon humidity.
* **Deterministic Calculation Latency:** < 180ms.

---

## Slide 13: Additional Details / Future Development
1. **SCADA IoT Ingestion:** Live telemetry ingestion from cooling tower Modbus/BACnet sensors.
2. **Dynamic Grid Carbon Forecasting:** Direct API hooks into national Load Dispatch Centers (SLDC/RLDC).
3. **Multilingual Public Briefs:** Translating community consultation documents into regional Indian languages (Kannada, Tamil, Hindi) via Gemini.

---

## Slide 14: Links
* **GitHub Public Repository:** https://github.com/ritobandutta/aqua-carbon
* **Demo Video Link (3 Minutes):** [Insert your 3-minute video link]
* **Final Product Link:** [Insert your deployed Cloud Run URL]
