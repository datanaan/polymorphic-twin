"""API key management and Bearer token authentication middleware.

Provides APIKey creation, verification, and revocation, plus a FastAPI
dependency that extracts and validates Bearer tokens from requests.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

if TYPE_CHECKING:
    pass

security = HTTPBearer()


class APIKey(BaseModel):
    """Stored representation of an API key.

    The raw key is never stored; only its SHA-256 hash is kept.
    """

    key_id: str
    key_hash: str  # SHA-256 of the actual key
    role: str  # admin, operator, viewer, lab_operator, bridge_operator
    name: str = ""
    active: bool = True


class APIKeyManager:
    """In-memory manager for API keys.

    Supports creating, verifying, and revoking keys. The raw key is
    available only at creation time and is never stored.
    """

    def __init__(self) -> None:
        self._keys: dict[str, APIKey] = {}

    def create_key(self, role: str, name: str = "") -> tuple[str, str]:
        """Create a new API key.

        Args:
            role: One of admin, operator, viewer, lab_operator, bridge_operator.
            name: Optional human-readable label.

        Returns:
            Tuple of (key_id, raw_key). The raw_key is only available here.
        """
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = f"ptk_{secrets.token_hex(8)}"
        api_key = APIKey(key_id=key_id, key_hash=key_hash, role=role, name=name)
        self._keys[key_id] = api_key
        return key_id, raw_key

    def verify_key(self, raw_key: str) -> APIKey | None:
        """Verify an API key and return the matching APIKey object.

        Args:
            raw_key: The bearer token presented by the caller.

        Returns:
            The APIKey if valid and active, otherwise None.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        for api_key in self._keys.values():
            if api_key.key_hash == key_hash and api_key.active:
                return api_key
        return None

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by key_id.

        Args:
            key_id: The key identifier (ptk_...) to revoke.

        Returns:
            True if the key was found and deactivated, False otherwise.
        """
        if key_id in self._keys:
            self._keys[key_id].active = False
            return True
        return False


# ── Module-level singleton ────────────────────────────────────────────

_key_manager: APIKeyManager | None = None


def get_key_manager() -> APIKeyManager:
    """Return the shared APIKeyManager singleton."""
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def reset_key_manager() -> None:
    """Reset the APIKeyManager singleton. Used between test sessions."""
    global _key_manager
    _key_manager = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),  # noqa: B008
    key_manager: APIKeyManager = Depends(get_key_manager),  # noqa: B008
) -> APIKey:
    """FastAPI dependency: extract and verify Bearer token.

    Raises:
        HTTPException: 401 if the token is invalid or the key is inactive.
    """
    api_key = key_manager.verify_key(credentials.credentials)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
