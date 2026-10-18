# Architecture

Status: **design**, nothing built yet. Companion to [`PLAN.md`](PLAN.md). Rationale for choices is in [`DECISIONS.md`](DECISIONS.md).

## Components

```
web (Next.js)  ──REST/SSE──►  api (FastAPI + ADK orchestrator)
                                 │  ├─ intake agent (Flash)
                                 │  ├─ context agent (Flash + MCP data tools)
                                 │  ├─ planner agent (Pro + engine calls)
                                 │  └─ advisor agent (Pro)
                                 ├──MCP──► engine-mcp (FastMCP wrapper over aquacarbon_engine)
                                 ├──A2A──► verifier service
                                 ├──A2A──► community-impact service
                                 └──► store (DuckDB locally │ BigQuery in cloud)
```

| Component | Responsibility | Talks to |
|---|---|---|
| `engine/` | Pure Python. Hourly simulation, cooling profiles, facility and community ledgers, planner search. No I/O, no LLM. | imported by services |
| `services/engine_mcp` | Exposes engine functions and curated data lookups as typed MCP tools. Logs every call for provenance. | agents |
| `services/api` | REST and SSE for the web app. Hosts the ADK orchestrator and the intake, context, planner and advisor agents. Owns the store adapter. | web, MCP, A2A, store |
| `services/verifier` | Independent check of every number and claim in a brief against engine output. Blocks mismatches. | api (A2A) |
| `services/community` | Builds the community ledger and runs the coverage check. | api (A2A) |
| `web/` | Scenario builder, comparison, chat, what-if drawer, coverage panel, brief export. | api |
| store | Scenario inputs, runs, results, provenance. | api |

## Data flow for one analysis

1. **Describe.** The user fills a form or types plain language. The intake agent returns a validated `Scenario` (Pydantic). Missing fields stay missing and are flagged.
2. **Context.** The context agent fetches weather, water-stress, grid-factor and outage context through MCP tools. Each value arrives with source, resolution and confidence.
3. **Compute.** The api calls the engine through MCP. The engine returns a `RunResult` with the facility ledger, uncertainty bands, thermal-envelope flags and `run_id`.
4. **Community ledger.** The community service builds the ledger and coverage flags from the `RunResult` and context.
5. **Explain.** The advisor drafts a brief as structured output. Every claim references `metric_id`s from the result.
6. **Verify.** The verifier checks numbers deterministically, then qualitative claims with a Flash pass. A mismatch goes back to the advisor, up to 2 retries. After that the user sees "could not verify", never an unverified brief.
7. **Present.** The web app shows ledgers, burden bars, assumptions and the brief with its verified badge.
8. **What-if.** A changed input creates a new run. The engine diff (inputs, metrics, recommendation flip) is computed deterministically *before* Gemini explains it.

## Trust boundaries

- **Engine is the source of numeric truth.** Nothing downstream may produce a metric.
- **Verifier independence.** It runs as a separate process and, in the cloud, a separate Cloud Run service with its own service account. It receives the brief and the engine output, and never the advisor's prompt or reasoning. This is why it is reached over A2A and not a function call.
- **Community service** is also separate over A2A, so its access to external data is isolated from the api.
- **LLM output is untrusted** until validated against a schema and the verifier.

## Core contracts

Defined in code as Pydantic models once Phase 1 starts. The OpenAPI schema generates the TypeScript types.

| Contract | Key fields |
|---|---|
| `Quantity` | `value`, `unit`, `source_id`, `resolution`, `confidence`, optional `(low, central, high)` band. Or `Unavailable(reason)`. |
| `Scenario` | site context, IT load, period, profile ids, constraints, assumption overrides, `illustrative: bool` |
| `RunResult` | `run_id`, per-profile facility ledger, community ledger, burden view, envelope flags, provenance |
| `Diff` | changed inputs, changed metrics, `recommendation_flipped`, binding constraints |
| `Brief` | `audience` (operator or community), `claims[]` each with `metric_ids`, verification status |

`run_id = hash(inputs, engine_version, dataset_versions)`. The same inputs always give the same run.

## Local versus cloud

| Concern | Local | Cloud (later, personal GCP) |
|---|---|---|
| LLM | AI Studio API key | Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=true`) |
| Store | DuckDB file | BigQuery |
| Services | separate ports via compose | separate Cloud Run services |
| Secrets | `.env` (git-ignored) | Secret Manager |
| Web | `next dev` | Firebase Hosting or Cloud Run |

The same code runs in both. Differences are env vars and the store adapter. See [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Failure behaviour

- Missing input data: show `unavailable`, lower confidence, never default silently.
- No feasible configuration: the planner says so and returns the nearest trade-off with its binding constraints.
- Verifier failure after retries: show "could not verify" with the raw ledgers. No brief.
- LLM or network error: the ledgers still render, since they come from the engine alone.
