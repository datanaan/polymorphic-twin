"""YAML/JSON parsing for DomainPack files with validation.

Provides parse_domainpack() which reads a YAML or JSON file, validates
its structure, and returns a typed DomainPack model.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .types import DomainPack
from .validator import ValidationError, validate_domainpack_data


class DomainPackValidationError(Exception):
    """Raised when a DomainPack file fails validation after parsing."""

    def __init__(self, filepath: str, errors: list[ValidationError]):
        self.filepath = filepath
        self.errors = errors
        error_details = "; ".join(str(e) for e in errors)
        super().__init__(f"DomainPack validation failed for {filepath}: {error_details}")


def parse_domainpack(filepath: Path | str) -> DomainPack:
    """Parse a YAML or JSON file into a validated DomainPack model.

    Args:
        filepath: Path to the DomainPack YAML/JSON file.

    Returns:
        A typed DomainPack instance.

    Raises:
        DomainPackValidationError: If validation errors are found.
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML cannot be parsed.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"DomainPack file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8")

    # Determine format by extension
    data = json.loads(text) if filepath.suffix in (".json",) else yaml.safe_load(text)

    if not isinstance(data, dict):
        raise DomainPackValidationError(
            str(filepath),
            [ValidationError(str(filepath), "Top-level must be a mapping")],
        )

    # Run validation checks
    errors = validate_domainpack_data(data, name=filepath.name)
    if errors:
        raise DomainPackValidationError(str(filepath), errors)

    # Parse into typed DomainPack model
    return DomainPack.model_validate(data)
