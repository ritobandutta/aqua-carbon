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
    for phrase in ("The cost of cold", "A model explains. The engine counts.", "Straight answers.", "Ask who pays."):
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


# ---- the landing page may only state numbers the repo can back ----
def test_landing_stats_match_the_codebase():
    html = read("index.html")
    from engine.models import CoolingType
    assert f'data-stat="profiles"><i>{len(list(CoolingType))}</i>' in html

    nine = len(VALUE_STATUS)
    verified = sum(1 for v in VALUE_STATUS.values() if v == "published")
    assert f'data-stat="verified-inputs"><i>{verified}</i>/{nine}' in html, \
        "landing page's verified-inputs stat is out of date with VALUE_STATUS"

    # catch-rate stat comes from the real eval, not from memory
    from evals.run_evals import eval_verifier_catch_rate
    r = eval_verifier_catch_rate()
    assert f'data-stat="verifier-catch"><i>{r["detected_failures"]}</i>/{r["total_injected_checks"]}' in html, \
        "landing page's verifier stat is out of date with the eval suite"
    assert r["detected_failures"] == r["total_injected_checks"]


def test_landing_page_makes_no_claims_the_project_cannot_support():
    text = re.sub(r"<[^>]+>", " ", read("index.html")).lower()
    negations = ("not ", "no ", "never ", "n't ", "without ")
    for banned in ("zero hallucination", "guaranteed", "cryptographic", "verified savings", "real-time control"):
        for m in re.finditer(re.escape(banned), text):
            window = text[max(0, m.start() - 70):m.start()]
            assert any(n in window for n in negations), f"affirmative claim of '{banned}': ...{text[max(0, m.start()-50):m.end()+20]}..."
    assert "illustrative" in text and "modelled" in text
