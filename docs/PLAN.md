# AquaCarbon DC — Commons Edition: Build Plan

## Context

We're building AquaCarbon DC for the AI Builder Cup (Sustainability & Social Impact) in the empty private repo `ritobandutta/aqua-carbon`. The collaborator is OnHighEngineer.
- **v1 (PDF)**: a decision-support tool that compares 2–3 data-center cooling profiles for one site. It reports a *facility ledger* (energy, PUE, direct water, WUE, carbon, cost), and Gemini explains the trade-offs.
- **v2 (Commons Edition docx)**: adds a *community ledger*, a burden-shifting view, a coverage check, a constraint-aware planner, time-varying what-ifs, an independent verifier agent (A2A), the engine exposed over MCP, and two briefs (operator and community).

Judging weights: Technical/GenAI 40%, Impact 25%, Innovation 25%, UX 10%.

Decisions from the user:
- No time limit, so we aim for the full vision.
- Build and run locally first. OnHighEngineer deploys later from a personal GCP account, so deployment must be documented as we go.
- Frontend is Next.js + Tailwind + shadcn.
- Work split is not decided yet, so the plan is organized as workstreams with clear contracts between them.

**Non-negotiable principle:** the deterministic engine is the only source of numbers. LLMs plan, explain and verify, but never produce a number themselves. Missing data shows as `unavailable` and is never silently replaced with a default.

---

## Architecture

```
web (Next.js)  ──REST/SSE──►  api (FastAPI + ADK orchestrator)
                                 │  ├─ intake agent (Flash)
                                 │  ├─ context agent (Flash + MCP data tools)
                                 │  ├─ planner agent (Pro + engine calls)
                                 │  └─ advisor agent (Pro)
                                 ├──MCP──► engine-mcp (FastMCP wrapper over `aquacarbon_engine`)
                                 ├──A2A──► verifier service (separate process / Cloud Run)
                                 ├──A2A──► community-impact service (separate process / Cloud Run)
                                 └──► store (DuckDB locally │ BigQuery in cloud, same repo interface)
```

- **LLM client:** `google-genai` / ADK, switched by an env flag. Locally it uses an AI Studio API key; in the cloud it uses Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=true`). The same code runs in both places.
- **Locally:** everything runs from `docker compose up` (or `make dev`). A2A services run on separate ports, so the trust boundary between agents is real even on a laptop.
- **Lean stack decision:** drop Genkit and Firebase AI Logic. They overlap with ADK and its evals, and v2's own risk table warns about decorative tech. Cube.js stays deferred. The submission notes record why each was dropped.

## Repo layout (monorepo)

```
engine/        Python package `aquacarbon_engine` — pure, no I/O, no LLM
  models/      cooling profiles (evap tower+chiller, air-cooled chiller/dry cooler, hybrid adiabatic, DLC+dry cooler)
  ledger/      facility.py, community.py, burden.py
  planner/     search.py (grid/enumerate → feasible set → Pareto → nearest-infeasible)
  units.py     Quantity{value, unit, source_id, resolution, confidence} | Unavailable
  sim.py       hourly 8760 simulation over weather series
  tests/       golden-value + property tests (hypothesis)
data/          curated datasets + sources.yaml (provenance registry: id, URL, licence, resolution, accessed date)
  bengaluru/   TMY weather, tariff, water price, grid EF, CGWB, Aqueduct, BESCOM peak, etc.
services/
  api/         FastAPI app, ADK agents, store adapters, SSE streaming
  engine_mcp/  FastMCP server exposing engine functions + data tools
  verifier/    A2A agent: deterministic numeric check + Flash semantic check
  community/   A2A agent: community ledger + coverage check
