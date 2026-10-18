# Status: Validation and Plan Gap Analysis

Last updated 2026-10-18. Covers the implementation OnHighEngineer pushed (46 files, 16 commits) measured against [`PLAN.md`](PLAN.md) and the v2 product doc.

`PLAN.md` was written before that implementation landed. The implementation chose a simpler shape (one FastAPI app, vanilla JS UI, agents as plain classes). Where the two differ, this file says which one is current.

## What was validated

| Check | Result |
|---|---|
| Test suite | 33 passing (was 10 passing and 6 failing before this pass) |
| Eval suite (`python -m evals.run_evals`) | 5 of 5 pass, with the stricter verifier |
| Docker image builds and serves | Yes. `/api/health`, `/`, and `/api/evals/run` all work in the container |
| Secrets in git history | None found (scan for API-key patterns) |
| `.pyc` files tracked | Removed |
| Live Gemini path | **Not exercised.** No API key was available. Fallback path and the verifier gate are tested with a mocked model |

## Defects found and fixed in this pass

| # | Defect | Fix |
|---|---|---|
| 1 | `/api/investigate` crashed with `NameError` whenever no Gemini key was set (`q_lower` never defined) and also if the Gemini call failed. The documented offline fallback never worked. | Rewrote the investigator path. Tests cover no-key, hallucinating-model and faithful-model cases |
| 2 | Verifier reported `matched=True` unconditionally for carbon and headroom, so those could never fail. True single-error catch rate was 77%, not the 100% claimed. The eval's "13.3%" figure was the share of checks failing under one blanket mutation, not a catch rate. | Verifier now requires every headline value to be cited, and checks every unit-tagged number against engine values. Eval injects one corruption at a time plus a fabricated claim: 14 of 14 caught |
| 3 | Verifier ignored extra fabricated numbers if the true ones were still present. | New claim check flags any unit-tagged number that matches no engine value or pairwise difference |
| 4 | Investigator answers were hard-coded `PASSED` and never verified. | Every answer, Gemini or template, now goes through the verifier. A Gemini draft that fails is blocked and replaced by the deterministic answer |
| 5 | Audit signature used Python `hash()`, which changes per process, and was described as cryptographic. | SHA-256 over the check results. Deterministic |
| 6 | Planner refusal text was one fixed paragraph regardless of constraints. `min_data_confidence` was accepted but ignored. | Messages derive from the actual violations. Names binding constraint and the closest profile. `min_data_confidence` enforced |
| 7 | Model output was inserted with `innerHTML` unescaped (XSS from a bad model reply or query). | HTML-escape before the markdown subset is applied |
| 8 | Endpoint tests required a server on port 8000 (collided with an unrelated container). | Tests use an in-process `TestClient` |
| 9 | `python-dotenv` and `google-genai` were imported but missing from `requirements.txt`, so a clean install failed. | Added |
| 10 | README, FLOW, SPEC and UI footer claimed "zero hallucination", "cryptographic", Gemini 1.5 Pro and Gemma, ADK, while code uses none of those as described. | Reworded to what the code does. Eval output in README regenerated from a real run |

## Known limitations (not fixed, be honest about them in the demo)

