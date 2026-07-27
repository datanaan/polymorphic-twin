"""Submission chain: Lab-to-Core candidate submission pipeline.

Full chain: candidate -> CoreCompatibilityPrecheck -> pack -> quarantine -> feedback.

Key invariants:
- M3-C2: Precheck rejects incomplete candidates but does NOT simulate HardGate.
- M3-C3: Full submission chain with logging.
- M3-C4: Feedback desensitization — Lab cannot distinguish rejection reasons.
"""
from __future__ import annotations

import logging
import uuid

from polytwin.core.quarantine import SubmissionQuarantine
from polytwin.lab.types import (
    CandidateModelPackage,
    LabSubmission,
    LabSubmissionResponse,
)
from polytwin.tom.types import CallerIdentity

logger = logging.getLogger(__name__)


class SubmissionChain:
    """Lab-to-Core submission pipeline.

    Handles candidate packaging, format precheck, quarantine submission,
    and desensitized feedback.
    """

    def __init__(self, quarantine: SubmissionQuarantine | None = None) -> None:
        self._quarantine = quarantine or SubmissionQuarantine()
        self._caller = CallerIdentity(component="lab", role="explorer")

    async def submit(
        self,
        candidates: list[CandidateModelPackage],
    ) -> LabSubmissionResponse:
        """M3-C3: Full submission chain with desensitized feedback.

        Steps:
            1. Precheck each candidate for format completeness (M3-C2).
            2. Pack valid candidates into a LabSubmission.
            3. Submit to quarantine.
            4. Return desensitized feedback (M3-C4).

        Args:
            candidates: List of CandidateModelPackage to submit.

        Returns:
            LabSubmissionResponse with hidden_set_info_exposed=False.
        """
        submission_id = str(uuid.uuid4())

        # Step 1: Precheck
        valid = [c for c in candidates if self._precheck(c)]

        if not valid:
            logger.info("All candidates rejected by precheck for submission %s", submission_id)
            return LabSubmissionResponse(
                submission_id=submission_id,
                aggregate_summary="All candidates rejected by precheck",
                hidden_set_info_exposed=False,
            )

        # Step 2: Pack
        submission = LabSubmission(
            submission_id=submission_id,
            items=valid,
            is_prescreen=True,
        )

        # Build quarantine-compatible payload
        payload = self._build_quarantine_payload(submission)

        # Step 3: Submit to quarantine
        result = await self._quarantine.submit(payload, self._caller)

        # Step 4: Desensitized feedback (M3-C4)
        if result.rejected:
            logger.info(
                "Submission %s quarantined: %s", submission_id, result.reason
            )
            return LabSubmissionResponse(
                submission_id=submission_id,
                aggregate_summary="Batch processed",
                hidden_set_info_exposed=False,
            )

        logger.info("Submission %s accepted", submission_id)
        return LabSubmissionResponse(
            submission_id=submission_id,
            aggregate_summary="Batch processed",
            item_results=[{"model_id": c.model_id, "status": "submitted"} for c in valid],
            hidden_set_info_exposed=False,
        )

    def _precheck(self, candidate: CandidateModelPackage) -> bool:
        """M3-C2: Format completeness check.

        Validates that the candidate has required fields. Does NOT
        simulate HardGate or Core validation logic.
        """
        if not candidate.model_id:
            return False
        return bool(candidate.training_data_lineage)

    @staticmethod
    def _build_quarantine_payload(submission: LabSubmission) -> dict:
        """Build a quarantine-compatible payload from a LabSubmission.

        The quarantine requires: hypothesis_id, lineage, domain_id.
        """
        items_data = [item.model_dump() for item in submission.items]
        return {
            "hypothesis_id": submission.submission_id,
            "lineage": items_data[0].get("training_data_lineage", "") if items_data else "",
            "domain_id": "lab_exploration",
            "payload": items_data,
            "is_prescreen": True,
        }
