"""Simulate CLI command -- run in-memory DomainPack simulations.

Provides the ``simulate`` Click command that loads a DomainPack,
optionally seeds state, runs N ticks, and displays per-tick results
using Rich formatting.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def run_simulate(
    domain_pack_file: str,
    ticks: int,
    state_json: str,
    ctx_obj: dict[str, Any],
) -> int:
    """Execute the simulate command. Returns exit code."""
    from polytwin.domainpack.parser import parse_domainpack
    from polytwin.simulator.engine import SimulationEngine

    quiet = ctx_obj.get("quiet", False)
    verbose = ctx_obj.get("verbose", False)
    out: Console = ctx_obj["console"]

    # Parse DomainPack
    try:
        dp = parse_domainpack(Path(domain_pack_file))
    except Exception as exc:
        out.print(f"[red]Error loading DomainPack:[/red] {exc}")
        return 1

    # Parse initial state
    try:
        initial = json.loads(state_json)
    except json.JSONDecodeError as exc:
        out.print(f"[red]Invalid state JSON:[/red] {exc}")
        return 1

    engine = SimulationEngine(dp)
    engine.set_state(initial)

    if not quiet:
        out.print(Panel(
            f"[bold]{dp.domain_name}[/bold]\n"
            f"ID: {dp.domain_id}  |  Version: {dp.domain_version}\n"
            f"Ticks: {ticks}",
            title="Simulation",
        ))

    # Run simulation ticks
    passed_count = 0
    failed_count = 0

    for _ in range(ticks):
        step = asyncio.get_event_loop().run_until_complete(engine.step())
        if step.passed:
            passed_count += 1
            if not quiet:
                out.print(
                    f"  [green]Tick {step.tick:3d}:[/green] PASS  "
                    f"({step.evaluated} evaluated)"
                )
        else:
            failed_count += 1
            if not quiet:
                out.print(
                    f"  [red]Tick {step.tick:3d}:[/red]  FAIL  "
                    f"({step.evaluated} evaluated)"
                    + (" [yellow]SAFETY FALLBACK[/yellow]" if step.safety_fallback else "")
                )

            # Verbose: show individual constraint results on failure
            if verbose:
                for indiv in step.individual:
                    status_color = "green" if indiv["status"] == "passed" else "red"
                    out.print(f"      [{status_color}]{indiv['id']}[/]: {indiv['status']}")

    # Summary
    if not quiet:
        out.print()
        summary_table = Table(title="Simulation Summary", show_lines=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="bold")
        summary_table.add_row("Total ticks", str(ticks))
        summary_table.add_row("Passed", f"[green]{passed_count}[/green]")
        summary_table.add_row("Failed", f"[red]{failed_count}[/red]")
        summary_table.add_row("Domain", dp.domain_id)
        out.print(summary_table)

    return 1 if failed_count > 0 else 0
