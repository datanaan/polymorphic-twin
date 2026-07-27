"""SubmissionQuarantine: Lab submission entry point with three-step check.

Ensures that Lab submissions are structurally valid, within resource
limits, and free of sensitive information before they enter the Core
processing pipeline.
"""
from __future__ import annotations

from polytwin.core.types import QuarantineRejection
from polytwin.tom.types import CallerIdentity

# Maximum submission payload size in bytes (10 MB).
_MAX_PAYLOAD_BYTES = 10 * 1024 * 1024

# Keywords that indicate sensitive/hidden information.
_SENSITIVE_KEYWORDS = frozenset({
    "hidden_challenge_set",
    "hidden_validation_set",
    "audit_benchmark_reference",
    "production_acceptance_reference",
})


class SubmissionQuarantine:
    """Three-step quarantine check for Lab submissions.

    Steps:
        1. Format integrity — required fields present.
        2. Resource check — payload within size limits.
        3. Sensitive info scan — no prohibited keywords.
    """

    async def submit(
        self,
        submission: dict,
        caller: CallerIdentity,
    ) -> QuarantineRejection:
        """Run three-step quarantine check.

        Args:
            submission: The Lab submission payload.
            caller: Identity of the calling component.

        Returns:
            QuarantineRejection with ``rejected=False`` on success,
            or ``rejected=True`` with reason on failure.
        """
        # Caller identity gate: only Lab callers are accepted
        if caller.component != "lab":
            return QuarantineRejection(
                rejected=True,
                reason="caller_not_authorized",
                detail=f"Component '{caller.component}' is not authorized for submission.",
            )

        # Step 1: Format integrity
        if not self._check_format(submission):
            return QuarantineRejection(
                rejected=True,
                reason="format_integrity",
                detail="Submission missing required fields (hypothesis_id, lineage, or domain_id).",
            )

        # Step 2: Resource check
        if not self._check_resources(submission):
            return QuarantineRejection(
                rejected=True,
                reason="payload_too_large",
                detail=f"Submission payload exceeds {_MAX_PAYLOAD_BYTES} bytes.",
            )

        # Step 3: Sensitive info scan
        if not self._scan_sensitive_info(submission):
            return QuarantineRejection(
                rejected=True,
                reason="sensitive_info_detected",
                detail="Submission contains references to sensitive/hidden information.",
            )

        return QuarantineRejection(rejected=False, reason="", detail="")

    # ── Step 1: Format integrity ───────────────────────────────────────
    @staticmethod
    def _check_format(submission: dict) -> bool:
        """Verify required fields are present in the submission."""
        required_fields = {"hypothesis_id", "lineage", "domain_id"}
        return required_fields.issubset(submission.keys())

    # ── Step 2: Resource check ─────────────────────────────────────────
    @staticmethod
    def _check_resources(submission: dict) -> bool:
        """Verify submission payload is within size limits."""
        payload = submission.get("payload", submission)
        # Measure the actual content size, not just the dict wrapper.
        total = 0
        stack = [payload]
        while stack:
            obj = stack.pop()
            if isinstance(obj, (str, bytes)):
                total += len(obj)
                if total > _MAX_PAYLOAD_BYTES:
                    return False
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    stack.append(k)
                    stack.append(v)
            elif isinstance(obj, (list, tuple)):
                stack.extend(obj)
        return total <= _MAX_PAYLOAD_BYTES

    # ── Step 3: Sensitive info scan ────────────────────────────────────
    @staticmethod
    def _scan_sensitive_info(submission: dict) -> bool:
        """Scan submission for sensitive information references."""
        text = str(submission).lower()
        return all(keyword not in text for keyword in _SENSITIVE_KEYWORDS)
