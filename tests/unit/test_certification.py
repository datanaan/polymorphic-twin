"""Tests for ModelCertification: certificate management.

Test cases:
1. Score >= 0.8 -> certificate granted
2. Score < 0.8 -> certificate denied with gaps
3. Revoke existing certificate -> True
4. Revoke non-existent certificate -> False
5. Verify existing certificate -> True
6. Verify non-existent certificate -> False
"""
import pytest

from polytwin.core.certification import ModelCertification

# ── Grant certificate ──────────────────────────────────────────────


class TestCertify:
    @pytest.mark.asyncio
    async def test_high_score_grants_certificate(self):
        """Score >= 0.8 -> certificate granted."""
        certifier = ModelCertification()
        result = await certifier.certify("model-1", 0.85, [])
        assert result.granted is True
        assert result.certificate is not None
        assert result.certificate.model_id == "model-1"
        assert result.certificate.score == 0.85

    @pytest.mark.asyncio
    async def test_exact_threshold_grants_certificate(self):
        """Score exactly at 0.8 threshold -> certificate granted."""
        certifier = ModelCertification()
        result = await certifier.certify("model-2", 0.8, [])
        assert result.granted is True

    @pytest.mark.asyncio
    async def test_perfect_score(self):
        """Score 1.0 -> certificate granted."""
        certifier = ModelCertification()
        result = await certifier.certify("model-3", 1.0)
        assert result.granted is True
        assert result.score == 1.0


# ── Deny certificate ───────────────────────────────────────────────


class TestCertifyDenied:
    @pytest.mark.asyncio
    async def test_low_score_denied(self):
        """Score < 0.8 -> certificate denied with gaps."""
        certifier = ModelCertification()
        result = await certifier.certify("model-bad", 0.5, [])
        assert result.granted is False
        assert result.certificate is None
        assert len(result.gaps) > 0
        assert "Score below threshold" in result.gaps

    @pytest.mark.asyncio
    async def test_zero_score_denied(self):
        """Score 0.0 -> denied."""
        certifier = ModelCertification()
        result = await certifier.certify("model-zero", 0.0)
        assert result.granted is False

    @pytest.mark.asyncio
    async def test_just_below_threshold_denied(self):
        """Score 0.79 -> denied."""
        certifier = ModelCertification()
        result = await certifier.certify("model-almost", 0.79)
        assert result.granted is False


# ── Revoke ──────────────────────────────────────────────────────────


class TestRevoke:
    @pytest.mark.asyncio
    async def test_revoke_existing_certificate(self):
        """Revoke existing certificate -> True."""
        certifier = ModelCertification()
        await certifier.certify("model-1", 0.9, [])
        revoked = await certifier.revoke("model-1", "safety violation")
        assert revoked is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_certificate(self):
        """Revoke non-existent certificate -> False."""
        certifier = ModelCertification()
        revoked = await certifier.revoke("model-ghost", "no such cert")
        assert revoked is False

    @pytest.mark.asyncio
    async def test_revoke_then_verify_fails(self):
        """After revocation, verify returns False."""
        certifier = ModelCertification()
        await certifier.certify("model-1", 0.9)
        await certifier.revoke("model-1", "expired")
        assert await certifier.verify("model-1") is False


# ── Verify ──────────────────────────────────────────────────────────


class TestVerify:
    @pytest.mark.asyncio
    async def test_verify_existing_certificate(self):
        """Verify existing certificate -> True."""
        certifier = ModelCertification()
        await certifier.certify("model-1", 0.85, [])
        assert await certifier.verify("model-1") is True

    @pytest.mark.asyncio
    async def test_verify_nonexistent_certificate(self):
        """Verify non-existent certificate -> False."""
        certifier = ModelCertification()
        assert await certifier.verify("model-ghost") is False

    @pytest.mark.asyncio
    async def test_re_certify_after_revocation(self):
        """Model can be re-certified after revocation."""
        certifier = ModelCertification()
        await certifier.certify("model-1", 0.9)
        await certifier.revoke("model-1", "expired")
        result = await certifier.certify("model-1", 0.95)
        assert result.granted is True
        assert await certifier.verify("model-1") is True
