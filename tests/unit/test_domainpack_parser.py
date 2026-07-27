"""Tests for DomainPack parser (parser.py)."""
import json
from pathlib import Path

import pytest
import yaml

from polytwin.domainpack.parser import DomainPackValidationError, parse_domainpack

CONFIGS = Path("configs/examples")


class TestParseValidYAML:
    """Test parsing valid YAML into DomainPack."""

    def test_parse_minimal_domain_pack(self):
        pack = parse_domainpack(CONFIGS / "minimal-domain-pack.yaml")
        assert pack.domain_id == "example.minimal_device_monitor"
        assert pack.domain_name == "最小设备监控场景"

    def test_parsed_pack_has_variables(self):
        pack = parse_domainpack(CONFIGS / "minimal-domain-pack.yaml")
        assert len(pack.variables) == 5
        assert "temperature" in pack.variable_names

    def test_parsed_pack_has_constraint_cards(self):
        pack = parse_domainpack(CONFIGS / "minimal-domain-pack.yaml")
        assert "absolute" in pack.constraint_cards
        assert len(pack.constraint_cards["absolute"]) == 4


class TestParseInvalidYAML:
    """Test that invalid YAML raises DomainPackValidationError."""

    def test_soft_safety_critical_rejected(self):
        with pytest.raises(DomainPackValidationError) as exc_info:
            parse_domainpack(CONFIGS / "invalid-soft-safety.yaml")
        assert "safety_critical" in str(exc_info.value)
        assert len(exc_info.value.errors) > 0

    def test_missing_fallback_target_rejected(self):
        with pytest.raises(DomainPackValidationError) as exc_info:
            parse_domainpack(CONFIGS / "invalid-missing-fallback.yaml")
        assert "target_state" in str(exc_info.value)

    def test_undefined_variable_rejected(self):
        with pytest.raises(DomainPackValidationError) as exc_info:
            parse_domainpack(CONFIGS / "invalid-undefined-variable.yaml")
        assert "undefined state variable" in str(exc_info.value)


class TestParseMissingFields:
    """Test parsing with missing required fields."""

    def test_missing_domain_id(self, tmp_path):
        data = {
            "domain_name": "test",
            "domain_version": "0.1.0",
            "state_semantics_template": {"variables": []},
            "constraint_cards": {"absolute": [], "soft": [], "learnable": []},
            "safe_fallback": {"policy_id": "test"},
            "action_templates": {
                "immediate_action_types": [],
                "conditional_action_types": [],
                "forbidden_action_types": [],
            },
            "human_roles": [],
        }
        filepath = tmp_path / "missing_id.yaml"
        filepath.write_text(yaml.dump(data))
        with pytest.raises(DomainPackValidationError) as exc_info:
            parse_domainpack(filepath)
        assert "domain_id" in str(exc_info.value)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_domainpack("/nonexistent/path.yaml")


class TestParseJSON:
    """Test parsing from JSON files."""

    def test_parse_valid_json(self, tmp_path):
        data = yaml.safe_load((CONFIGS / "minimal-domain-pack.yaml").read_text())
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        pack = parse_domainpack(filepath)
        assert pack.domain_id == "example.minimal_device_monitor"
