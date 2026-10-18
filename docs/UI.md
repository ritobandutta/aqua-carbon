# UI

Two pages share one visual system, inspired by a dark "generated light" landing-page style: near-black ground, one indigo accent, hairlines instead of cards, and imagery drawn in the browser.

| Route | File | What it is |
|---|---|---|
| `/` | `static/index.html`, `landing.css`, `landing.js` | Landing page: intro stage, WebGL ribbon hero, four canvas tiles, a spectrum field, stats, FAQ |
| `/app` | `static/app.html`, `app.js` | The workbench: seven tabs over the engine. `/app#review` opens a tab directly |
| both | `static/style.css` | Tokens, buttons, forms, and the whole workbench |

## Rules

- Ground `#0A0A0A`, ink white, one accent indigo `#6366F1`. Inter 300/400, JetBrains Mono 300 for all labels. Radii 0. No shadows, no bitmaps.
- Hairlines (`rgba(255,255,255,.10)`) carry structure. Grids use explicit track counts (4, then 2 at 1000px, then 1 at 560px), never auto-fit.
- **Status never relies on colour.** Solid outline means known, dashed means unverified, inverse (white fill) means failed or blocked. This is why the workbench has no red or green.
- Under `prefers-reduced-motion` the intro never runs, every animation stops, each canvas draws one still frame, and all content is visible.
- `tests/test_ui_contract.py` enforces: ids the scripts look up exist, every emitted class is styled, no shadows or inline styles or hard-coded colours, radii are 0, the only gradients are the hero veil, and reduced motion is handled.

## Honesty rules for copy

The landing page's numbers are tested against the codebase (profile count, the verifier's `14/14` from the real eval, and `0/9` verified inputs from `VALUE_STATUS`). If one of those changes, the test fails until the page is updated. The spectrum drawing is labelled as illustrative, not model output.

## Known deviations from the reference style

- The brief asks for at most six accent-coloured elements per page. The landing page has eight at rest: the wordmark word, two primary buttons, the selected spectrum band, and four stat numerals. The workbench uses more, because bars, slider thumbs and the active tab each mark state.
- The hero veil is the one gradient used, and only to keep type legible over bright ribbons.
- Contrast: palette muted `#71717A` is 4.1:1, so it is used only for decorative index numbers. Small informational text uses `#8E8E98` (6.1:1).

## Not verified

- Screenshots were taken in headless Chrome at 1440 and 390 wide. Other browsers, real devices, Safari's WebGL and a screen reader were not tried.
- The WebGL path ran (software-rendered). The canvas-2D fallback is written but was not exercised.
