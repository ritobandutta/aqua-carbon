"""
AquaCarbon DC: Deterministic Calculation CLI Demo
Grounded in Karimi et al. (2022) and WRI Aqueduct baselines.
"""

from engine.core import AquaCarbonEngine, CoreScenarioInput

if __name__ == "__main__":
    scenario = CoreScenarioInput()
    engine = AquaCarbonEngine(scenario)
    
    print("=== EVAPORATIVE (WET) COOLING ===")
    print(engine.calculate_profile("evaporative"))
    print("\n=== DRY (AIR-COOLED) COOLING ===")
    print(engine.calculate_profile("dry"))
    print("\n=== HYBRID ADIABATIC COOLING ===")
    print(engine.calculate_profile("hybrid"))
