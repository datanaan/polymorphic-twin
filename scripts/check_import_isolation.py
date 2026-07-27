#!/usr/bin/env python3
"""check_import_isolation.py — Scan source files for forbidden cross-module imports."""
import ast
import sys
from pathlib import Path

FORBIDDEN = {
    "polytwin.lab": [
        "polytwin.core.engine", "polytwin.core.hardgate", "polytwin.core.fallback",
        "polytwin.core.evidence", "polytwin.core.certification", "polytwin.core.audit",
    ],
    "polytwin.bridge": [
        "polytwin.core.engine", "polytwin.core.hardgate", "polytwin.core.fallback",
        "polytwin.core.evidence", "polytwin.core.certification",
        "polytwin.lab.explorer", "polytwin.lab.sandbox", "polytwin.lab.data_release",
    ],
    "polytwin.core": [
        "polytwin.lab.explorer", "polytwin.lab.sandbox", "polytwin.lab.data_release",
        "polytwin.bridge.orchestrator", "polytwin.bridge.action_space",
    ],
}

def get_imports(filepath: Path) -> list[str]:
    """Extract all import targets from a Python file using AST."""
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def check_isolation(src_root: Path) -> list[str]:
    """Scan all source files for forbidden imports. Returns list of violation strings."""
    violations = []
    for module_name, forbidden_imports in FORBIDDEN.items():
        module_dir = src_root / module_name.replace(".", "/")
        if not module_dir.exists():
            continue
        for py_file in module_dir.rglob("*.py"):
            imports = get_imports(py_file)
            for imp in imports:
                for forbidden in forbidden_imports:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        rel_path = py_file.relative_to(src_root)
                        violations.append(
                            f"{rel_path}: imports '{imp}' (forbidden for {module_name})"
                        )
    return violations

def main():
    src_root = Path("src")
    if not src_root.exists():
        print("ERROR: src/ directory not found")
        sys.exit(1)
    violations = check_isolation(src_root)
    if violations:
        print(f"ISOLATION VIOLATION: {len(violations)} forbidden import(s) found:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("ISOLATION CHECK PASSED: no forbidden cross-module imports")
        sys.exit(0)

if __name__ == "__main__":
    main()
