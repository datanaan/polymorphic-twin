"""EvidenceAdmission: item-level independent judgment with feedback desensitization.

Admits or rejects individual evidence items from Lab submissions.
Each item is judged independently (M2-C4), and feedback is
desensitized so Lab cannot distinguish rejection reasons (M2-C5).
"""
from __future__ import annotations

from polytwin.core.types import EvidenceAdmissionResult

# Fields that indicate hidden/audit validation sets — items referencing
# these must be rejected.
_HIDDEN_REFERENCES = frozenset({
    "hidden_challenge_set",
    "hidden_validation_set",
    "audit_benchmark_reference",
    "production_acceptance_reference",
})


class EvidenceAdmission:
    """Item-level evidence admission with desensitized feedback.

    Design principles:
    - M2-C4: Each item is judged independently — one item's rejection
      does not affect another item's outcome.
    - M2-C5: Feedback is desensitized — Lab cannot distinguish whether
      an item was rejected because of a hidden_set violation or a
      public_set violation.
    """

    async def admit_batch(
        self,
        items: list[dict],
        validation_results: dict,
    ) -> list[EvidenceAdmissionResult]:
        """M2-C4: Item-level independence — each item judged independently.

        Args:
            items: List of evidence item dicts.  Each should have at
                   least an ``item_id`` field.
            validation_results: Dict mapping item_id -> validation
                outcome.  May include ``source`` (``"hidden_set"`` or
                ``"public_set"``) and ``passed`` (bool).

        Returns:
            List of EvidenceAdmissionResult, one per item, in order.
        """
        results = []
        for item in items:
            result = self._admit_single(item, validation_results)
            results.append(result)
        return results

    def _admit_single(
        self,
        item: dict,
        validation_results: dict,
    ) -> EvidenceAdmissionResult:
        """Judge a single evidence item for admission.

        Rejection reasons (kept internal — not exposed to Lab):
        - Item references hidden validation sets.
        - Validation result indicates failure on hidden set.
        - Item is missing required fields.
        """
        item_id = item.get("item_id", "")
        if not item_id:
            return EvidenceAdmissionResult(
                item_id="",
                admitted=False,
                reason="missing_item_id",
            )

        # Check for hidden references in the item itself
        item_text = str(item).lower()
        for ref in _HIDDEN_REFERENCES:
            if ref in item_text:
                return EvidenceAdmissionResult(
                    item_id=item_id,
                    admitted=False,
                    reason="hidden_reference_detected",
                )

        # Check validation results for this item
        item_validation = validation_results.get(item_id, {})
        if isinstance(item_validation, dict):
            passed = item_validation.get("passed", True)
            source = item_validation.get("source", "")

            if not passed:
                return EvidenceAdmissionResult(
                    item_id=item_id,
                    admitted=False,
                    reason=f"validation_failed:{source}",
                )

            # Reject if source is hidden_set (even if passed=True,
            # hidden_set results must not be admitted through normal
            # channels — they are Core-internal)
            if source == "hidden_set":
                return EvidenceAdmissionResult(
                    item_id=item_id,
                    admitted=False,
                    reason="hidden_set_source",
                )

        return EvidenceAdmissionResult(
            item_id=item_id,
            admitted=True,
            reason="passed_all_checks",
        )

    def desensitize_feedback(
        self,
        results: list[EvidenceAdmissionResult],
    ) -> dict:
        """M2-C5: Desensitize feedback — Lab cannot distinguish rejection reasons.

        Returns a uniform summary regardless of why items were rejected.
        The format is identical whether items were rejected for hidden_set
        reasons, public_set reasons, or format issues.
        """
        return {
            "item_count": len(results),
            "admitted_count": sum(1 for r in results if r.admitted),
            "summary": "Batch processed",
        }
