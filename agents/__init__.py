"""Agents package. Imports are lazy so that importing one agent (for example the verifier) does not pull in
the others. This matters for the verifier's independence: a verifier process must not load advisor,
orchestrator or planner code just because it imported agents.verifier_agent."""

_LAZY = {
    "ContextAgent": ".context_agent",
    "AdvisorAgent": ".advisor_agent",
    "VerifierAgent": ".verifier_agent",
    "PlannerAgent": ".planner_agent",
    "AgentOrchestrator": ".orchestrator",
}

__all__ = list(_LAZY)


def __getattr__(name):
    if name in _LAZY:
        import importlib
        return getattr(importlib.import_module(_LAZY[name], __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
