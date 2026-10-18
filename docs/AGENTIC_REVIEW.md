# Permit Claim Review (ADK + MCP + A2A)

A second use case built on the same engine. An applicant states figures ("the hybrid system will use 40 ML of water a year"). The tool compares each figure with the engine's modelled low/central/high range for the same site and workload, and produces a short list of questions for a permitting body or community group to ask.

It is a prompt for questions, not a finding of fault. The modelled inputs are illustrative and unverified (see `DATA_SOURCES.md`), and every result says so.

## Why each protocol is here

| Protocol | Job | Why not a plain function call |
|---|---|---|
| **MCP** (`mcp_server/`) | Exposes the engine as typed tools: `check_applicant_claim`, `modelled_range`, `compare_profiles`, `list_regions`, plus a `aquacarbon://sources` resource. The reviewer agent calls these instead of computing anything. | Any MCP client (not just this app) can ask the engine for numbers, with a typed contract and readable errors. |
| **ADK** (`review/service.py`) | Runs two agents: a claim extractor (structured output) and a reviewer with the MCP toolset. Also hosts the A2A client and server. | Agent loop, tool plumbing and A2A glue come from the framework. |
| **A2A** (`a2a_verifier/`) | Sends the finished review to an independent verifier process. | The agent that checks the reviewer must not share its code, prompt or reasoning. A separate process is a real boundary. |

## Rule kept: the model never produces a number

- The extractor returns claims. The verifier proves each claimed figure appears in the applicant's text, so an invented claim is blocked.
- The reviewer agent only calls `check_applicant_claim`. The verifier recomputes every verdict itself and compares, so a model that changes an argument or skips a call is blocked.
- The review text is rendered by code from the verdict rows. Any unit-tagged number in it must trace to the engine, a modelled-range bound, or a proven applicant figure.
- If the verifier is configured but unreachable, the review is **withheld** (fails closed).

## Modes

- **structured**: you supply claims. MCP tools are called directly. No model is involved. This is what the UI's "Check this figure" does, and it works with no API key.
- **agentic**: you supply application text. A Gemini-backed ADK agent extracts claims, then an ADK agent with the MCP toolset checks each one. Needs `GEMINI_API_KEY` (or Vertex settings).

## Run it

```bash
pip install -r requirements-agents.txt     # Python >= 3.11 (google-adk requires it)
make run-mcp                               # MCP server    :8200  (optional)
make run-a2a                               # A2A verifier  :8300  (optional)
MCP_URL=http://127.0.0.1:8200 A2A_VERIFIER_URL=http://127.0.0.1:8300 make run
```

With neither URL set, the MCP tools run in memory and verification runs in-process; the response's `provenance` field says which was used. The A2A agent card advertises `A2A_PUBLIC_HOST/PORT/PROTOCOL`; clients reject a card whose address is not the one they fetched it from, so set these to the address clients actually use.

API: `POST /api/review` with `{"scenario": {...}, "claims": [...]}` or `{"scenario": {...}, "applicant_text": "..."}`.

## What is and is not verified

Verified by tests (`tests/test_review_*.py`, `tests/test_a2a_independence.py`, `tests/test_claims.py`):
- structured mode through in-memory MCP, real MCP over HTTP, and a real A2A verifier process
- A2A down means blocked output
- an invented claim, tampered tool arguments, and a model that skips the tool are each blocked
- the verifier process loads no reviewer-side code and holds no model client

Container run (`docker-compose.review.yml`, `Dockerfile.review`, Python 3.12):
- The image builds, and all three services started.
- The first end-to-end call **failed**: the MCP server refused the Docker service name `mcp:8200` with `421 Invalid Host header`, because the SDK only trusts localhost Host headers by default.
- Fix: `MCP_ALLOWED_HOSTS` extends the allow-list while DNS-rebinding protection stays on. `tests/test_mcp_server.py` checks that an unknown host is still refused and an allow-listed one is accepted.
- **The rerun of the containers after that fix was not completed.** An automated safety check blocked the command in this session. So the fix is covered by a unit test, but the full containerised round trip has not been seen working. Run `docker compose -f docker-compose.review.yml up --build`, then POST to `/api/review` on port 8000, before relying on it.

Not verified:
- the agentic path against **real Gemini**. Tests use a scripted stand-in model, so wiring is tested but extraction quality is not
- the new UI tab in a browser (only the API route it calls is tested)
- deployment to GCP
- the verifier cannot judge whether the review's wording is fair, only that its figures are real

## Known limits

- ADK's A2A support is marked experimental by Google and may change.
- `google-adk` needs Python >= 3.11. The base app still runs on 3.10; only this feature needs the extras (`/api/review` returns 503 if they are missing).
- Importing ADK costs roughly 120 MB of memory, which matters on a 512 MiB Cloud Run instance. Deploy the review feature with at least 1 GiB, or as a separate service.
- The scripted test model and a real model may differ on tool-call behaviour; the verifier is what makes that safe.
