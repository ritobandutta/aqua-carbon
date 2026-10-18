# Open Questions and Verify-Before-Building

From v2 section 13 plus items raised during planning. Do these in Phase 0, before writing engine code. Record each answer here with a date.

## Blocking

- [ ] **Eligibility.** The v2 doc says the site states this edition is for working professionals and that students are not eligible. Confirm both collaborators qualify and whether employer IP or conflict-of-interest rules apply. Check this before building on a company laptop.
- [ ] **Deadline and deliverables.** Submission date, required artifacts (demo video, repo link, write-up, deployed URL), judging format.
- [ ] **Commit identity.** Decide the author name and email for all commits. Only the initial README commit carries the office email today (see `CONTRIBUTING.md`).
- [ ] **Employer policy.** Confirm side projects on a company machine are allowed, and that no company data, code or credentials are used.

## Technical verification

- [ ] **Model IDs and quotas.** Current Gemini Flash and Pro IDs, Gemma availability, fine-tuning options on Vertex AI, free-tier rate limits on AI Studio. Fill `MODEL_FLASH` and `MODEL_PRO` in `.env.example` afterwards.
- [ ] **SDK versions.** ADK, A2A and MCP Python SDKs: current versions, compatibility, and whether ADK supports A2A as a client and server the way the plan assumes.
- [ ] **Datasets, access and licence.** First pass done 2026-10-18 (`DATA_SOURCES.md`, `data/sources.yaml`): licences read for Open-Meteo, GHSL, LBNL. Still open: open the official CEA, KERC, BWSSB, CGWB and CPHEEO files and record page and cell.
- [ ] **Cooling profiles.** Locate published relationships (for example Karimi et al. 2022, ASHRAE) and decide which two profiles the engine can support credibly. Likely an evaporative tower with a water-cooled chiller, against an air-cooled chiller or dry cooler.
- [ ] **Prior-art pass.** Re-check integrated cooling-plus-community tools, including recent launches. The pitch claim is "integrated, agentic and confidence-aware", not "first ever".

## Product decisions still open

- [ ] Final list of community-ledger indicators (depends on dataset audit).
- [ ] Which season split to model: dry, monsoon, or three seasons.
- [ ] Regional language for the community brief (Kannada or Hindi) if we reach the stretch tier.
- [ ] Whether the community read-only view is a separate route or an export only.

## Deployment

- [ ] Who deploys: collaborator's personal GCP account, or the user's personal account.
- [ ] Budget cap and credits available for Vertex AI, Cloud Run and BigQuery.
- [ ] Web hosting: Firebase Hosting versus Cloud Run.

## Answers log

| Date | Question | Answer | Source |
|---|---|---|---|
| | | | |
