#!/usr/bin/env python3
"""validate_domainpack.py — DomainPack CLI validation wrapper.

Thin CLI wrapper around polytwin.domainpack.validator.
See that module for the actual validation logic.

Usage:
    python scripts/validate_domainpack.py configs/examples/minimal-domain-pack.yaml
    python scripts/validate_domainpack.py configs/examples/*.yaml
"""
import sys
from pathlib import Path

import yaml

from polytwin.domainpack.validator import ValidationError, validate_domainpack_data


def validate_domainpack(filepath: Path) -> list[ValidationError]:
    """Validate a single DomainPack YAML file. Returns list of errors."""
    try:
        data = yaml.safe_load(filepath.read_text())
    except yaml.YAMLError as e:
        return [ValidationError(str(filepath), f"YAML parse error: {e}")]

    return validate_domainpack_data(data, name=filepath.name)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_domainpack.py <file.yaml> [file2.yaml ...]")
        sys.exit(1)

    all_errors: list[ValidationError] = []
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: {path_str} not found")
            sys.exit(1)
        errors = validate_domainpack(path)
        all_errors.extend(errors)

    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} error(s)")
        for err in all_errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print(f"VALIDATION PASSED: {len(sys.argv) - 1} file(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
