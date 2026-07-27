"""Tests for JellyClient mock mode, JellyConfig defaults, and exception hierarchy."""


import pytest

from polytwin.jelly import JellyClient, JellyConfig
from polytwin.jelly.exceptions import (
    JellyConnectionError,
    JellyDataAlignmentError,
    JellyDomainPackNotFoundError,
    JellyError,
    JellyPermissionDeniedError,
    JellyServiceUnavailableError,
)
from polytwin.jelly.mock import MockProvider

EXAMPLES_DIR = "configs/examples"
KNOWN_DOMAIN_ID = "example.minimal_device_monitor"


# ── JellyConfig defaults ───────────────────────────────────────────


class TestJellyConfigDefaults:
    def test_defaults(self):
        cfg = JellyConfig()
        assert cfg.enabled is False
        assert cfg.base_url == "http://localhost:9091"
        assert cfg.timeout_seconds == 5.0
        assert cfg.auth_token is None
        assert cfg.max_retries == 3
        assert cfg.retry_backoff == [1.0, 2.0, 4.0]
        assert cfg.mock_mode is True
        assert cfg.mock_data_dir == "configs/examples"
        assert cfg.enable_secondary_filter is True


# ── MockProvider ────────────────────────────────────────────────────


class TestMockProvider:
    def test_get_domain_pack_found(self):
        provider = MockProvider(EXAMPLES_DIR)
        result = provider.get_domain_pack(KNOWN_DOMAIN_ID)
        assert result is not None
        assert result["domain_id"] == KNOWN_DOMAIN_ID
        assert "constraint_cards" in result

    def test_get_domain_pack_not_found(self):
        provider = MockProvider(EXAMPLES_DIR)
        assert provider.get_domain_pack("nonexistent.domain") is None

    def test_search_by_keyword(self):
        provider = MockProvider(EXAMPLES_DIR)
        results = provider.search_domain_packs(["minimal"])
        assert len(results) >= 1
        assert any(r["domain_id"] == KNOWN_DOMAIN_ID for r in results)

    def test_search_no_match(self):
        provider = MockProvider(EXAMPLES_DIR)
        results = provider.search_domain_packs(["zzz_no_such_keyword"])
        assert results == []

    def test_health_check_dir_exists(self):
        provider = MockProvider(EXAMPLES_DIR)
        assert provider.health_check() is True

    def test_health_check_dir_missing(self):
        provider = MockProvider("/no/such/directory/ever")
        assert provider.health_check() is False

    def test_get_domain_pack_missing_dir(self):
        provider = MockProvider("/no/such/directory/ever")
        assert provider.get_domain_pack(KNOWN_DOMAIN_ID) is None


# ── JellyClient (mock mode) ────────────────────────────────────────


class TestJellyClientMockMode:
    def test_get_domain_pack(self):
        client = JellyClient(JellyConfig(mock_data_dir=EXAMPLES_DIR))
        result = client.get_domain_pack(KNOWN_DOMAIN_ID)
        assert result is not None
        assert result["domain_id"] == KNOWN_DOMAIN_ID

    def test_get_domain_pack_unknown_returns_none(self):
        client = JellyClient(JellyConfig(mock_data_dir=EXAMPLES_DIR))
        assert client.get_domain_pack("unknown.id") is None

    def test_search_domain_packs(self):
        client = JellyClient(JellyConfig(mock_data_dir=EXAMPLES_DIR))
        results = client.search_domain_packs(["minimal"])
        assert len(results) >= 1

    def test_health_check_true(self):
        client = JellyClient(JellyConfig(mock_data_dir=EXAMPLES_DIR))
        assert client.health_check() is True

    def test_health_check_false(self):
        client = JellyClient(JellyConfig(mock_data_dir="/no/such/dir"))
        assert client.health_check() is False

    def test_close_is_noop(self):
        client = JellyClient(JellyConfig(mock_data_dir=EXAMPLES_DIR))
        client.close()  # should not raise


# ── JellyClient (non-mock mode stubs) ──────────────────────────────


class TestJellyClientNonMock:
    def test_get_domain_pack_returns_none(self):
        client = JellyClient(JellyConfig(mock_mode=False))
        assert client.get_domain_pack(KNOWN_DOMAIN_ID) is None

    def test_search_returns_empty(self):
        client = JellyClient(JellyConfig(mock_mode=False))
        assert client.search_domain_packs(["anything"]) == []

    def test_health_check_returns_false(self):
        client = JellyClient(JellyConfig(mock_mode=False))
        assert client.health_check() is False


# ── Exception hierarchy ────────────────────────────────────────────


class TestExceptionHierarchy:
    @pytest.mark.parametrize(
        "exc_cls",
        [
            JellyConnectionError,
            JellyDomainPackNotFoundError,
            JellyPermissionDeniedError,
            JellyDataAlignmentError,
            JellyServiceUnavailableError,
        ],
    )
    def test_inherits_from_jelly_error(self, exc_cls):
        assert issubclass(exc_cls, JellyError)

    def test_jelly_error_inherits_from_exception(self):
        assert issubclass(JellyError, Exception)

    def test_can_catch_all_with_base(self):
        with pytest.raises(JellyError):
            raise JellyConnectionError("boom")

        with pytest.raises(JellyError):
            raise JellyDomainPackNotFoundError("missing")
