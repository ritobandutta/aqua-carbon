"""
Planner Agent for AquaCarbon DC — Commons Edition (v2).
Executes constraint-aware optimization across facility engineering limits
and community commons boundaries. Rejects infeasible scenarios transparently.
"""

from typing import Dict, Any
from engine.models import ScenarioInput, PlannerConstraints, PlannerOutput
from engine.calculator import run_constraint_planner


class PlannerAgent:
    """
    Evaluates scenario feasibility against joint operator and community constraints.
    """

    def plan_configurations(
        self,
        scenario: ScenarioInput,
        constraints: PlannerConstraints
    ) -> PlannerOutput:
        return run_constraint_planner(scenario, constraints)
