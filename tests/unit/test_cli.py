"""Tests for the Polymorphic-Twin Workbench CLI.

Covers all major commands: validate, init, templates list/show,
domainpack list/show/validate, and --version.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from polytwin.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project_dir():
    """Create a temporary directory for project init tests."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── Version ────────────────────────────────────────────────────────────


class TestVersion:
    def test_version_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


# ── Validate command ───────────────────────────────────────────────────


class TestValidate:
    def test_validate_valid_file(self, runner: CliRunner):
        result = runner.invoke(cli, ["validate", "configs/examples/minimal-domain-pack.yaml"])
        assert result.exit_code == 0
        assert "PASSED" in result.output

    def test_validate_invalid_soft_safety(self, runner: CliRunner):
        result = runner.invoke(cli, ["validate", "configs/examples/invalid-soft-safety.yaml"])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_validate_invalid_missing_fallback(self, runner: CliRunner):
        result = runner.invoke(cli, ["validate", "configs/examples/invalid-missing-fallback.yaml"])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_validate_invalid_undefined_variable(self, runner: CliRunner):
        result = runner.invoke(cli, ["validate", "configs/examples/invalid-undefined-variable.yaml"])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_validate_nonexistent_file(self, runner: CliRunner):
        result = runner.invoke(cli, ["validate", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_validate_verbose_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["--verbose", "validate", "configs/examples/minimal-domain-pack.yaml"])
        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_validate_quiet_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["--quiet", "validate", "configs/examples/minimal-domain-pack.yaml"])
        # Quiet suppresses output but should still exit 0
        assert result.exit_code == 0


# ── Init command ───────────────────────────────────────────────────────


class TestInit:
    def test_init_creates_project(self, runner: CliRunner, project_dir: str):
        result = runner.invoke(cli, ["init", "my-test-project", "-d", project_dir])
        assert result.exit_code == 0
        assert "Created project" in result.output

        target = Path(project_dir) / "my-test-project"
        assert target.is_dir()
        assert (target / "configs" / "examples").is_dir()
        assert (target / "src" / "my_test_project" / "__init__.py").is_file()
        assert (target / "tests" / "unit").is_dir()

    def test_init_starter_domainpack(self, runner: CliRunner, project_dir: str):
        result = runner.invoke(cli, ["init", "demo-app", "-d", project_dir])
        assert result.exit_code == 0

        target = Path(project_dir) / "demo-app"
        yaml_files = list((target / "configs" / "examples").glob("*.yaml"))
        assert len(yaml_files) == 1
        assert "demo_app" in yaml_files[0].name

    def test_init_already_exists(self, runner: CliRunner, project_dir: str):
        # Create it first
        runner.invoke(cli, ["init", "existing-project", "-d", project_dir])
        # Try again
        result = runner.invoke(cli, ["init", "existing-project", "-d", project_dir])
        assert result.exit_code == 1
        assert "already exists" in result.output


# ── Templates commands ────────────────────────────────────────────────


class TestTemplates:
    def test_templates_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["templates", "list"])
        assert result.exit_code == 0
        assert "minimal-domain-pack" in result.output

    def test_templates_show_existing(self, runner: CliRunner):
        result = runner.invoke(cli, ["templates", "show", "minimal-domain-pack.yaml"])
        assert result.exit_code == 0
        assert "domain_id" in result.output

    def test_templates_show_with_extension(self, runner: CliRunner):
        result = runner.invoke(cli, ["templates", "show", "minimal-domain-pack"])
        assert result.exit_code == 0
        assert "domain_id" in result.output

    def test_templates_show_nonexistent(self, runner: CliRunner):
        result = runner.invoke(cli, ["templates", "show", "does-not-exist"])
        assert result.exit_code == 1
        assert "not found" in result.output


# ── DomainPack commands ───────────────────────────────────────────────


class TestDomainPack:
    def test_domainpack_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["domainpack", "list"])
        assert result.exit_code == 0
        # At least the minimal DomainPack should load
        assert "example.minimal_device_monitor" in result.output

    def test_domainpack_show_existing(self, runner: CliRunner):
        result = runner.invoke(cli, ["domainpack", "show", "example.minimal_device_monitor"])
        assert result.exit_code == 0
        assert "minimal_device_monitor" in result.output
        assert "State Variables" in result.output

    def test_domainpack_show_nonexistent(self, runner: CliRunner):
        result = runner.invoke(cli, ["domainpack", "show", "nonexistent.pack"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_domainpack_validate_valid(self, runner: CliRunner):
        result = runner.invoke(cli, ["domainpack", "validate", "configs/examples/minimal-domain-pack.yaml"])
        assert result.exit_code == 0
        assert "PASSED" in result.output

    def test_domainpack_validate_invalid(self, runner: CliRunner):
        result = runner.invoke(cli, ["domainpack", "validate", "configs/examples/invalid-soft-safety.yaml"])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_domainpack_show_verbose(self, runner: CliRunner):
        result = runner.invoke(cli, ["--verbose", "domainpack", "show", "example.minimal_device_monitor"])
        assert result.exit_code == 0
        assert "Constraint details" in result.output


# ── 3-level validation pipeline (direct function test) ────────────────


class TestValidationPipeline:
    def test_syntax_valid_yaml(self):
        from polytwin.cli.validate import validate_domainpack_3level

        results = validate_domainpack_3level("configs/examples/minimal-domain-pack.yaml")
        assert results["syntax"]["passed"] is True

    def test_semantic_valid(self):
        from polytwin.cli.validate import validate_domainpack_3level

        results = validate_domainpack_3level("configs/examples/minimal-domain-pack.yaml")
        assert results["semantic"]["passed"] is True

    def test_compatibility_valid(self):
        from polytwin.cli.validate import validate_domainpack_3level

        results = validate_domainpack_3level("configs/examples/minimal-domain-pack.yaml")
        assert results["compatibility"]["passed"] is True

    def test_semantic_invalid_soft_safety(self):
        from polytwin.cli.validate import validate_domainpack_3level

        results = validate_domainpack_3level("configs/examples/invalid-soft-safety.yaml")
        assert results["semantic"]["passed"] is False
        assert any("safety_critical" in e for e in results["semantic"]["errors"])

    def test_semantic_invalid_missing_fallback(self):
        from polytwin.cli.validate import validate_domainpack_3level

        results = validate_domainpack_3level("configs/examples/invalid-missing-fallback.yaml")
        assert results["semantic"]["passed"] is False

    def test_syntax_invalid_file(self, tmp_path: Path):
        from polytwin.cli.validate import validate_domainpack_3level

        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{{{invalid yaml::::", encoding="utf-8")
        results = validate_domainpack_3level(str(bad_file))
        assert results["syntax"]["passed"] is False
