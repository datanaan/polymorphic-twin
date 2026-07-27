"""Tests for EvidenceAdmission: item-level independent judgment.

Test cases:
1. Valid item -> admitted
2. Invalid item -> not admitted
3. Mixed batch: valid admitted, invalid rejected, independent (M2-C4)
4. Feedback desensitization: same format for hidden_set vs public_set rejection (M2-C5)
5. Empty batch -> empty results
6. Item referencing hidden set -> rejected
7. Item missing item_id -> rejected
"""
import pytest

from polytwin.core.evidence import EvidenceAdmission
from polytwin.core.types import EvidenceAdmissionResult

# ── Valid item ───────────────────────────────────────────────────────


class TestValidItem:
    @pytest.mark.asyncio
    async def test_valid_item_admitted(self):
        """Valid item -> admitted."""
        ea = EvidenceAdmission()
        items = [{"item_id": "ev-001", "data": "hypothesis_result"}]
        results = await ea.admit_batch(items, {})
        assert len(results) == 1
        assert results[0].item_id == "ev-001"
        assert results[0].admitted is True

    @pytest.mark.asyncio
    async def test_valid_item_with_passing_validation(self):
        """Valid item with passing validation -> admitted."""
        ea = EvidenceAdmission()
        items = [{"item_id": "ev-001"}]
        validation = {"ev-001": {"passed": True, "source": "public_set"}}
        results = await ea.admit_batch(items, validation)
        assert results[0].admitted is True


# ── Invalid item ────────────────────────────────────────────────────


class TestInvalidItem:
    @pytest.mark.asyncio
    async def test_failed_validation_not_admitted(self):
        """Item that fails validation -> not admitted."""
        ea = EvidenceAdmission()
        items = [{"item_id": "ev-001"}]
        validation = {"ev-001": {"passed": False, "source": "public_set"}}
        results = await ea.admit_batch(items, validation)
        assert results[0].admitted is False

    @pytest.mark.asyncio
    async def test_missing_item_id_not_admitted(self):
        """Item without item_id -> not admitted."""
        ea = EvidenceAdmission()
        items = [{"data": "no_id"}]
        results = await ea.admit_batch(items, {})
        assert results[0].admitted is False
        assert results[0].item_id == ""

    @pytest.mark.asyncio
    async def test_hidden_set_source_not_admitted(self):
        """Item from hidden_set source -> not admitted."""
        ea = EvidenceAdmission()
        items = [{"item_id": "ev-001"}]
        validation = {"ev-001": {"passed": True, "source": "hidden_set"}}
        results = await ea.admit_batch(items, validation)
        assert results[0].admitted is False

    @pytest.mark.asyncio
    async def test_item_referencing_hidden_challenge_set(self):
        """Item containing hidden_challenge_set -> not admitted."""
        ea = EvidenceAdmission()
        items = [{"item_id": "ev-001", "ref": "hidden_challenge_set"}]
        results = await ea.admit_batch(items, {})
        assert results[0].admitted is False


# ── Mixed batch (M2-C4) ────────────────────────────────────────────


class TestMixedBatch:
    @pytest.mark.asyncio
    async def test_mixed_batch_independent_judgment(self):
        """M2-C4: Valid admitted, invalid rejected, independently."""
        ea = EvidenceAdmission()
        items = [
            {"item_id": "ev-001", "data": "good"},
            {"item_id": "ev-002", "data": "bad"},
            {"item_id": "ev-003", "data": "also_good"},
        ]
        validation = {
            "ev-001": {"passed": True, "source": "public_set"},
            "ev-002": {"passed": False, "source": "public_set"},
            "ev-003": {"passed": True, "source": "public_set"},
        }
        results = await ea.admit_batch(items, validation)
        assert len(results) == 3
        assert results[0].admitted is True   # ev-001
        assert results[1].admitted is False  # ev-002
        assert results[2].admitted is True   # ev-003

    @pytest.mark.asyncio
    async def test_each_item_judged_independently(self):
        """One item's rejection does not affect others."""
        ea = EvidenceAdmission()
        items = [
            {"item_id": "ev-001"},
            {"item_id": "ev-002", "ref": "hidden_challenge_set"},
            {"item_id": "ev-003"},
        ]
        results = await ea.admit_batch(items, {})
        assert results[0].admitted is True   # ev-001 passes
        assert results[1].admitted is False  # ev-002 has hidden ref
        assert results[2].admitted is True   # ev-003 passes independently


# ── Feedback desensitization (M2-C5) ────────────────────────────────


class TestFeedbackDesensitization:
    def test_same_format_hidden_set_rejection(self):
        """M2-C5: Same format for hidden_set rejection."""
        ea = EvidenceAdmission()
        results = [
            EvidenceAdmissionResult(item_id="ev-001", admitted=False, reason="hidden_set_source"),
        ]
        feedback = ea.desensitize_feedback(results)
        assert feedback["item_count"] == 1
        assert feedback["admitted_count"] == 0
        assert feedback["summary"] == "Batch processed"

    def test_same_format_public_set_rejection(self):
        """M2-C5: Same format for public_set rejection."""
        ea = EvidenceAdmission()
        results = [
            EvidenceAdmissionResult(item_id="ev-001", admitted=False, reason="validation_failed:public_set"),
        ]
        feedback = ea.desensitize_feedback(results)
        assert feedback["item_count"] == 1
        assert feedback["admitted_count"] == 0
        assert feedback["summary"] == "Batch processed"

    def test_desensitization_uniform_across_reasons(self):
        """Feedback is identical regardless of rejection reason."""
        ea = EvidenceAdmission()
        hidden_results = [
            EvidenceAdmissionResult(item_id="ev-001", admitted=False, reason="hidden_set_source"),
            EvidenceAdmissionResult(item_id="ev-002", admitted=True, reason="passed"),
        ]
        public_results = [
            EvidenceAdmissionResult(item_id="ev-001", admitted=False, reason="validation_failed:public_set"),
            EvidenceAdmissionResult(item_id="ev-002", admitted=True, reason="passed"),
        ]
        hidden_feedback = ea.desensitize_feedback(hidden_results)
        public_feedback = ea.desensitize_feedback(public_results)
        # Same shape and content — Lab cannot tell the difference
        assert hidden_feedback == public_feedback

    def test_desensitization_keys(self):
        """Feedback has expected keys and types."""
        ea = EvidenceAdmission()
        results = [
            EvidenceAdmissionResult(item_id="ev-001", admitted=True, reason="passed"),
        ]
        feedback = ea.desensitize_feedback(results)
        assert "item_count" in feedback
        assert "admitted_count" in feedback
        assert "summary" in feedback
        assert isinstance(feedback["item_count"], int)
        assert isinstance(feedback["admitted_count"], int)


# ── Empty batch ─────────────────────────────────────────────────────


class TestEmptyBatch:
    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty(self):
        """Empty batch -> empty results."""
        ea = EvidenceAdmission()
        results = await ea.admit_batch([], {})
        assert results == []

    def test_empty_batch_desensitize(self):
        """Empty batch desensitization."""
        ea = EvidenceAdmission()
        feedback = ea.desensitize_feedback([])
        assert feedback["item_count"] == 0
        assert feedback["admitted_count"] == 0
        assert feedback["summary"] == "Batch processed"
