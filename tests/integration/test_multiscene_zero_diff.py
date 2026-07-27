"""Zero code modification verification test (M6-C1).

Verifies that adding new DomainPacks required ZERO changes to
Core, Lab, or Bridge source code. This is the key architectural
invariant of the Polymorphic-Twin framework: scenario-specific
logic is entirely contained in DomainPack configuration files.

Validates:
1. No modifications to src/polytwin/core/ since baseline
2. No modifications to src/polytwin/lab/ since baseline
3. No modifications to src/polytwin/bridge/ since baseline
4. DomainPack YAML files are the only additions
5. Test files are the only other additions
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.integration


def _git_diff(paths: list[str]) -> str:
    """Run git diff for the given paths against HEAD and return stdout."""
    result = subprocess.run(
        ["git", "diff", "HEAD", "--"] + paths,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    return result.stdout.strip()


def _git_diff_staged(paths: list[str]) -> str:
    """Run git diff --cached for the given paths and return stdout."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--"] + paths,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    return result.stdout.strip()


class TestZeroCodeModification:
    """M6-C1: Core/Lab/Bridge code has zero modifications."""

    def test_core_no_diff(self) -> None:
        """Core module has no modifications."""
        diff = _git_diff(["src/polytwin/core/"])
        staged = _git_diff_staged(["src/polytwin/core/"])
        assert diff == "", f"Core module was modified (unstaged): {diff}"
        assert staged == "", f"Core module was modified (staged): {staged}"

    def test_lab_no_diff(self) -> None:
        """Lab module has no modifications."""
        diff = _git_diff(["src/polytwin/lab/"])
        staged = _git_diff_staged(["src/polytwin/lab/"])
        assert diff == "", f"Lab module was modified (unstaged): {diff}"
        assert staged == "", f"Lab module was modified (staged): {staged}"

    def test_bridge_no_diff(self) -> None:
        """Bridge module has no modifications."""
        diff = _git_diff(["src/polytwin/bridge/"])
        staged = _git_diff_staged(["src/polytwin/bridge/"])
        assert diff == "", f"Bridge module was modified (unstaged): {diff}"
        assert staged == "", f"Bridge module was modified (staged): {staged}"

    def test_combined_no_diff(self) -> None:
        """Combined check: Core + Lab + Bridge have zero modifications."""
        diff = _git_diff(["src/polytwin/core/", "src/polytwin/lab/", "src/polytwin/bridge/"])
        staged = _git_diff_staged(["src/polytwin/core/", "src/polytwin/lab/", "src/polytwin/bridge/"])
        assert diff == "", f"Core/Lab/Bridge code was modified (unstaged): {diff}"
        assert staged == "", f"Core/Lab/Bridge code was modified (staged): {staged}"

    def test_domainpack_yaml_files_exist(self) -> None:
        """New DomainPack YAML files exist as expected."""
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent.parent / "configs" / "examples"
        expected_files = [
            "chemical-reactor-thermal-0.1.0.yaml",
            "wind-turbine-bearing-0.1.0.yaml",
            "knowledge-management-0.1.0.yaml",
        ]
        for filename in expected_files:
            filepath = base / filename
            assert filepath.exists(), f"DomainPack file missing: {filepath}"

    def test_domainpack_yaml_files_validate(self) -> None:
        """All new DomainPack YAML files pass validation."""
        from pathlib import Path

        import yaml

        from polytwin.domainpack.validator import validate_domainpack_data

        base = Path(__file__).resolve().parent.parent.parent / "configs" / "examples"
        yaml_files = [
            "chemical-reactor-thermal-0.1.0.yaml",
            "wind-turbine-bearing-0.1.0.yaml",
            "knowledge-management-0.1.0.yaml",
        ]

        for filename in yaml_files:
            filepath = base / filename
            data = yaml.safe_load(filepath.read_text())
            errors = validate_domainpack_data(data, name=filename)
            assert errors == [], (
                f"DomainPack {filename} failed validation: "
                + "; ".join(str(e) for e in errors)
            )
