# Workstreams

The split between collaborators is **undecided**. Work is organized by workstream with explicit interfaces, so any assignment works. Put names in the Owner column when decided.

| # | Workstream | Scope | Depends on | Hands off to | Owner |
|---|---|---|---|---|---|
| A | Engine and data | `engine/`, `data/`: profiles, hourly sim, ledgers, uncertainty, planner search, golden and property tests, `sources.yaml` | Phase 0 research | B, C, D via `RunResult` | TBD |
| B | Services and agents | `services/*`: FastAPI, ADK agents, MCP server, A2A verifier and community services, store adapter | A's contracts | D via OpenAPI | TBD |
| C | Evals | `evals/`: fidelity, verifier catch-rate, planner cases, stability, cost and latency report | A, B | report in `docs/` | TBD |
| D | Web | `web/`: scenario builder, comparison, burden bars, chat, what-if, coverage, export | B's OpenAPI schema | demo | TBD |
| E | Research and data audit | `docs/DATA_SOURCES.md`, coefficient sourcing, prior-art pass, organizer questions | none | A | TBD |
| F | Infra and deploy docs | `infra/`, `docs/DEPLOYMENT.md`, CI, compose | B | deploy day | TBD |

## Interfaces to agree first

These contracts unblock parallel work. Agree and freeze them in Phase 1, before building behind them.

1. **`Quantity` / `Unavailable`** shapes (`ARCHITECTURE.md`). Everyone depends on it.
2. **`Scenario` and `RunResult`** schemas, so web and agents can use fixtures before the engine is done.
3. **OpenAPI surface** of the api: scenarios, runs, diff, brief, chat stream.
4. **MCP tool signatures** for the engine and data lookups.
5. **A2A message shapes** for the verifier and community services.

## Suggested splits

- **Two people, balanced:** one takes A + C + E (engine, evals, research), the other takes B + D + F (services, web, infra).
- **Engine-first pairing:** both work on A and E in Phase 0 to 2, then split B and D from Phase 3.

## Working rhythm

- Short sync at the start of each phase: what ships, who owns what, any contract change.
- A contract change needs an ADR and a heads-up before merge.
- Use fixtures for `RunResult` so web and agent work never waits on the engine.
