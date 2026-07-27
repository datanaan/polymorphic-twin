"""EngineConfig: master configuration for PolymorphicTwinEngine.

Aggregates all component-level configuration into a single Pydantic model
with sensible defaults. Every knob that the SDK exposes is declared here.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from polytwin.jelly.config import JellyConfig


class EngineConfig(BaseModel):
    """Master configuration for PolymorphicTwinEngine.

    Attributes:
        storage_backend: Storage type -- "memory" for development, "postgres" for production.
        database_url: Connection string for PostgreSQL (unused when storage_backend="memory").
        domain_pack_dirs: Directories scanned for DomainPack YAML/JSON files on startup.
        jelly: Jelly MCP integration configuration.
        identity_check_interval: Seconds between periodic identity checks.
        drift_tolerance: Maximum allowed drift ratio before triggering uncertain/forked.
        max_constraint_cards: Hard limit on constraint cards per validation batch.
        safety_fallback_timeout_ms: Maximum milliseconds for a safety fallback to complete.
        enable_lab: Whether to initialise the Lab exploration engine.
        enable_bridge: Whether to initialise the Bridge decision interface.
        enable_audit: Whether to initialise the audit log writer.
    """

    # Storage
    storage_backend: str = "memory"  # "memory" | "postgres"
    database_url: str = ""

    # DomainPack
    domain_pack_dirs: list[str] = Field(default_factory=lambda: ["configs/examples"])

    # Jelly (optional external data)
    jelly: JellyConfig = Field(default_factory=JellyConfig)

    # Identity Monitor
    identity_check_interval: float = 1.0
    drift_tolerance: float = 0.05

    # Performance
    max_constraint_cards: int = 100
    safety_fallback_timeout_ms: int = 200

    # Features
    enable_lab: bool = True
    enable_bridge: bool = True
    enable_audit: bool = True
