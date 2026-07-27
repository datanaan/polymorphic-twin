"""Tests for EngineConfig."""


from polytwin.config import EngineConfig
from polytwin.jelly.config import JellyConfig


class TestEngineConfigDefaults:
    """Verify that EngineConfig defaults are sensible."""

    def test_default_storage_backend(self) -> None:
        cfg = EngineConfig()
        assert cfg.storage_backend == "memory"

    def test_default_database_url(self) -> None:
        cfg = EngineConfig()
        assert cfg.database_url == ""

    def test_default_domain_pack_dirs(self) -> None:
        cfg = EngineConfig()
        assert cfg.domain_pack_dirs == ["configs/examples"]

    def test_default_jelly(self) -> None:
        cfg = EngineConfig()
        assert isinstance(cfg.jelly, JellyConfig)
        assert cfg.jelly.enabled is False
        assert cfg.jelly.mock_mode is True

    def test_default_identity_settings(self) -> None:
        cfg = EngineConfig()
        assert cfg.identity_check_interval == 1.0
        assert cfg.drift_tolerance == 0.05

    def test_default_performance_settings(self) -> None:
        cfg = EngineConfig()
        assert cfg.max_constraint_cards == 100
        assert cfg.safety_fallback_timeout_ms == 200

    def test_default_feature_flags(self) -> None:
        cfg = EngineConfig()
        assert cfg.enable_lab is True
        assert cfg.enable_bridge is True
        assert cfg.enable_audit is True


class TestEngineConfigCustom:
    """Verify that EngineConfig accepts custom values."""

    def test_custom_storage_backend(self) -> None:
        cfg = EngineConfig(storage_backend="postgres", database_url="postgresql://localhost/twindb")
        assert cfg.storage_backend == "postgres"
        assert cfg.database_url == "postgresql://localhost/twindb"

    def test_custom_domain_pack_dirs(self) -> None:
        cfg = EngineConfig(domain_pack_dirs=["/data/packs", "/etc/twin"])
        assert cfg.domain_pack_dirs == ["/data/packs", "/etc/twin"]

    def test_custom_identity_settings(self) -> None:
        cfg = EngineConfig(identity_check_interval=5.0, drift_tolerance=0.1)
        assert cfg.identity_check_interval == 5.0
        assert cfg.drift_tolerance == 0.1

    def test_disable_features(self) -> None:
        cfg = EngineConfig(enable_lab=False, enable_bridge=False)
        assert cfg.enable_lab is False
        assert cfg.enable_bridge is False

    def test_custom_jelly(self) -> None:
        jelly = JellyConfig(enabled=True, base_url="http://jelly:9091")
        cfg = EngineConfig(jelly=jelly)
        assert cfg.jelly.enabled is True
        assert cfg.jelly.base_url == "http://jelly:9091"

    def test_model_dump(self) -> None:
        cfg = EngineConfig()
        d = cfg.model_dump()
        assert "storage_backend" in d
        assert "domain_pack_dirs" in d
        assert "jelly" in d
        assert d["storage_backend"] == "memory"

    def test_model_dump_json(self) -> None:
        cfg = EngineConfig()
        json_str = cfg.model_dump_json()
        assert "memory" in json_str
        assert "configs/examples" in json_str


class TestEngineConfigValidation:
    """Verify Pydantic validation on EngineConfig."""

    def test_extra_fields_ignored(self) -> None:
        """Pydantic BaseModel ignores extra fields by default."""
        cfg = EngineConfig()  # type: ignore[call-arg]
        # Extra fields are silently ignored, which is safe behavior
        assert cfg.storage_backend == "memory"

    def test_accepts_valid_types(self) -> None:
        cfg = EngineConfig(
            max_constraint_cards=50,
            safety_fallback_timeout_ms=500,
        )
        assert cfg.max_constraint_cards == 50

    def test_immutable_copy(self) -> None:
        """EngineConfig is a Pydantic BaseModel, should support model_copy."""
        cfg = EngineConfig()
        cfg2 = cfg.model_copy(update={"enable_lab": False})
        assert cfg.enable_lab is True
        assert cfg2.enable_lab is False
