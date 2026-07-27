"""Lab exploration example.

Demonstrates running Lab exploration to find constraint boundary
violations and generate hypotheses about constraint behaviour.
"""
import asyncio

from polytwin import EngineConfig, PolymorphicTwinEngine
from polytwin.lab.types import ExplorationBudget


async def main() -> None:
    # Create engine with Lab enabled (default)
    config = EngineConfig(enable_lab=True)
    engine = PolymorphicTwinEngine(config)

    # Define constraints to explore
    constraints = [
        {
            "constraint_id": "pressure_limit",
            "scenario_criticality": "safety_critical",
            "validation": {
                "method": "range_check",
                "config": {"variable": "pressure", "min": 0.0, "max": 10.0},
            },
        },
        {
            "constraint_id": "temperature_limit",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "min": -10.0, "max": 100.0},
            },
        },
    ]

    # Prepare exploration data
    data = {
        "state_variables": {"pressure": 5.0, "temperature": 45.0},
    }

    # Run full exploration with a budget
    budget = ExplorationBudget(max_iterations=50, max_seconds=5.0)
    result = await engine.run_exploration(data, constraints, budget)

    print(f"Exploration findings: {len(result.findings)}")
    print(f"Counterexamples found: {len(result.counterexamples)}")
    print(f"Hypotheses generated: {len(result.hypotheses)}")
    print(f"Strategy: {result.strategy_manifest.get('strategy', 'unknown')}")

    # Show counterexample details
    for ce in result.counterexamples[:3]:
        print(f"  Counterexample: {ce.constraint_violated} at state {ce.state_at_failure}")


if __name__ == "__main__":
    asyncio.run(main())
