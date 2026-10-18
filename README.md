# AquaCarbon DC — Commons Edition

Every data-center cooling choice moves a burden somewhere: onto the local water system, onto the power grid, or into the atmosphere. AquaCarbon DC makes that shift visible to both sides of the decision, the operator who picks the cooling strategy and the community that lives with the consequences, and is honest about where the data runs out.

Built for the **AI Builder Cup — Sustainability & Social Impact**.

> **Status: planning.** No code yet. Start with [`docs/PLAN.md`](docs/PLAN.md).

## The idea in 30 seconds

Compare 2–3 cooling configurations for the same site and workload. For each one, the deterministic engine computes:

- a **facility ledger**: energy, PUE, direct water, WUE, carbon, cost
- a **community ledger**: water headroom, groundwater stress, grid peak, carbon intensity, vulnerability context, each with source, resolution and confidence
- a **burden-shifting view**: water, power and carbon side by side, with no single combined score

Gemini agents (built with Google ADK) plan, explain and answer what-ifs. An independent verifier agent checks every number in a brief against engine output before the user sees it.

**Design principle:** the calculation engine is the only source of numbers. AI never invents measurements, factors or coefficients. Missing data shows as `unavailable`.

## Docs

| Doc | What it covers |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | Full build plan, phases, verification |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, data flow, trust boundaries, contracts |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architecture decision records |
| [`docs/WORKSTREAMS.md`](docs/WORKSTREAMS.md) | Workstreams and interfaces, so work can be split |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Verify-before-building checklist |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Dataset audit tracker |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | GCP deployment guide (grown per phase) |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | PUE, WUE, CoC and other terms |
| [`docs/product/`](docs/product/) | Original v1 overview (PDF) and v2 Commons Edition (docx) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Workflow, conventions, definition of done |
| [`AGENTS.md`](AGENTS.md) | Context for AI coding assistants (`CLAUDE.md` imports it) |

## Getting started

Nothing to run yet. Once Phase 1 lands, the goal is: clone, `cp .env.example .env`, add a Gemini API key, `make dev`.
