# Contributing

Two people, one hackathon. Keep it lightweight but predictable.

## Before your first commit

Set a repo-local git identity so commits carry the author you intend. This does not touch your global git config:

```bash
git config user.name  "<your name>"
git config user.email "<email you want on commits>"
git config --local --list | grep user
```

Author metadata is baked into every commit permanently, and it survives repo transfers. Check it first.

## Workflow

- `main` is always working and demo-able.
- Branch from `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
- Open a PR for every change. The other person reviews unless it is a docs-only typo fix.
- Keep PRs small, ideally under 400 changed lines.
- Squash-merge, so `main` history stays readable.
- If the plan changes, update `docs/PLAN.md` in the same PR. If an architectural choice changes, add an ADR to `docs/DECISIONS.md`.

## Commit messages

Conventional Commits: `type(scope): summary`.

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
Examples: `feat(engine): add evaporative tower water model`, `docs: add dataset audit for Aqueduct`.

## Definition of done

- Tests pass: unit, property and (for agents) eval cases.
- New engine behaviour has a test. Coefficients cite a source in `data/sources.yaml`.
- Displayed metrics carry units, boundary, source, resolution and confidence.
- Docs updated, including `docs/DEPLOYMENT.md` if deployment changes.
- No secrets, no real facility data, no personal data.
- Nothing numeric comes from an LLM. See `AGENTS.md` hard rules.

## Rules of thumb

- **Engine first.** UI and agents consume engine output. They never compute metrics.
- **Honest data.** Prefer showing `unavailable` and low confidence over a plausible default.
- **Cite everything.** Every coefficient, factor and dataset has an entry in `data/sources.yaml` (id, URL, licence, resolution, accessed date).
- **Label synthetic data** as "Illustrative" in code, data files and UI.
- **Decisions in writing.** Short ADRs beat long chat threads.

## Secrets

- Never commit `.env`, keys, tokens or service-account JSON. `.gitignore` covers the common ones. Check `git status` before committing.
- Use `.env.example` for placeholders only.
- If a secret is committed, rotate it immediately. Deleting the commit is not enough.

## Branch protection (recommended)

If the repo plan allows it, enable on `main`: require PR before merging, require 1 approval, require CI to pass, block force pushes.
