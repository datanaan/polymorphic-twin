"""Export CLI command -- export simulation results to file.

Provides the ``export`` Click command that writes simulation results
to a JSON file with a manifest header.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console


def run_export(
    engine: Any,
    output_file: str,
    fmt: str,
    ctx_obj: dict[str, Any],
) -> int:
    """Execute the export command. Returns exit code."""
    quiet = ctx_obj.get("quiet", False)
    out: Console = ctx_obj["console"]

    results = engine.export_results()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        output_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        out.print(f"[red]Unsupported format:[/red] {fmt}")
        return 1

    if not quiet:
        manifest = results.get("manifest", {})
        out.print(f"[green]Exported[/green] {manifest.get('ticks', 0)} ticks to {output_path}")
        out.print(f"  Domain: {manifest.get('domain_pack', 'N/A')}")
        out.print(f"  Exported at: {manifest.get('exported_at', 'N/A')}")

    return 0
