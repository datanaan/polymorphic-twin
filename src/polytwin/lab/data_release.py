"""DataReleaseManager: Core-to-Lab data channel.

Manages the controlled release of data from Core to Lab. The key
invariant is that hidden validation sets are NEVER exposed through
this interface. The method ``get_hidden_challenge_set()`` does NOT
exist on this class.
"""
from __future__ import annotations


class DataReleaseManager:
    """Manages data flow from Core to Lab.

    Only LabExplorationView-compatible data is released. Hidden
    validation sets (audit_benchmark_reference, production_acceptance_reference)
    are never accessible through this interface.
    """

    async def release_failure_logs(self, dp_id: str) -> dict:
        """Release desensitized failure logs for a DomainPack.

        Args:
            dp_id: DomainPack identifier.

        Returns:
            Dict with desensitized failure logs.
        """
        return {"logs": [], "domain_pack_id": dp_id}

    async def get_authorized_data(self, dp_id: str) -> dict:
        """Get authorized exploration data for a DomainPack.

        Returns data that conforms to LabExplorationView projection.
        Hidden validation sets and certifier logic are excluded.

        Args:
            dp_id: DomainPack identifier.

        Returns:
            Dict with LabExplorationView-compatible records.
        """
        return {"domain_pack_id": dp_id, "records": []}

    async def get_public_eval_set(self, dp_id: str) -> list[dict]:
        """Get the public evaluation set for a DomainPack.

        Hidden validation sets are NEVER accessible. This method
        only returns the public evaluation set that Lab is allowed
        to see.

        Args:
            dp_id: DomainPack identifier.

        Returns:
            List of public evaluation records.
        """
        return []

    async def get_constraint_summary(self, dp_id: str) -> list[dict]:
        """Get constraint card summaries (LabExplorationView projection).

        Returns constraint summaries WITHOUT certifier logic, thresholds,
        or hidden validation sets.

        Args:
            dp_id: DomainPack identifier.

        Returns:
            List of constraint summary dicts.
        """
        return []

    def validate_no_hidden_exposure(self, data: dict) -> bool:
        """Verify that data contains no hidden validation set references.

        Args:
            data: Data to check.

        Returns:
            True if no hidden references are found.
        """
        hidden_keywords = {
            "audit_benchmark_reference",
            "production_acceptance_reference",
            "hidden_challenge_set",
            "hidden_validation_set",
        }
        text = str(data).lower()
        return not any(kw in text for kw in hidden_keywords)
