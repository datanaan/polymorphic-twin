"""DomainPack sub-commands for the CLI.

Provides ``list``, ``show``, and ``validate`` sub-commands that operate
on DomainPacks loaded from the configured example directories.
"""
from __future__ import annotations

import contextlib
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from polytwin.domainpack.registry import DomainPackRegistry


def _build_registry() -> DomainPackRegistry:
    """Build a registry loaded from the default configs/examples directory."""
    from pathlib import Path

    registry = DomainPackRegistry()
    examples_dir = Path("configs/examples")
    if examples_dir.is_dir():
        with contextlib.suppress(Exception):
            registry.load_from_directory(examples_dir)
    return registry


@click.group("domainpack")
@click.pass_context
def domainpack(ctx: click.Context) -> None:
    """Manage loaded DomainPacks."""


@domainpack.command("list")
@click.pass_context
def domainpack_list(ctx: click.Context) -> None:
    """List all loaded DomainPacks."""
    quiet = ctx.obj.get("quiet", False)
    out: Console = ctx.obj["console"]

    registry = _build_registry()
    ids = registry.list_all()

    if not ids:
        out.print("[yellow]No DomainPacks loaded.[/yellow]")
        return

    table = Table(title="Loaded DomainPacks", show_lines=False)
    table.add_column("Domain ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Version", style="dim")
    table.add_column("Variables", style="blue", justify="right")

    for did in ids:
        dp = registry.get(did)
        if dp is not None:
            table.add_row(
                dp.domain_id,
                dp.domain_name,
                dp.domain_version,
                str(len(dp.variables)),
            )

    if not quiet:
        out.print(table)


@domainpack.command("show")
@click.argument("domain_id")
@click.pass_context
def domainpack_show(ctx: click.Context, domain_id: str) -> None:
    """Show details for a loaded DomainPack."""
    verbose = ctx.obj.get("verbose", False)
    ctx.obj.get("quiet", False)
    out: Console = ctx.obj["console"]

    registry = _build_registry()
    dp = registry.get(domain_id)

    if dp is None:
        out.print(f"[red]Error:[/red] DomainPack not found: {domain_id}")
        out.print("[dim]Use 'polytwin-cli domainpack list' to see available packs.[/dim]")
        sys.exit(1)

    # Header
    out.print(Panel(
        f"[bold]{dp.domain_name}[/bold]\n"
        f"ID: {dp.domain_id}  |  Version: {dp.domain_version}",
        title="DomainPack",
    ))

    # State variables
    variables = dp.variables
    if variables:
        var_table = Table(title="State Variables", show_lines=False)
        var_table.add_column("Name", style="cyan")
        var_table.add_column("Unit", style="dim")
        var_table.add_column("Range", style="blue")
        var_table.add_column("Required", style="yellow")

        for v in variables:
            var_table.add_row(
                v.name,
                v.unit,
                f"[{v.range_min}, {v.range_max}]",
                "yes" if v.required else "no",
            )
        out.print(var_table)

    # Constraint counts
    cc = dp.constraint_cards
    absolute_count = len(cc.get("absolute", []))
    soft_count = len(cc.get("soft", []))
    learnable_count = len(cc.get("learnable", []))
    out.print(f"\n  Constraints: {absolute_count} absolute, {soft_count} soft, {learnable_count} learnable")

    # Human roles
    if dp.human_roles:
        out.print(f"  Roles: {', '.join(r.role_id for r in dp.human_roles)}")

    # Verbose: show constraint IDs
    if verbose:
        out.print("\n[bold]Constraint details:[/bold]")
        for rigidity in ("absolute", "soft", "learnable"):
            cards = cc.get(rigidity, [])
            for card in cards:
                cid = card.get("constraint_id", "?")
                crit = card.get("scenario_criticality", "?")
                out.print(f"  [{rigidity}] {cid} ({crit})")


@domainpack.command("validate")
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def domainpack_validate(ctx: click.Context, file: str) -> None:
    """Validate a DomainPack file through 3-level pipeline."""
    from polytwin.cli.validate import run_validate

    exit_code = run_validate(file, ctx.obj)
    sys.exit(exit_code)
