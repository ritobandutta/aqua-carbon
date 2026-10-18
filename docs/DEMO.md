# Demo Script

Runs from a clean clone with no API key (deterministic mode). Add `GEMINI_API_KEY` to `.env` to see live Gemini answers in step 5. Everything else is identical.

## Setup (once)

```bash
make setup
cp .env.example .env      # optional: add GEMINI_API_KEY
make check                # tests + evals, should all pass
make run                  # http://127.0.0.1:8000  (set PORT=8010 if 8000 is busy)
```

## Narrative (about 5 minutes)

1. **The gap.** "PUE alone cannot show who bears the cost of a cooling choice." Open the app. Preset: Bengaluru, 15 MW. Say out loud that facility inputs are illustrative.
2. **Compare.** Three profiles side by side. Facility ledger first (PUE, WUE, energy, water, carbon, cost), then the community ledger, then the burden bars. Point out there is no combined score.
3. **Honest data.** In the community ledger, every indicator shows a confidence chip and a source label. Most read **LOW** and "illustrative, not yet verified". Say why: the values have not been traced to a source yet, and the tool says so instead of showing false confidence. Open the coverage panel: satellite built-up area is 1.83x the official piped footprint, and the water-headroom indicator is lowered because of it.
4. **Planner refusal.** Set max PUE 1.15 and max water 10 ML. Nothing is feasible. Show that the tool refuses, names the binding constraint and the closest profile, instead of inventing a compromise. Then relax a limit and show a feasible set.
5. **Investigate.** Ask "Why does dry cooling save water but strain the grid?". Show the answer and the verifier digest. With a key set, the draft is Gemini's and is blocked if any number fails the check.
6. **Tamper demo.** Click the tamper button: a corrupted brief is caught and publication is blocked.
7. **What-if.** Switch season from winter to dry summer at the same limits. The feasible set changes (evaporative drops out). Say what flipped and why.
8. **Close.** Run the evals from the header. Then state limitations: annual multipliers, not an hourly simulation; regional values pending the dataset audit; modelled potential impact, not measured savings; any real deployment needs qualified engineering review.

## Optional: show the separate verifier

```bash
make run-verifier        # terminal 1
make run-split           # terminal 2
```
Open the app: the line above the brief reads `Verifier: remote`. Stop the verifier and re-run: the brief is blocked and shows `UNVERIFIED:verifier_unreachable`. The tool refuses to show output it could not check.

## Things not to claim

- That numbers are sourced or verified before `docs/DATA_SOURCES.md` says so.
- "Zero hallucination". The verifier checks numbers that carry a unit, not every statement.
- ADK, MCP or A2A. The agents are plain classes; the verifier can run as a separate HTTP service, which is not the A2A protocol.
- That the uncertainty ranges are confidence intervals. They are sensitivity ranges around unverified inputs.
- Measured savings. Everything is modelled.
