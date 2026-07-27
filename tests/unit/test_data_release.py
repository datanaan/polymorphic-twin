"""Tests for DataReleaseManager: Core-to-Lab data channel.

Key tests:
1. Returns data with correct structure
2. Hidden validation sets are NEVER exposed
3. No get_hidden_challenge_set method exists
4. Validation catches hidden references
"""
import pytest

from polytwin.lab.data_release import DataReleaseManager


class TestDataReleaseBasic:
    @pytest.mark.asyncio
    async def test_release_failure_logs_structure(self):
        mgr = DataReleaseManager()
        result = await mgr.release_failure_logs("dp-1")
        assert "logs" in result
        assert result["domain_pack_id"] == "dp-1"

    @pytest.mark.asyncio
    async def test_get_authorized_data_structure(self):
        mgr = DataReleaseManager()
        result = await mgr.get_authorized_data("dp-1")
        assert "domain_pack_id" in result
        assert "records" in result
        assert result["domain_pack_id"] == "dp-1"

    @pytest.mark.asyncio
    async def test_get_public_eval_set_returns_list(self):
        mgr = DataReleaseManager()
        result = await mgr.get_public_eval_set("dp-1")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_constraint_summary_returns_list(self):
        mgr = DataReleaseManager()
        result = await mgr.get_constraint_summary("dp-1")
        assert isinstance(result, list)


class TestNoHiddenAccess:
    def test_no_get_hidden_challenge_set_method(self):
        """The method get_hidden_challenge_set MUST NOT exist."""
        mgr = DataReleaseManager()
        assert not hasattr(mgr, "get_hidden_challenge_set")

    def test_no_get_hidden_validation_set_method(self):
        mgr = DataReleaseManager()
        assert not hasattr(mgr, "get_hidden_validation_set")

    def test_validate_clean_data(self):
        mgr = DataReleaseManager()
        assert mgr.validate_no_hidden_exposure({"domain_pack_id": "dp-1"}) is True

    def test_validate_detects_hidden_challenge_set(self):
        mgr = DataReleaseManager()
        assert mgr.validate_no_hidden_exposure({"hidden_challenge_set": []}) is False

    def test_validate_detects_audit_benchmark(self):
        mgr = DataReleaseManager()
        assert mgr.validate_no_hidden_exposure({"audit_benchmark_reference": "x"}) is False

    def test_validate_detects_production_acceptance(self):
        mgr = DataReleaseManager()
        assert mgr.validate_no_hidden_exposure({"production_acceptance_reference": "x"}) is False

    def test_validate_detects_nested_reference(self):
        mgr = DataReleaseManager()
        data = {"outer": {"inner": "contains hidden_validation_set ref"}}
        assert mgr.validate_no_hidden_exposure(data) is False