1. **The numbers are table lookups, not a simulation.** `engine/calculator.py` takes base PUE and WUE per profile and applies seasonal multipliers. There is no hourly 8760 model, no wet-bulb-driven physics, and no uncertainty bands. The PLAN's engine design is not built. Coefficients cite Karimi et al. in comments but are not traced to specific tables.
2. **Regional data is hard-coded in Python** (`engine/data_sources.py`, `engine/coverage.py`) with source names but no URLs, licences, access dates or datasets. Several figures look like illustrative values, for example the 220 ML headroom, the 60 MW substation, the 46% tanker dependency, the coverage km² values. `docs/DATA_SOURCES.md` is still entirely unverified. Do not present them as sourced until each is checked.
3. **All community indicators are labelled HIGH or MEDIUM confidence**, including ones that are assumed. Nothing is ever `unavailable`, which contradicts the v2 principle. The coverage check lowers a confidence in prose only. It does not change any indicator.
4. **Two engines exist.** `engine/core.py` (used only by `engine.py`, `adk_verifier.py`, `streamlit_app.py`) and `engine/calculator.py` (used by the API) give different numbers for the same profile. For example evaporative PUE is 1.18 in one and 1.22 in the other for similar inputs. They should be merged or the standalone one removed.
5. **`adk_verifier.py` is a demo script** with its own looser check and hard-coded fallback defaults. It is not the verifier the API uses.
6. **No real ADK, MCP or A2A.** The "agents" are in-process classes. The verifier is not a separate service, so the trust-boundary claim is design intent only. `PLAN.md` Phase 6 covers this.
7. **Gemini is only used for the investigator answer.** The operator and community briefs are string templates, not model output. The verifier therefore checks template text for those, which is a weaker test than checking model text.
8. **Investigator and brief verification is number-only.** Qualitative claims ("saves water") are not checked.
9. **The planner enumerates three fixed profiles**, with no setpoint or CoC search and no Pareto set.
10. **Some template prose has hard-coded numbers** (for example "~69%" and "over 65%" water savings in the advisor brief). They are not derived from the engine, and the verifier does not look at percentages of that kind.
11. **Workload-shifting and arbiter results are modelled with fixed multipliers** (for example WUE x0.82), so they illustrate the idea but are not derived.
12. **CORS is `*` and the API is unauthenticated.** Fine for a public judging demo, not for anything else.

## Update 2026-10-18 (later): completed since the table above

- One engine (`engine/calculator.py`). `engine/core.py`, `engine.py`, `adk_verifier.py` removed. Streamlit now uses the same engine.
- Unknown regions return 404 instead of silently using Bengaluru.
- Confidence is derived from provenance: untraced values are LOW and labelled illustrative. The coverage check lowers dependent indicators.
- `run_id` and `engine_version` on results. Evals now 9 checks (repeat-run stability, seeded gap with control, season flip, latency). CI workflow, Makefile and `docs/DEMO.md` added.
- Dataset audit run: see `docs/DATA_SOURCES.md`. Result: nothing verified against an official file. The 710 kg/MWh factor and the 2.10 L/kWh evaporative WUE are the two values most likely to be wrong.

Limitations 3 and 4 above are resolved. Limitation 2 remains open and is now documented in detail.

## Update 2026-10-18 (latest): engine bands, separate verifier, Gemini briefs

- **Sensitivity ranges** (`evaluate_with_bands`): water, energy, carbon and cost each shown as low/central/high. These are **assumed sensitivity ranges around unverified inputs, not sourced confidence intervals**, and the UI says so.
- **Physics bound tests** (`tests/test_bands_and_physics.py`): evaporative WUE checked against a derived floor and ceiling in every season.
- **Verifier as a separate service** (`verifier_service/`, `Dockerfile.verifier`, `make run-verifier`). Set `VERIFIER_URL` and all verification runs there. The service recomputes ground truth itself from the scenario, so the caller cannot supply favourable numbers. If the service is configured but unreachable, the output is **blocked (fails closed)**. Verified with two real processes. This is plain HTTP, not the A2A protocol.
- **Gemini-drafted briefs**: the model writes prose with placeholders like `{{evaporative.pue}}`, never digits. The engine fills them, appends an engine-generated figures table, and the verifier still checks the result. A draft with its own numbers, an invented placeholder, or a failed check falls back to the template. Tested with a mocked model only.
- **Vertex AI path**: `GOOGLE_GENAI_USE_VERTEXAI=true` uses Application Default Credentials. Untested, no credentials available.
- Correction: the earlier note that 2.10 L/kWh "looks high versus LBNL" compared against a fleet average and was not like-for-like. See `DATA_SOURCES.md`.

Still not done: official-source verification of every regional number (needs a person with access), live Gemini and Vertex tests (need a key or project), hourly simulation, real ADK/MCP/A2A protocols, Gemma, Kannada/Hindi brief.

