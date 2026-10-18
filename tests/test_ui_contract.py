"""The UI is static HTML plus JS, so a rename or a stale template breaks it silently. These tests pin the contract
between the pages, the scripts, the stylesheet and the API, and keep the landing page's numbers true."""

import re
import pathlib
import pytest
from fastapi.testclient import TestClient
from api.main import app
from engine.data_sources import VALUE_STATUS

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
client = TestClient(app)
read = lambda n: (STATIC / n).read_text(encoding="utf-8")


def test_routes_serve_the_right_pages():
    land, wb = client.get("/"), client.get("/app")
    assert land.status_code == 200 and "The cost of cold" in land.text and 'id="hero-canvas"' in land.text
    assert wb.status_code == 200 and 'id="btn-recalculate"' in wb.text and "Workbench" in wb.text
    assert land.text != wb.text
    for asset in ("style.css", "landing.css", "landing.js", "app.js"):
        assert client.get(f"/static/{asset}").status_code == 200, asset


def test_every_id_app_js_looks_up_exists_in_the_workbench():
    js, html = read("app.js"), read("app.html")
    wanted = set(re.findall(r'getElementById\("([^"]+)"\)', js))
    present = set(re.findall(r'id="([^"]+)"', html))
    missing = sorted(wanted - present)
    assert not missing, f"app.js looks up ids that app.html does not define: {missing}"


def test_every_id_landing_js_looks_up_exists_on_the_landing_page():
    js, html = read("landing.js"), read("index.html")
    wanted = set(re.findall(r'\$\("#([\w-]+)"\)', js))
    present = set(re.findall(r'id="([^"]+)"', html))
    assert not (wanted - present), sorted(wanted - present)
    assert {c for c in re.findall(r'data-viz="(\w+)"', html)} == {"wave", "grid", "stems", "ring"}


def test_tabs_and_panels_match_one_to_one():
    html = read("app.html")
    tabs = re.findall(r'data-tab="(\w+)"', html)
    panels = re.findall(r'id="tab-(\w+)"', html)
    assert tabs and sorted(tabs) == sorted(panels)


def test_landing_anchor_links_resolve():
    html = read("index.html")
    ids = set(re.findall(r'id="([^"]+)"', html))
    for target in re.findall(r'href="#([\w-]+)"', html):
        assert target in ids, target
    # deep link into a workbench tab exists
    for tab in re.findall(r'href="/app#(\w+)"', html):
        assert f'data-tab="{tab}"' in read("app.html"), tab


def test_every_class_the_scripts_emit_is_styled():
    css = read("style.css") + read("landing.css")
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    emitted = set()
    for name in ("app.js", "landing.js"):
        for m in re.finditer(r'class="([^"$]*)', read(name)):
            emitted.update(m.group(1).split())
        for m in re.finditer(r'classList\.(?:add|toggle|remove)\("([\w-]+)"', read(name)):
            emitted.add(m.group(1))
    # headline word/glyph spans are styled under .headline; bar-row and actions-box are structural wrappers with no
    # visual rule of their own; "conf-" is the stem of a template string (conf-${level}), whose real classes are styled.
    ignore = {"w", "g", "bar-row", "actions-box", "conf-"}
    unstyled = sorted(c for c in emitted if c not in defined and c not in ignore)
    for level in ("high", "medium", "low", "unavailable"):
        assert f"conf-{level}" in defined, f"confidence level conf-{level} has no style"
    assert not unstyled, f"classes emitted by JS but never styled: {unstyled}"


def test_design_rules_hold_in_the_stylesheets():
    for name in ("style.css", "landing.css"):
        css = read(name)
        assert "box-shadow" not in css.replace("/* ", ""), f"{name}: no drop shadows or glow boxes"
        radii = re.findall(r"border-radius:\s*([^;}]+)", css)
        assert all(r.strip() == "0" for r in radii), f"{name}: radii are 0 everywhere, found {radii}"
        assert not re.search(r"font-weight:\s*(500|600|700|800|900|bold)", css), f"{name}: Inter 300/400 only"
    assert re.search(r"border-radius:\s*0", read("style.css")), "the global reset must zero radii"
    # gradients: only the single functional veil that protects hero legibility
    grads = re.findall(r"(linear|radial)-gradient", read("style.css") + read("landing.css"))
    assert len(grads) == 2, f"expected only the hero veil's two gradients, found {len(grads)}"
    assert "linear-gradient" in read("landing.css").split(".veil")[1].split("}")[0]


def test_no_bitmap_images_and_no_inline_styles_in_templates():
    for name in ("index.html", "app.html", "app.js"):
        src = read(name)
        assert not re.search(r"<img\b|\.(png|jpe?g|gif|webp)\b", src), name
        assert 'style="' not in src, f"{name}: use classes, not inline styles"
    assert not re.search(r"#[0-9a-fA-F]{6}\b", read("app.js")), "no hard-coded colours in app.js"


def test_reduced_motion_is_handled_everywhere():
    assert "prefers-reduced-motion" in read("style.css") and "prefers-reduced-motion" in read("landing.css")
    land_js = read("landing.js")
    assert "prefers-reduced-motion: reduce" in land_js and "reduced" in land_js
    assert "display: none !important" in read("landing.css").split("prefers-reduced-motion")[-1]


