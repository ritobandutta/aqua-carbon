# Decision Log (ADRs)

Newest last. Add a new entry for any change that is hard to reverse or affects both of us. Status is one of `accepted`, `proposed`, `superseded by ADR-N`.

Template:

```
## ADR-N: Title
Date: YYYY-MM-DD | Status: proposed
Context: why a decision is needed.
Decision: what we chose.
Consequences: what gets easier and harder.
```

---

## ADR-1: Deterministic engine is the only source of numbers
Date: 2026-10-17 | Status: accepted

**Context.** The product's credibility depends on never presenting invented figures. Both source documents state this principle.
**Decision.** All metrics come from a pure-Python engine with no I/O and no LLM. LLMs plan, explain and verify only.
**Consequences.** Everything numeric is testable and reproducible. Agents are constrained to structured hand-offs. Engine quality (sourced coefficients) becomes the main technical risk.

## ADR-2: Local-first build, cloud deployment later from a personal account
Date: 2026-10-17 | Status: accepted

**Context.** Development happens on a company laptop. Deployment will be done by the collaborator or from a personal GCP account.
**Decision.** Everything runs locally from compose with an AI Studio API key. The same code switches to Vertex AI and BigQuery through env vars and a store adapter. `DEPLOYMENT.md` is updated every phase.
**Consequences.** No cloud dependency during development. Cloud manifests must be kept in sync, or deployment day becomes a surprise.

## ADR-3: ADK for orchestration, with MCP for tools and A2A only across a trust boundary
Date: 2026-10-17 | Status: accepted

**Context.** v2 specifies ADK, MCP and A2A and warns against decorative technology.
**Decision.** ADK orchestrates agents. The engine and data sources are MCP tools. A2A is used only for the verifier and the community-impact service, where independence is real.
**Consequences.** Fewer moving parts than A2A everywhere. Each protocol has a stated reason.

## ADR-4: Drop Genkit and Firebase AI Logic. Defer Cube.js.
Date: 2026-10-17 | Status: accepted

**Context.** v2 lists Genkit for flows and tracing, and Firebase AI Logic for client-side Q&A. ADK already covers orchestration and evals, and Q&A over computed results can run through the api.
**Decision.** Do not adopt Genkit or Firebase AI Logic. Cube.js stays deferred as v2 already says.
**Consequences.** One agent framework to learn. We lose client-side Gemini calls, which we did not need. Revisit only if a concrete gap appears.

## ADR-5: Frontend is Next.js, Tailwind and shadcn, with a Python backend
Date: 2026-10-17 | Status: accepted

**Context.** UX is 10% of the score, and the interface needs charts, a streaming chat panel and a what-if drawer.
**Decision.** Next.js App Router with Tailwind, shadcn and Recharts. Backend stays Python. Types are generated from the FastAPI OpenAPI schema.
**Consequences.** Better polish than a notebook-style UI. Two languages, so the API contract must stay disciplined.

## ADR-6: No single combined score
Date: 2026-10-17 | Status: accepted

**Context.** A merged score would hide exactly the trade-off the product exists to show.
**Decision.** Show water, power and carbon burdens side by side, with binding constraints.
**Consequences.** Harder to rank at a glance. The planner uses constraints and a Pareto set, not a weighted sum.

## ADR-7: Gemma fine-tuning is gated on a measured baseline
Date: 2026-10-17 | Status: accepted

**Context.** v2 includes fine-tuned Gemma for document extraction but notes it should not be decorative.
**Decision.** Build a hand-labelled document set first. Fine-tune only if Flash falls short or cost and latency justify it, and record the result either way.
**Consequences.** Gemma may never ship. That is acceptable and will be stated in the submission.
