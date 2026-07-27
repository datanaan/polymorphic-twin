"""Main CLI entry point for polytwin-cli.

Defines the top-level Click group and global options (--version, --verbose, --quiet),
then delegates to submodules for individual commands.
"""
from __future__ import annotations

import sys

import click
from rich.console import Console

from polytwin import __version__

console = Console()
error_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__, prog_name="polytwin-cli")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose output.")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Suppress non-error output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Polymorphic-Twin Workbench CLI -- developer tools for DomainPack governance."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["console"] = console
    ctx.obj["error_console"] = error_console


# ── Inline commands (validate, init) ───────────────────────────────────


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, file: str) -> None:
    """Validate a DomainPack file through 3-level pipeline (syntax, semantic, compatibility)."""
    from polytwin.cli.validate import run_validate

    exit_code = run_validate(file, ctx.obj)
    sys.exit(exit_code)


@cli.command()
@click.argument("domain_pack_file", type=click.Path(exists=True))
@click.option("--ticks", default=10, help="Number of simulation ticks.")
@click.option("--state", "state_json", default="{}", help="Initial state JSON.")
@click.pass_context
def simulate(ctx: click.Context, domain_pack_file: str, ticks: int, state_json: str) -> None:
    """Run simulation with a DomainPack."""
    from polytwin.cli.simulate import run_simulate

    exit_code = run_simulate(domain_pack_file, ticks, state_json, ctx.obj)
    sys.exit(exit_code)


@cli.command()
@click.argument("output_file", type=click.Path())
@click.option("--format", "fmt", default="json", type=click.Choice(["json"]))
@click.option("--domain-pack", "domain_pack_file", type=click.Path(exists=True), default=None,
              help="DomainPack file to simulate before exporting.")
@click.option("--ticks", default=10, help="Number of simulation ticks.")
@click.option("--state", "state_json", default="{}", help="Initial state JSON.")
@click.pass_context
def export(ctx: click.Context, output_file: str, fmt: str,
           domain_pack_file: str | None, ticks: int, state_json: str) -> None:
    """Run simulation and export results to a file."""
    import json
    from pathlib import Path

    from polytwin.cli.export import run_export
    from polytwin.simulator.engine import SimulationEngine

    if domain_pack_file is None:
        ctx.obj["console"].print("[red]Error:[/red] --domain-pack is required")
        sys.exit(1)

    from polytwin.domainpack.parser import parse_domainpack

    try:
        dp = parse_domainpack(Path(domain_pack_file))
    except Exception as exc:
        ctx.obj["console"].print(f"[red]Error loading DomainPack:[/red] {exc}")
        sys.exit(1)

    engine = SimulationEngine(dp)
    engine.set_state(json.loads(state_json))

    import asyncio
    for _ in range(ticks):
        asyncio.get_event_loop().run_until_complete(engine.step())

    exit_code = run_export(engine, output_file, fmt, ctx.obj)
    sys.exit(exit_code)


@cli.command()
@click.argument("project_name")
@click.option("--directory", "-d", default=".", help="Parent directory for the new project.")
@click.pass_context
def init(ctx: click.Context, project_name: str, directory: str) -> None:
    """Initialize a new Polymorphic-Twin project with standard structure."""
    from pathlib import Path

    quiet = ctx.obj.get("quiet", False)
    out = ctx.obj["console"]

    target = Path(directory) / project_name
    if target.exists():
        out.print(f"[red]Error:[/red] Directory already exists: {target}")
        sys.exit(1)

    # Create directory structure
    dirs_to_create = [
        target,
        target / "configs",
        target / "configs" / "examples",
        target / "src" / project_name.replace("-", "_"),
        target / "tests",
        target / "tests" / "unit",
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    # Create __init__.py in source package
    pkg_name = project_name.replace("-", "_")
    (target / "src" / pkg_name / "__init__.py").write_text(
        f'"""{project_name} -- Polymorphic-Twin project."""\n'
    )

    # Create a starter DomainPack template
    starter_dp = f"""\
# {project_name} starter DomainPack
domain_id: "{pkg_name}.starter"
domain_name: "{project_name} starter scenario"
domain_version: "0.1.0"

state_semantics_template:
  ontology_reference: "{pkg_name}:starter"
  variables:
    - name: "value"
      physical_meaning: "Primary observable value"
      unit: "unit"
      range_min: 0.0
      range_max: 100.0
      observability: "observable"
      controllability: "controllable"
      required: true

constraint_cards:
  knowledge_base_reference: "{pkg_name}:starter:constraints"
  absolute: []
  soft: []
  learnable: []

safe_fallback:
  policy_id: "starter_fallback"
  domain_of_validity:
    conditions: []
    match_mode: "all"
  target_state:
    state_description: "Safe idle state"
    state_parameters:
      value: 0.0
  trajectory_constraints:
    max_rate: {{}}
    forbidden_zones: []
  max_duration: "PT0S"
  unavailable_action: "freeze"
  post_fallback_action: "hold"
  verification_record:
    verified_in_simulation: false
    verified_scenarios: []
    last_verification_date: "2026-01-01T00:00:00Z"

action_templates:
  knowledge_base_reference: "{pkg_name}:starter:actions"
  immediate_action_types: []
  conditional_action_types: []
  forbidden_action_types: []

human_roles: []
"""
    (target / "configs" / "examples" / f"{pkg_name}-starter.yaml").write_text(starter_dp)

    # Create a minimal test
    test_content = f'''"""Tests for {project_name}."""


def test_project_init():
    """Verify the project was created with expected structure."""
    import importlib

    mod = importlib.import_module("{pkg_name}")
    assert mod is not None
'''
    (target / "tests" / "unit" / f"test_{pkg_name}.py").write_text(test_content)

    if not quiet:
        out.print(f"[green]Created project:[/green] {target}")
        out.print(f"  configs/examples/{pkg_name}-starter.yaml")
        out.print(f"  src/{pkg_name}/__init__.py")
        out.print(f"  tests/unit/test_{pkg_name}.py")


# ── Sub-group registrations ────────────────────────────────────────────

from polytwin.cli.domainpack import domainpack  # noqa: E402
from polytwin.cli.templates import templates  # noqa: E402

cli.add_command(templates)
cli.add_command(domainpack)


# ── Allow ``python -m polytwin.cli.main`` ──────────────────────────────

if __name__ == "__main__":
    cli()
