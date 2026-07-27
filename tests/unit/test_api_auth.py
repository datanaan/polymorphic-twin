"""Tests for the API key management and Bearer token authentication."""
from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from polytwin.api.auth import APIKey, APIKeyManager, get_current_user

# ── APIKeyManager unit tests ──────────────────────────────────────────


class TestCreateKey:
    """APIKeyManager.create_key returns key_id and raw_key."""

    def test_returns_key_id_with_ptk_prefix(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        assert key_id.startswith("ptk_")

    def test_returns_non_empty_raw_key(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        assert len(raw_key) > 0

    def test_key_id_and_raw_key_are_distinct(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        assert key_id != raw_key

    def test_stores_key_with_given_role(self) -> None:
        mgr = APIKeyManager()
        key_id, _ = mgr.create_key(role="viewer", name="test-key")
        stored = mgr._keys[key_id]
        assert stored.role == "viewer"
        assert stored.name == "test-key"

    def test_each_call_produces_unique_key_id(self) -> None:
        mgr = APIKeyManager()
        ids = {mgr.create_key(role="admin")[0] for _ in range(10)}
        assert len(ids) == 10


class TestVerifyKey:
    """APIKeyManager.verify_key validates raw keys."""

    def test_valid_key_returns_api_key(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="operator")
        result = mgr.verify_key(raw_key)
        assert result is not None
        assert result.key_id == key_id
        assert result.role == "operator"

    def test_invalid_key_returns_none(self) -> None:
        mgr = APIKeyManager()
        mgr.create_key(role="admin")
        result = mgr.verify_key("completely_wrong_key")
        assert result is None

    def test_wrong_key_returns_none(self) -> None:
        mgr = APIKeyManager()
        mgr.create_key(role="admin")
        _, other_raw = mgr.create_key(role="viewer")
        # We need a key that doesn't match any stored hash
        result = mgr.verify_key("not_a_real_key_at_all")
        assert result is None


class TestRevokeKey:
    """APIKeyManager.revoke_key deactivates keys."""

    def test_revoke_makes_verify_return_none(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        assert mgr.verify_key(raw_key) is not None
        mgr.revoke_key(key_id)
        assert mgr.verify_key(raw_key) is None

    def test_revoke_returns_true_for_existing_key(self) -> None:
        mgr = APIKeyManager()
        key_id, _ = mgr.create_key(role="admin")
        assert mgr.revoke_key(key_id) is True

    def test_revoke_returns_false_for_unknown_key(self) -> None:
        mgr = APIKeyManager()
        assert mgr.revoke_key("ptk_nonexistent") is False


class TestKeyHash:
    """Key hash is SHA-256 of the raw key."""

    def test_stored_hash_matches_sha256(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        stored = mgr._keys[key_id]
        assert stored.key_hash == expected_hash

    def test_hash_is_64_hex_chars(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        stored = mgr._keys[key_id]
        assert len(stored.key_hash) == 64
        assert all(c in "0123456789abcdef" for c in stored.key_hash)


# ── Bearer token middleware tests ─────────────────────────────────────


class TestGetCurrentUser:
    """get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_api_key(self) -> None:
        mgr = APIKeyManager()
        _, raw_key = mgr.create_key(role="admin", name="bearer-test")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_key)
        result = await get_current_user(credentials=creds, key_manager=mgr)
        assert isinstance(result, APIKey)
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        mgr = APIKeyManager()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, key_manager=mgr)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_token_raises_401(self) -> None:
        mgr = APIKeyManager()
        key_id, raw_key = mgr.create_key(role="admin")
        mgr.revoke_key(key_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_key)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, key_manager=mgr)
        assert exc_info.value.status_code == 401