web/           Next.js App Router + shadcn + Recharts (shadcn charts)
evals/         ADK eval sets, verifier catch-rate harness, planner cases, report generator
docs/          ARCHITECTURE.md, DEPLOYMENT.md, DATA_SOURCES.md, DECISIONS.md (ADR log), DEMO.md, research/
infra/         Dockerfiles, compose.yaml, Cloud Run service YAMLs, BigQuery schema, deploy scripts
```

Tooling:
- Python: `uv` workspace, ruff, pyright, pytest.
- Web: pnpm.
- The API contract is defined by FastAPI's OpenAPI schema. TypeScript types are generated from it with `openapi-typescript`, so the web types never drift from the backend.
- CI runs lint, tests and evals-lite on GitHub Actions.

---

## Engine design (the core of the technical score)

- **Hourly simulation:** run 8760 hours of weather for Bengaluru (TMY or ERA5/Open-Meteo historical, with the source recorded). Hourly resolution means seasonal and time-of-day what-ifs come free.
- **Energy:** `P_cooling(t) = Q_IT / COP_profile(T_db, T_wb, setpoints)` plus fans, pumps and economizer hours. PUE is derived from total energy over IT energy.
- **Direct water** (for evaporative profiles), from physics rather than a fudge factor:
  - Evaporation ≈ rejected heat ÷ latent heat, about 1.5–1.6 L per kWh of heat rejected, scaled by an evaporative fraction.
  - Blowdown = evaporation ÷ (CoC − 1), plus drift.
  - WUE = annual water ÷ IT energy.
- **Indirect water:** grid water intensity (L/kWh, with a sourced range).
- **Carbon:** grid emission factor from the CEA CO₂ Baseline Database. A hourly factor derived from the Grid-India generation mix is a stretch goal.
- **Cost:** BESCOM HT tariff plus BWSSB water tariff.
- **Uncertainty:** every coefficient is a `(low, central, high)` range taken from a cited source (for example Karimi et al. 2022 and ASHRAE). The engine runs all three bands, and the UI shows them as error bars.
- **Thermal safety:** each profile has an envelope (max ambient for its rated capacity, and ASHRAE A1 inlet limits). Hours outside the envelope are flagged and feed into the planner's safety-margin constraint.
- **Reproducibility:** each run gets `run_id = hash(inputs, engine_version, dataset_versions)` and stores the full provenance.

Ledgers:
- **Community ledger indicators:** each one carries a source, a geographic resolution, a confidence level, and an `unavailable` state.
  - Modelled peak water demand as a share of BWSSB supply headroom
  - CGWB groundwater stage of extraction (taluk level)
  - WRI Aqueduct basin water stress
  - Share of BESCOM peak electricity demand
  - Grid carbon intensity
  - Public vulnerability context
- **Burden view:** three normalized bars per profile for water, power and carbon. There is deliberately no combined score.

Planner:
- Enumerates profiles × setpoints × CoC × economizer thresholds.
- The engine evaluates every combination; the planner filters by facility and community constraints, then computes the Pareto set.
- If nothing is feasible, it returns the nearest option using a minimal weighted constraint violation, together with the binding constraints.
- Gemini only parses ambiguous constraints and explains the result.

## Agents and grounding

- **Structured output:** every agent returns a Pydantic schema. The advisor's brief contains `claims[]`, and each claim references `metric_id`s from the engine output.
- **Verifier (A2A):**
  1. A deterministic pass extracts every number in the brief and matches it to the engine output, within a rounding tolerance and with units checked.
  2. A Flash pass checks qualitative claims, for example "saves water" when the water delta is actually positive.
  3. Mismatches block the brief and are sent back to the advisor, with a maximum of 2 retries. After that, the user sees a "could not verify" state rather than an unverified brief.
- **What-ifs:** each what-if creates a new run, then a diff object (changed inputs → changed metrics → whether the recommendation flipped) is generated deterministically before Gemini explains it.
- **Gemma gate:**
  - Build a hand-labelled set of 20–30 public documents (BWSSB and BESCOM reports, CEA PDFs).
  - Measure Flash's extraction accuracy on that set first.
  - Fine-tune Gemma only if Flash falls short or cost and latency justify it, and record the result either way.

## UX (web)

The flow follows v2 §5: **Describe → Compare → Investigate → What-if → Coverage → Decide/Share**.
- **Scenario builder:** a form plus a plain-language box handled by the intake agent. The input summary shows source badges and missing-data warnings.
- **Comparison view:** facility and community ledgers side by side, the burden bars, and seasonal charts (monthly energy and water, hourly carbon).
- **Chat panel:** streams agent answers over SSE. A "verified ✓" badge shows per brief, with a click-through to the supporting numbers.
- **What-if drawer:** sliders and toggles for season, grid factor, water availability and constraints. Changes animate as a diff, and a "recommendation flipped" callout appears when it flips.
- **Coverage panel and export:** the coverage panel lists low-confidence indicators. Operator and community briefs export as PDF or Markdown.
- **Synthetic data labels:** synthetic facility inputs are permanently labelled "Illustrative".

---

## Phased build order (Must → Should → Could; each phase ends with a working demo)

**Phase 0 — Groundwork and verify-before-building (v2 §13)**
- **Commit authorship first:** set the repo-local `git config user.name/email` to the personal identity before any further commits. Only the initial README commit carries the office email so far.
- Confirm eligibility, deadline and deliverables with the organizers.
- Confirm current Gemini and Gemma model IDs, ADK and A2A SDK versions, and Vertex fine-tuning availability.
- **Dataset audit:** check access and licence for each dataset (WRI Aqueduct, Open-Meteo/ERA5, CEA baseline, Grid-India, BESCOM/BWSSB tariffs and capacity, CGWB, GHSL/WorldPop, Census) and write the results into `docs/research/datasets.md` and `data/sources.yaml`.
- **Coefficient research:** pull coefficient ranges from Karimi et al., ASHRAE and vendor datasheets, then pick the 2 core profiles. Most likely these are an evaporative tower + water-cooled chiller versus an air-cooled chiller/dry cooler.
- **Prior-art pass:** look again at integrated cooling-plus-community tools.

**Phase 1 — Foundation**
- Set up the monorepo skeleton, uv workspace, pnpm web app, compose file, CI, `.env.example`, and docs stubs including `DEPLOYMENT.md`.

**Phase 2 — Engine (Must)**
- Build `units.py`, two profiles, the hourly sim, the facility ledger, cost and carbon, uncertainty bands, and provenance.
- **Tests:**
  - Golden values worked out by hand in a notebook that is exported to a test fixture.
  - Property tests, for example: higher wet-bulb → more water, higher CoC → less blowdown, a higher grid EF changes carbon only.

**Phase 3 — API, store and web MVP (Must)**
- FastAPI endpoints for scenarios, runs and results, with diffs.
- A DuckDB store behind a repository interface.
- Web pages for the scenario builder, the facility ledger comparison, and what-if reruns.

**Phase 4 — Grounded Gemini (Must)**
- ADK orchestrator with the intake agent, plus advisor explanations that consume structured engine output.
- SSE chat panel.
- Numerical-fidelity test on the explanations.
- **Must tier complete at this point:** a full v1 demo works end to end.

**Phase 5 — Community ledger and burden view (Should)**
- Community-impact service over A2A, with honest unavailable and low-confidence states.
- Burden bars in the UI.

**Phase 6 — Verifier, planner and seasonal what-ifs (Should)**
- Verifier service over A2A with the retry loop.
- Engine MCP server, and agents switched to call the engine through MCP.
- Constraint planner with Pareto and nearest-infeasible results.
- Dry versus monsoon what-ifs, with recommendation-flip detection.

**Phase 7 — Evals (Should)**
- Implement the full v2 §8 harness:
  - numerical fidelity
  - verifier catch-rate (injected errors)
  - planner known cases
  - recommendation stability
  - inference cost and latency per scenario
- Generate `docs/EVAL_REPORT.md` automatically from the results.

**Phase 8 — Stretch (Could)**
- Coverage check on one real layer pair (GHSL built-up vs Census) at ward level, with seeded-gap tests.
- Hourly grid carbon from the Grid-India mix.
- A future-grid scenario.
- The community brief in Kannada/Hindi.
- Gemma extraction, if it passes its gate.
- Optional 3rd and 4th profiles (hybrid adiabatic, DLC).

**Phase 9 — Deploy-ready and demo**
- BigQuery store adapter and schema.
- Cloud Run manifests for api, engine-mcp, verifier and community; web on Firebase Hosting (Next.js) or Cloud Run.
- Secret Manager setup.
- One-command deploy script.
- Demo script following v2 §14, plus a seeded demo scenario.
- README and submission write-up.

## Deployment documentation (maintained continuously)

`docs/DEPLOYMENT.md` grows with each phase and covers:
- the GCP project setup checklist: APIs to enable, IAM service accounts per service with least privilege, the Artifact Registry repo
- env vars per service
- the Vertex versus AI Studio switch
- the BigQuery dataset and table DDL in `infra/bigquery/`
- Cloud Run deploy commands for each service, including the A2A service URLs and auth (service-to-service IAM)
- Firebase Hosting config
- cost guardrails: budget alert, min-instances=0
- teardown steps

Any project or account specifics stay as placeholders, so OnHighEngineer can deploy from a personal account.

## Verification

- **Engine:** `uv run pytest engine` covers golden and property tests, and coverage on `engine/` is at least 90%.
- **Services:** `make dev` starts the full stack. A Playwright smoke test then walks the demo path: describe → compare → ask → what-if → planner refusal → export.
- **Agents:** `uv run python -m evals.run` produces `EVAL_REPORT.md`, which reports fidelity (target 100%), verifier catch-rate, planner correctness and stability.
- **Cold-start demo:** a clean clone, `cp .env.example .env` with a Gemini API key added, then `make dev`, completes the demo with no manual steps.
