"""Tests for SubmissionQuarantine: three-step Lab submission check.

Test cases:
1. Valid submission -> accepted
2. Missing lineage -> rejected("format_integrity")
3. Payload > 10MB -> rejected("payload_too_large")
4. Contains "hidden_challenge_set" -> rejected("sensitive_info_detected")
5. Lab caller accepted, non-lab rejected
"""
import pytest

from polytwin.core.quarantine import SubmissionQuarantine
from polytwin.tom.types import CallerIdentity


def _lab_caller() -> CallerIdentity:
    return CallerIdentity(component="lab", role="explorer")


def _non_lab_caller() -> CallerIdentity:
    return CallerIdentity(component="core", role="validator")


def _valid_submission(**overrides: object) -> dict:
    """Build a minimal valid Lab submission."""
    sub = {
        "hypothesis_id": "hyp-001",
        "lineage": {"creator_id": "lab-engine"},
        "domain_id": "thermal-management",
        "payload": {"data": "test"},
    }
    sub.update(overrides)
    return sub


# ── Valid submission ─────────────────────────────────────────────────


class TestValidSubmission:
    @pytest.mark.asyncio
    async def test_valid_submission_accepted(self):
        """Valid submission with all fields -> accepted."""
        q = SubmissionQuarantine()
        result = await q.submit(_valid_submission(), _lab_caller())
        assert result.rejected is False
        assert result.reason == ""

    @pytest.mark.asyncio
    async def test_valid_submission_with_extra_fields(self):
        """Extra fields are allowed."""
        q = SubmissionQuarantine()
        result = await q.submit(_valid_submission(extra="data"), _lab_caller())
        assert result.rejected is False


# ── Step 1: Format integrity ────────────────────────────────────────


class TestFormatIntegrity:
    @pytest.mark.asyncio
    async def test_missing_lineage_rejected(self):
        """Missing lineage -> rejected("format_integrity")."""
        q = SubmissionQuarantine()
        sub = _valid_submission()
        del sub["lineage"]
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "format_integrity"

    @pytest.mark.asyncio
    async def test_missing_hypothesis_id_rejected(self):
        """Missing hypothesis_id -> rejected("format_integrity")."""
        q = SubmissionQuarantine()
        sub = _valid_submission()
        del sub["hypothesis_id"]
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "format_integrity"

    @pytest.mark.asyncio
    async def test_missing_domain_id_rejected(self):
        """Missing domain_id -> rejected("format_integrity")."""
        q = SubmissionQuarantine()
        sub = _valid_submission()
        del sub["domain_id"]
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "format_integrity"


# ── Step 2: Resource check ──────────────────────────────────────────


class TestResourceCheck:
    @pytest.mark.asyncio
    async def test_payload_too_large_rejected(self):
        """Payload > 10MB -> rejected("payload_too_large")."""
        q = SubmissionQuarantine()
        # Create a payload that exceeds 10MB
        large_data = "x" * (11 * 1024 * 1024)
        sub = _valid_submission(payload={"data": large_data})
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "payload_too_large"


# ── Step 3: Sensitive info scan ─────────────────────────────────────


class TestSensitiveInfoScan:
    @pytest.mark.asyncio
    async def test_hidden_challenge_set_rejected(self):
        """Contains 'hidden_challenge_set' -> rejected("sensitive_info_detected")."""
        q = SubmissionQuarantine()
        sub = _valid_submission(payload={"ref": "hidden_challenge_set"})
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "sensitive_info_detected"

    @pytest.mark.asyncio
    async def test_audit_benchmark_reference_rejected(self):
        """Contains 'audit_benchmark_reference' -> rejected."""
        q = SubmissionQuarantine()
        sub = _valid_submission(payload={"ref": "audit_benchmark_reference"})
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "sensitive_info_detected"

    @pytest.mark.asyncio
    async def test_production_acceptance_reference_rejected(self):
        """Contains 'production_acceptance_reference' -> rejected."""
        q = SubmissionQuarantine()
        sub = _valid_submission(payload={"ref": "production_acceptance_reference"})
        result = await q.submit(sub, _lab_caller())
        assert result.rejected is True
        assert result.reason == "sensitive_info_detected"


# ── Caller identity ─────────────────────────────────────────────────


class TestCallerIdentity:
    @pytest.mark.asyncio
    async def test_lab_caller_accepted(self):
        """Lab caller -> not rejected by caller gate."""
        q = SubmissionQuarantine()
        result = await q.submit(_valid_submission(), _lab_caller())
        assert result.rejected is False

    @pytest.mark.asyncio
    async def test_core_caller_rejected(self):
        """Non-lab caller -> rejected("caller_not_authorized")."""
        q = SubmissionQuarantine()
        result = await q.submit(_valid_submission(), _non_lab_caller())
        assert result.rejected is True
        assert result.reason == "caller_not_authorized"

    @pytest.mark.asyncio
    async def test_bridge_caller_rejected(self):
        """Bridge caller -> rejected."""
        q = SubmissionQuarantine()
        bridge_caller = CallerIdentity(component="bridge", role="decision")
        result = await q.submit(_valid_submission(), bridge_caller)
        assert result.rejected is True
        assert result.reason == "caller_not_authorized"