## Update 2026-10-18 (latest): second use case, Permit Claim Review (ADK + MCP + A2A)

Design and caveats are in [`AGENTIC_REVIEW.md`](AGENTIC_REVIEW.md). In short:
- **MCP** (`mcp_server/`): the engine as typed tools. **ADK** (`review/service.py`): a claim extractor and a reviewer agent that calls those tools. **A2A** (`a2a_verifier/`): an independent verifier process that recomputes the numbers and fails closed.
- The model never produces a number. Tests cover an invented claim, tampered tool arguments, and a model that skips the tool; each is blocked. A test also checks that the verifier process loads no reviewer-side code and holds no model client.
- `agents/__init__.py` is now lazy. Before this, importing the verifier also loaded the advisor, orchestrator and planner, which defeated the independence claim.
- Needs Python 3.11 or newer for ADK (`requirements-agents.txt`, `Dockerfile.review`). The base app is unchanged and `/api/review` returns 503 without the extras.
- ADK's A2A support is marked experimental by Google.
- **Not verified:** real Gemini on the agentic path (scripted stand-in only), the UI tab in a browser, GCP deployment, and the rebuilt three-container run after the MCP host-header fix (the rerun was blocked by an automated safety check in this session).

## Plan status

| Plan phase | State |
|---|---|
| 0. Verify before building | **Not done.** Eligibility, deadline, model IDs, dataset licences, coefficient sourcing, prior art are all open. See [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md). Dataset audit is the biggest gap (limitation 2) |
| 1. Foundation | **Partly.** Dockerfile, CI absent, no uv workspace (plain `requirements.txt`), no Makefile or compose. Single-app layout instead of the monorepo |
| 2. Engine | **Prototype.** Three profiles, seasonal multipliers, ledgers, tests. Missing: hourly sim, uncertainty bands, thermal envelope hours, run provenance and `run_id` |
| 3. API, store and web MVP | **Done in a simpler form.** FastAPI plus static JS UI. No store (stateless), no generated TypeScript types |
| 4. Grounded Gemini | **Partly.** Live Gemini for the investigator only, now verified. Briefs are templated |
| 5. Community ledger and burden view | **Done** (8 indicators, burden bars). Confidence handling is not honest yet (limitation 3) |
| 6. Verifier, planner, seasons | **Partly.** In-process verifier (strengthened), planner (fixed), seasonal what-if. No A2A or MCP, no flip detection |
| 7. Evals | **Partly.** 5 checks, deterministic, run from the UI and CLI. Missing: inference cost and latency, stability on repeated runs, seeded-gap test for the coverage check |
| 8. Stretch | Coverage check exists on benchmark numbers, not real layers. Hourly diurnal arbiter exists. No Kannada or Hindi brief, no Gemma |
| 9. Deploy-ready and demo | **Partly.** Dockerfile and `deploy_cloudrun.sh` exist. No BigQuery, no Secret Manager wiring, no demo script |

## Recommended next steps, in order

1. **Phase 0 dataset audit.** Replace each hard-coded regional number with a cited, dated value or mark it `unavailable` with low confidence. Highest impact on both honesty and the Impact score.
2. **Make confidence real.** Derive indicator confidence from source quality, and let the coverage check lower the indicators it affects.
3. **Merge the two engines** into `engine/calculator.py` and delete the duplicate.
4. **Ground the briefs.** Have Gemini draft them from structured engine output, with the verifier gating them. Check qualitative claims.
5. **Engine depth.** Add the hourly simulation and uncertainty bands, or state clearly that the demo uses annual multipliers.
6. **Separate verifier service** over HTTP, if the trust-boundary claim is kept.
7. **Exercise the live Gemini path** with a real key before the demo, and confirm the model ID.
8. **Demo script and clean-run check** from a fresh clone.

Items 1 and 7 need either the friend's key or a personal one, and 1 needs web access to the sources.
