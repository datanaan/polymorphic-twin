"""Bridge decision interface example.

Demonstrates generating a structured action space from TwinObject
view data for human decision makers.
"""
import asyncio

from polytwin import BridgeOutput, EngineConfig, PolymorphicTwinEngine


async def main() -> None:
    # Create engine with Bridge enabled (default)
    config = EngineConfig(enable_bridge=True)
    engine = PolymorphicTwinEngine(config)

    # Prepare view data (simulating a BridgeDecisionView projection)
    view_data = {
        "twin_object_id": "device-pump-001",
        "constraint_state": {
            "active_constraints": ["pressure_limit", "temperature_limit"],
        },
        "constraint_summary": [
            {"constraint_id": "pressure_limit", "status": "failed"},
            {"constraint_id": "temperature_limit", "status": "passed"},
        ],
    }

    # Generate action space
    output: BridgeOutput = await engine.get_action_space(view_data)

    print(f"BridgeOutput ID: {output.output_id}")
    print(f"Object ID: {output.object_id}")
    print(f"Valid until: {output.valid_until}")
    print(f"Version tag: {output.version_tag}")

    # Inspect the four-category action space
    space = output.action_space
    print(f"\nImmediate actions: {len(space.immediate_actions)}")
    for action in space.immediate_actions:
        print(f"  - {action.action_type}: {action.description}")

    print(f"\nConditional actions: {len(space.conditional_actions)}")
    for action in space.conditional_actions:
        print(f"  - {action.action_type}: {action.description}")

    print(f"\nForbidden actions: {len(space.forbidden_actions)}")
    for action in space.forbidden_actions:
        print(f"  - {action.action_type}: {action.prohibition_reason}")

    print(f"\nUndetermined actions: {len(space.undetermined_actions)}")
    for action in space.undetermined_actions:
        print(f"  - {action.action_type}: {action.description}")


if __name__ == "__main__":
    asyncio.run(main())
