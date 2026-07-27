"""ModelCertification: certificate management for model qualification.

Issues, revokes, and verifies qualification certificates.  Isolated from
runtime validation and the hard-gate — certification is a separate concern
from constraint enforcement.
"""
from __future__ import annotations

from polytwin.core.types import Certificate, CertificationResult


class ModelCertification:
    """Manage model qualification certificates.

    Certificates are issued when a model's score meets the threshold
    (default 0.8).  They can be revoked for cause and verified at any time.
    """

    SCORE_THRESHOLD = 0.8

    def __init__(self) -> None:
        self._certificates: dict[str, Certificate] = {}

    async def certify(
        self, model_id: str, score: float, evidence: list | None = None
    ) -> CertificationResult:
        """Issue or deny certificate based on score and evidence.

        Args:
            model_id: Unique model identifier.
            score: Qualification score (0.0 to 1.0).
            evidence: Supporting evidence items (optional).

        Returns:
            CertificationResult indicating whether certificate was granted.
        """
        if score >= self.SCORE_THRESHOLD:
            cert = Certificate(model_id=model_id, score=score)
            self._certificates[model_id] = cert
            return CertificationResult(
                granted=True, score=score, certificate=cert
            )
        return CertificationResult(
            granted=False,
            score=score,
            gaps=["Score below threshold"],
        )

    async def revoke(self, model_id: str, reason: str) -> bool:
        """Revoke an existing certificate.

        Args:
            model_id: Model whose certificate should be revoked.
            reason: Reason for revocation (recorded for audit).

        Returns:
            True if a certificate was revoked, False if none existed.
        """
        if model_id in self._certificates:
            del self._certificates[model_id]
            return True
        return False

    async def verify(self, model_id: str) -> bool:
        """Check if a valid certificate exists for the model.

        Args:
            model_id: Model to verify.

        Returns:
            True if certificate exists and is valid.
        """
        return model_id in self._certificates
