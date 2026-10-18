# AquaCarbon DC — Agent & Contributor Context

Single source of truth for anyone (human or AI coding assistant) working in this repo. `CLAUDE.md` imports this file.

## What this is

AquaCarbon DC (Commons Edition) is a hackathon project for the AI Builder Cup (Sustainability & Social Impact). It compares 2–3 data-center cooling configurations for one site and workload, and produces two ledgers from the same scenario:

- **Facility ledger**: energy, PUE, direct water, WUE, carbon, cost.
- **Community ledger**: who absorbs the burden (water headroom, groundwater stress, grid peak, carbon, vulnerability context), with source, resolution and confidence on every indicator.

Read `docs/PLAN.md` for the build plan and `docs/product/` for the original v1 and v2 product documents.

## Status

**Planning only. No code has been written yet.** Do not scaffold or build until the team starts Phase 1 of `docs/PLAN.md`. Phase 0 (verify-before-building) comes first, see `docs/OPEN_QUESTIONS.md`.

## Hard rules (non-negotiable)

1. **The deterministic engine is the only source of numbers.** LLMs plan, explain and verify. They never invent measurements, emission factors, cooling coefficients or any other figure.
2. **Missing data is `unavailable`.** Never silently replace it with a default.
3. **Every displayed metric carries units, boundary, source, geographic resolution and confidence.**
4. **No single combined score.** Show water, power and carbon burdens side by side.
5. **Results are modelled potential impact, not measured savings.** Say so wherever results appear.
6. **Synthetic facility inputs are always labelled "Illustrative".**
7. **Area-level only.** Never identify individuals or households.
8. **The verifier must be independent of the advisor.** Separate service, separate process.
9. **No secrets in git.** Use `.env` locally (git-ignored) and Secret Manager in the cloud.
10. **No company infrastructure or accounts.** Cloud deployment happens later from a personal GCP account.

## Planned layout

```
engine/      pure Python package (no I/O, no LLM): cooling profiles, hourly sim, ledgers, planner
data/        curated datasets + sources.yaml provenance registry
services/    api (FastAPI + ADK), engine_mcp, verifier (A2A), community (A2A)
web/         Next.js App Router + Tailwind + shadcn
evals/       fidelity, verifier catch-rate, planner and stability harness
docs/        plan, architecture, decisions, deployment, data sources
infra/       Dockerfiles, compose, Cloud Run and BigQuery definitions
```

## Conventions

- Python: `uv` workspace, ruff, pyright, pytest (plus hypothesis for property tests).
- Web: pnpm, TypeScript strict. API types are generated from the FastAPI OpenAPI schema, never hand-written.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`).
- Architectural decisions go in `docs/DECISIONS.md` as a new ADR.
- Update `docs/DEPLOYMENT.md` in the same PR as anything that changes how the system is deployed.
- Terms: see `docs/GLOSSARY.md`.

## Where to look

| Need | File |
|---|---|
| Build plan and phases | `docs/PLAN.md` |
| How the pieces fit | `docs/ARCHITECTURE.md` |
| Why we chose X | `docs/DECISIONS.md` |
| Who builds what | `docs/WORKSTREAMS.md` |
| Unresolved items | `docs/OPEN_QUESTIONS.md` |
| Datasets and licences | `docs/DATA_SOURCES.md` |
| Deploying to GCP | `docs/DEPLOYMENT.md` |
| Original product docs | `docs/product/` |
