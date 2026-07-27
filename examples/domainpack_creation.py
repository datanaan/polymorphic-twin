"""DomainPack creation and loading example.

Demonstrates how to create a DomainPack programmatically,
register it with the engine, and list available DomainPacks.
"""
import asyncio

from polytwin import DomainPack, EngineConfig, PolymorphicTwinEngine
from polytwin.domainpack.types import (
    ConstraintCard,
    DomainOfValidity,
    SafeFallback,
    StateVariable,
    ValidationConfig,
)


async def main() -> None:
    # Create a custom DomainPack programmatically
    pack = DomainPack(
        domain_id="custom-reactor-001",
        domain_name="Custom Chemical Reactor",
        domain_version="0.1.0",
        state_semantics_template={
            "variables": [
                {
                    "name": "temperature",
                    "physical_meaning": "Reactor core temperature",
                    "unit": "degC",
                    "range_min": 0.0,
                    "range_max": 500.0,
                    "observability": "direct",
                    "controllability": "indirect",
                }
            ]
        },
        constraint_cards={
            "temp_upper_limit": {
                "constraint_id": "temp_upper_limit",
                "scenario_criticality": "safety_critical",
                "domain_of_validity": {"conditions": [], "match_mode": "all"},
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "temperature", "max": 450.0},
                },
            }
        },
        safe_fallback=SafeFallback(
            policy_id="reactor-safe-shutdown",
            target_state={"temperature": 25.0},
        ),
    )

    # Create engine and load DomainPacks
    config = EngineConfig(domain_pack_dirs=[])
    engine = PolymorphicTwinEngine(config)

    # The engine's internal registry is not directly accessible,
    # but DomainPacks loaded from configured directories are available via:
    print(f"Loaded DomainPacks: {engine.list_domain_packs()}")

    # Validate using the custom DomainPack's constraint cards
    constraint_dicts = list(pack.constraint_cards.values())
    result = await engine.validate(
        state_values={"temperature": 300.0},
        constraint_cards=constraint_dicts,
    )
    print(f"Validation with custom DomainPack: passed={result.passed}")

    # Check variables defined in the DomainPack
    print(f"State variables: {[v.name for v in pack.variables]}")
    print(f"Variable names: {pack.variable_names}")


if __name__ == "__main__":
    asyncio.run(main())
