"""Basic Polymorphic-Twin usage example.

Demonstrates creating an engine with default configuration and
validating a simple temperature constraint.
"""
import asyncio

from polytwin import EngineConfig, PolymorphicTwinEngine, ValidationResult


async def main() -> None:
    # Create engine with default config
    config = EngineConfig()
    engine = PolymorphicTwinEngine(config)

    # Validate a simple temperature constraint
    result: ValidationResult = await engine.validate(
        state_values={"temperature": 150.0},
        constraint_cards=[
            {
                "constraint_id": "temp_limit",
                "scenario_criticality": "safety_critical",
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "temperature", "max": 180.0},
                },
                "domain_of_validity": {"conditions": [], "match_mode": "all"},
            }
        ],
    )
    print(f"Validation: passed={result.passed}, count={result.evaluated_count}")

    # Test with an out-of-range value (should fail and trigger safety fallback)
    result_fail: ValidationResult = await engine.validate(
        state_values={"temperature": 200.0},
        constraint_cards=[
            {
                "constraint_id": "temp_limit",
                "scenario_criticality": "safety_critical",
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "temperature", "max": 180.0},
                },
                "domain_of_validity": {"conditions": [], "match_mode": "all"},
            }
        ],
    )
    print(
        f"Validation: passed={result_fail.passed}, "
        f"safety_fallback={result_fail.safety_fallback_triggered}"
    )


if __name__ == "__main__":
    asyncio.run(main())
