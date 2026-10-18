"""Gemini-drafted briefs: model prose with engine placeholders, never model-typed metrics."""

import pytest
from agents.orchestrator import AgentOrchestrator
from agents.advisor_agent import build_fact_sheet, fill_placeholders, has_bare_metric_digits
from engine.calculator import evaluate_scenario
from engine.models import ScenarioInput

S = ScenarioInput(it_capacity_mw=15.0, region="bengaluru")
GOOD = ("Evaporative cooling reaches a PUE of {{evaporative.pue}} and uses {{evaporative.water}} a year, "
        "while dry cooling draws {{dry_cooling.energy}}. Data are unverified.")


def _run(monkeypatch, reply):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("VERIFIER_URL", raising=False)
    orch = AgentOrchestrator()
    monkeypatch.setattr(orch, "_call_gemini", lambda prompt: reply)
    return orch.process_scenario(S)


def test_placeholders_are_filled_from_the_engine():
    a = evaluate_scenario(S)
    facts = build_fact_sheet(a)
    out = fill_placeholders(GOOD, facts)
    assert f"{a['evaporative'].facility_ledger.pue:.2f}" in out and "{{" not in out


def test_unknown_placeholder_rejects_the_draft():
    assert fill_placeholders("{{evaporative.nonsense}}", build_fact_sheet(evaluate_scenario(S))) is None
    assert fill_placeholders("{{plasma.pue}}", build_fact_sheet(evaluate_scenario(S))) is None


def test_model_typed_metrics_are_detected():
    assert has_bare_metric_digits("PUE of 0.95 and {{evaporative.water}}")
    assert not has_bare_metric_digits(GOOD)


def test_faithful_model_is_used_and_verified(monkeypatch):
    out = _run(monkeypatch, GOOD)
    assert out["brief_sources"] == {"operator": "gemini", "community": "gemini"}
    assert "{{" not in out["briefs"]["operator_brief_markdown"]
    assert out["verification"]["status"] == "PASSED"


def test_model_that_types_its_own_numbers_falls_back_to_template(monkeypatch):
    out = _run(monkeypatch, "Evaporative cooling reaches a PUE of 0.99 and {{evaporative.water}}.")
    assert out["brief_sources"] == {"operator": "template", "community": "template"}
    assert out["verification"]["status"] == "PASSED"


def test_invented_field_falls_back_to_template(monkeypatch):
    out = _run(monkeypatch, "Cooling uses {{evaporative.magic}}.")
    assert out["brief_sources"]["operator"] == "template"


def test_no_key_uses_templates(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VERIFIER_URL", raising=False)
    assert AgentOrchestrator().process_scenario(S)["brief_sources"] == {"operator": "template", "community": "template"}
