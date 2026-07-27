"""3-level DomainPack validation pipeline for the CLI.

Levels:
  1. Syntax  -- YAML/JSON parsing
  2. Semantic -- required fields, types, references
  3. Compatibility -- rigidity-criticality rules, Pydantic model acceptance
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def validate_domainpack_3level(filepath: str | Path) -> dict[str, Any]:
    """Run the three-level validation pipeline on a DomainPack file.

    Returns a dict with keys ``syntax``, ``semantic``, ``compatibility``,
    each containing ``{"passed": bool, ...}`` with optional error details.
    """
    filepath = Path(filepath)
    results: dict[str, Any] = {"syntax": None, "semantic": None, "compatibility": None}

    # ── Level 1: Syntax ────────────────────────────────────────────────
    try:
        text = filepath.read_text(encoding="utf-8")
        data = json.loads(text) if filepath.suffix == ".json" else yaml.safe_load(text)
        results["syntax"] = {"passed": True}
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        results["syntax"] = {"passed": False, "error": str(exc)}
        return results
    except Exception as exc:
        results["syntax"] = {"passed": False, "error": str(exc)}
        return results

    if not isinstance(data, dict):
        results["syntax"] = {"passed": False, "error": "Top-level must be a mapping"}
        return results

    # ── Level 2: Semantic ──────────────────────────────────────────────
    from polytwin.domainpack.validator import validate_domainpack_data

    errors = validate_domainpack_data(data, filepath.name)
    results["semantic"] = {
        "passed": len(errors) == 0,
        "errors": [str(e) for e in errors],
    }

    # ── Level 3: Compatibility (Pydantic model parse) ──────────────────
    from polytwin.domainpack.parser import parse_domainpack

    try:
        parse_domainpack(filepath)
        results["compatibility"] = {"passed": True}
    except Exception as exc:
        results["compatibility"] = {"passed": False, "error": str(exc)}

    return results


def run_validate(filepath: str, ctx_obj: dict) -> int:
    """Execute the validate command and print results. Returns exit code."""
    verbose = ctx_obj.get("verbose", False)
    quiet = ctx_obj.get("quiet", False)
    out = ctx_obj["console"]

    if not quiet:
        out.print(f"\n[bold]Validating:[/bold] {filepath}\n")

    results = validate_domainpack_3level(filepath)

    all_passed = True
    for level_name, level_result in results.items():
        if level_result is None:
            continue
        passed = level_result["passed"]
        all_passed = all_passed and passed
        status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
        if not quiet:
            out.print(f"  {level_name.capitalize():20s} {status}")

        # Print error details
        if not passed and not quiet:
            if "error" in level_result:
                out.print(f"    [red]{level_result['error']}[/red]")
            if "errors" in level_result:
                for err in level_result["errors"]:
                    out.print(f"    [red]{err}[/red]")

        # Verbose: print extra info even on success
        if verbose and passed:
            out.print("    [dim]No issues found[/dim]")

    if not quiet:
        out.print("")
        if all_passed:
            out.print("[bold green]All validation levels PASSED.[/bold green]")
        else:
            out.print("[bold red]Validation FAILED.[/bold red]")

    return 0 if all_passed else 1
