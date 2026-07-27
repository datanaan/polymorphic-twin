"""Template management commands for the CLI.

Templates are bundled DomainPack YAML examples that serve as starting
points for new scenarios.  They are stored in the ``configs/examples/``
directory shipped with the package.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

# Resolve the templates directory: prefer the repo configs/examples, fall back to package data.
_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "configs" / "examples"


def _iter_template_files() -> list[Path]:
    """Return sorted list of template YAML files."""
    if _TEMPLATES_DIR.is_dir():
        return sorted(
            p for p in _TEMPLATES_DIR.iterdir()
            if p.suffix in (".yaml", ".yml") and not p.name.startswith("invalid-")
        )
    return []


@click.group("templates")
@click.pass_context
def templates(ctx: click.Context) -> None:
    """Manage DomainPack templates."""


@templates.command("list")
@click.pass_context
def templates_list(ctx: click.Context) -> None:
    """List available DomainPack templates."""
    quiet = ctx.obj.get("quiet", False)
    out: Console = ctx.obj["console"]

    files = _iter_template_files()
    if not files:
        out.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="DomainPack Templates", show_lines=False)
    table.add_column("Name", style="cyan")
    table.add_column("Domain ID", style="green")
    table.add_column("Version", style="dim")

    for fpath in files:
        try:
            data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
            domain_id = data.get("domain_id", "?")
            version = data.get("domain_version", "?")
        except Exception:
            domain_id = "(parse error)"
            version = "?"
        table.add_row(fpath.name, domain_id, version)

    if not quiet:
        out.print(table)


@templates.command("show")
@click.argument("name")
@click.pass_context
def templates_show(ctx: click.Context, name: str) -> None:
    """Show the content of a named template."""
    quiet = ctx.obj.get("quiet", False)
    out: Console = ctx.obj["console"]

    # Match by filename with or without extension
    candidates = [name, f"{name}.yaml", f"{name}.yml"]
    target: Path | None = None
    for c in candidates:
        p = _TEMPLATES_DIR / c
        if p.is_file():
            target = p
            break

    if target is None:
        out.print(f"[red]Error:[/red] Template not found: {name}")
        sys.exit(1)

    content = target.read_text(encoding="utf-8")
    if quiet:
        out.print(content, highlight=False)
    else:
        out.print(f"\n[bold]Template:[/bold] {target.name}\n")
        out.print(content, highlight=False)