def test_landing_page_has_no_dead_ends_without_javascript():
    """The content must exist in the markup; JS only adds motion. (html.js is what hides things, and it is set by JS.)"""
    html = read("index.html")
    for phrase in ("The cost of cold", "A model explains. The engine counts.", "Questions, answered.", "Ask who pays."):
        assert phrase in html
    css = read("landing.css")
    assert re.search(r"html\.js[^{]*\.rv", css), "reveal hiding must be scoped to html.js"
    assert re.search(r"html\.js[^{]*\.intro", css), "intro stage must be scoped to html.js"


def test_headings_are_ordered_and_pages_have_one_h1():
    for name in ("index.html", "app.html"):
        html = read(name)
        assert len(re.findall(r"<h1\b", html)) <= 1
    assert len(re.findall(r"<h1\b", read("index.html"))) == 1
    assert 'lang="en"' in read("index.html") and 'lang="en"' in read("app.html")


# ---- the landing page may only state numbers and capabilities the repo can back ----
def test_landing_stats_match_the_codebase():
    html = read("index.html")
    from engine.models import CoolingType
    from engine.data_sources import REGIONAL_PROFILES
    from engine.arbiter import simulate_24h_arbiter
    from engine.models import ScenarioInput
    assert f'data-stat="profiles"><i>{len(list(CoolingType))}</i>' in html
    assert f'data-stat="cities"><i>{len(REGIONAL_PROFILES)}</i>' in html
    hours = len(simulate_24h_arbiter(ScenarioInput(region="bengaluru"), 40.0).hourly_steps)
    assert f'data-stat="hours"><i>{hours}</i>' in html
    # every city named on the page is a supported region, and every supported region is named
    for city in ("Bengaluru", "Chennai", "Mumbai"):
        assert city in html
    assert {c.lower() for c in ("Bengaluru", "Chennai", "Mumbai")} == set(REGIONAL_PROFILES)


def test_spectrum_chart_plots_the_real_model_output():
    import json
    from engine.arbiter import simulate_24h_arbiter
    from engine.models import ScenarioInput, Season
    shown = json.loads(re.search(r"const TEMPS = (\[[^\]]+\]);", read("landing.js")).group(1))
    model = [s.ambient_temp_c for s in simulate_24h_arbiter(
        ScenarioInput(region="bengaluru", it_capacity_mw=15.0, season=Season.ANNUAL_AVERAGE), 40.0).hourly_steps]
    assert shown == model, "landing.js TEMPS drifted from the dispatch model; regenerate it from engine/arbiter.py"


def test_highlighted_window_is_the_one_the_dispatch_model_defers():
    """The chart marks 12:00-17:00. The model must actually shift flexible load in exactly those hours."""
    from engine.arbiter import simulate_24h_arbiter
    from engine.models import ScenarioInput, Season
    steps = simulate_24h_arbiter(ScenarioInput(region="bengaluru", it_capacity_mw=15.0, season=Season.ANNUAL_AVERAGE), 40.0).hourly_steps
    deferred = [s.hour for s in steps if "CooL-LLM" in s.cooling_mode]
    js = read("landing.js")
    sel0, sel1 = (int(x) for x in re.search(r"SEL0 = (\d+), SEL1 = (\d+)", js).groups())
    bars = int(re.search(r"BARS = (\d+)", js).group(1))
    assert (sel0 * 24 // bars, sel1 * 24 // bars) == (min(deferred), max(deferred) + 1) == (12, 17)


def test_landing_capabilities_exist_in_the_product():
    html, wb = read("index.html"), read("app.html")
    # what-if controls named in the FAQ
    for control in ("preset-selector", "season-selector", "workload-selector", "capacity-slider", "grid-slider"):
        assert f'id="{control}"' in wb
    # planner, claim review, coverage, dispatch, briefs all have a tab
    for tab in ("planner", "review", "coverage", "arbiter", "briefs"):
        assert f'data-tab="{tab}"' in wb
    # the three designs named on the page are the three the engine models
    for phrase in ("evaporative towers", "air-cooled chillers", "hybrid adiabatic coolers"):
        assert phrase in html
    # the seasons the page names exist in the model
    from engine.models import Season
    assert {"dry_summer", "monsoon"} <= {x.value for x in Season}


def test_landing_page_makes_no_claims_the_project_cannot_support():
    text = re.sub(r"<[^>]+>", " ", read("index.html")).lower()
    negations = ("not ", "no ", "never ", "n't ", "without ")
    for banned in ("zero hallucination", "guaranteed", "cryptographic", "verified savings", "real-time control",
                   "certified", "validated digital twin", "live telemetry"):
        for m in re.finditer(re.escape(banned), text):
            window = text[max(0, m.start() - 70):m.start()]
            assert any(n in window for n in negations), f"affirmative claim of '{banned}': ...{text[max(0, m.start()-50):m.end()+20]}..."


def test_landing_page_carries_no_status_or_caveat_copy():
    """Disclosures live in the deck. The page reads like the finished product."""
    text = re.sub(r"<[^>]+>", " ", read("index.html")).lower()
    for phrase in ("illustrative", "not yet", "unverified", "not proven", "work in progress", "prototype", "hackathon",
                   "draft", "coming soon", "placeholder", "synthetic"):
        assert phrase not in text, f"status/caveat wording on the landing page: '{phrase}'"
