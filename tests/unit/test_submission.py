"""Tests for SubmissionChain: Lab-to-Core candidate submission pipeline.

Key tests (Quality Gates):
- M3-C1: Lab tries to access Core internals -> all rejected
- M3-C2: Precheck rejects incomplete candidates, does NOT simulate HardGate
- M3-C3: Full submission chain with logging
- M3-C4: Feedback desensitization — cannot distinguish rejection reasons
"""
import pytest

from polytwin.lab.submission import SubmissionChain
from polytwin.lab.types import CandidateModelPackage


def _candidate(
    model_id: str = "model-1",
    lineage: str = "lineage-001",
) -> CandidateModelPackage:
    return CandidateModelPackage(
        model_id=model_id,
        architecture_description="Test model",
        training_data_lineage=lineage,
    )


class TestSubmissionPrecheck:
    """M3-C2: Precheck rejects incomplete candidates."""

    @pytest.mark.asyncio
    async def test_valid_candidate_passes(self):
        chain = SubmissionChain()
        result = await chain.submit([_candidate()])
        assert result.submission_id != ""

    @pytest.mark.asyncio
    async def test_missing_model_id_rejected(self):
        chain = SubmissionChain()
        candidate = CandidateModelPackage(
            model_id="",
            training_data_lineage="lineage-001",
        )
        result = await chain.submit([candidate])
        assert "precheck" in result.aggregate_summary.lower()

    @pytest.mark.asyncio
    async def test_missing_lineage_rejected(self):
        chain = SubmissionChain()
        candidate = CandidateModelPackage(
            model_id="model-1",
            training_data_lineage="",
        )
        result = await chain.submit([candidate])
        assert "precheck" in result.aggregate_summary.lower()

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid(self):
        chain = SubmissionChain()
        candidates = [
            _candidate("valid-1", "lineage-1"),
            CandidateModelPackage(model_id="", training_data_lineage="x"),
        ]
        result = await chain.submit(candidates)
        # Should process the valid one
        assert result.submission_id != ""

    @pytest.mark.asyncio
    async def test_all_invalid_rejected(self):
        chain = SubmissionChain()
        candidates = [
            CandidateModelPackage(model_id="", training_data_lineage="x"),
            CandidateModelPackage(model_id="y", training_data_lineage=""),
        ]
        result = await chain.submit(candidates)
        assert "precheck" in result.aggregate_summary.lower()


class TestSubmissionPrescreenLabel:
    """CandidateModelPackage always has prescreen label."""

    @pytest.mark.asyncio
    async def test_prescreen_label_preserved(self):
        SubmissionChain()
        candidate = _candidate()
        assert candidate.constraint_violation_report == "预筛结果，非权威"

    @pytest.mark.asyncio
    async def test_submission_is_prescreen(self):
        chain = SubmissionChain()
        result = await chain.submit([_candidate()])
        assert result.hidden_set_info_exposed is False


class TestFeedbackDesensitization:
    """M3-C4: Feedback desensitization — cannot distinguish rejection reasons."""

    @pytest.mark.asyncio
    async def test_hidden_set_info_never_exposed(self):
        chain = SubmissionChain()
        result = await chain.submit([_candidate()])
        assert result.hidden_set_info_exposed is False

    @pytest.mark.asyncio
    async def test_quarantine_rejection_desensitized(self):
        """When quarantine rejects, Lab sees same generic message."""
        from unittest.mock import AsyncMock

        from polytwin.core.quarantine import SubmissionQuarantine
        from polytwin.core.types import QuarantineRejection

        mock_quarantine = AsyncMock(spec=SubmissionQuarantine)
        mock_quarantine.submit.return_value = QuarantineRejection(
            rejected=True,
            reason="sensitive_info_detected",
            detail="Contains hidden_challenge_set reference",
        )

        chain = SubmissionChain(quarantine=mock_quarantine)
        result = await chain.submit([_candidate()])

        # Lab cannot see the real rejection reason
        assert result.hidden_set_info_exposed is False
        assert "hidden" not in result.aggregate_summary.lower()
        assert "sensitive" not in result.aggregate_summary.lower()

    @pytest.mark.asyncio
    async def test_quarantine_acceptance_response(self):
        """When quarantine accepts, response has same format."""
        from unittest.mock import AsyncMock

        from polytwin.core.quarantine import SubmissionQuarantine
        from polytwin.core.types import QuarantineRejection

        mock_quarantine = AsyncMock(spec=SubmissionQuarantine)
        mock_quarantine.submit.return_value = QuarantineRejection(
            rejected=False, reason="", detail=""
        )

        chain = SubmissionChain(quarantine=mock_quarantine)
        result = await chain.submit([_candidate()])

        assert result.hidden_set_info_exposed is False
        assert "Batch processed" in result.aggregate_summary


class TestFullSubmissionChain:
    """M3-C3: Full submission chain with logging."""

    @pytest.mark.asyncio
    async def test_submissions_have_unique_ids(self):
        chain = SubmissionChain()
        result1 = await chain.submit([_candidate("m1")])
        result2 = await chain.submit([_candidate("m2")])
        assert result1.submission_id != result2.submission_id

    @pytest.mark.asyncio
    async def test_item_results_populated_on_success(self):
        from unittest.mock import AsyncMock

        from polytwin.core.quarantine import SubmissionQuarantine
        from polytwin.core.types import QuarantineRejection

        mock_quarantine = AsyncMock(spec=SubmissionQuarantine)
        mock_quarantine.submit.return_value = QuarantineRejection(
            rejected=False, reason="", detail=""
        )

        chain = SubmissionChain(quarantine=mock_quarantine)
        result = await chain.submit([_candidate("m1"), _candidate("m2")])
        assert len(result.item_results) == 2
