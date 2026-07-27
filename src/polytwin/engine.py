"""PolymorphicTwinEngine: main entry point for the Polymorphic-Twin SDK.

This facade initialises and wires together all components (Core engine,
DomainPack registry, Lab explorer, Bridge orchestrator, IdentityMonitor)
behind a single easy-to-use interface. No new business logic lives here --
every call delegates to the appropriate component.
"""
from __future__ import annotations

import logging

from polytwin.bridge.orchestrator import BridgeOrchestrator
from polytwin.bridge.types import BridgeOutput
from polytwin.config import EngineConfig
from polytwin.core.audit import AuditLogWriter
from polytwin.core.engine import ConstraintEngine
from polytwin.core.identity_monitor import IdentityMonitor
from polytwin.core.types import IdentityCheckResult, ValidationResult
from polytwin.domainpack.registry import DomainPackRegistry
from polytwin.domainpack.types import DomainPack
from polytwin.lab.explorer import LabExplorer
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import ExplorationBudget, ExplorationResult
from polytwin.tom.facade import TwinObjectFacade

logger = logging.getLogger(__name__)


class PolymorphicTwinEngine:
    """Main entry point for the Polymorphic-Twin SDK.

    Usage::

        from polytwin import PolymorphicTwinEngine, EngineConfig

        config = EngineConfig()
        engine = PolymorphicTwinEngine(config)

        result = await engine.validate(state_values, constraint_cards)

    Args:
        config: Optional EngineConfig. Uses sensible defaults if not provided.
    """

    def __init__(self, config: EngineConfig | None = None) -> None:
        self._config = config or EngineConfig()

        # Core components
        self._audit = AuditLogWriter()
        from polytwin.tom.facade import InMemoryTwinObjectStore as FacadeStore

        self._store = FacadeStore()
        self._facade = TwinObjectFacade(self._store)
        self._engine = ConstraintEngine(audit_writer=self._audit)

        # DomainPack registry
        self._registry = DomainPackRegistry()

        # Optional Lab
        self._lab: LabExplorer | None = None
        if self._config.enable_lab:
            self._lab = LabExplorer(AlgorithmicStrategy())

        # Optional Bridge
        self._bridge_orchestrator: BridgeOrchestrator | None = None
        if self._config.enable_bridge:
            self._bridge_orchestrator = BridgeOrchestrator()

        # Identity monitor
        self._identity_monitor = IdentityMonitor({
            "identity_check_interval": self._config.identity_check_interval,
            "drift_tolerance": self._config.drift_tolerance,
        })

        # Load DomainPacks from configured directories
        for dp_dir in self._config.domain_pack_dirs:
            try:
                self._registry.load_from_directory(dp_dir)
            except FileNotFoundError:
                logger.debug("DomainPack directory not found, skipping: %s", dp_dir)

    # ── Core validation ────────────────────────────────────────────────

    async def validate(
        self,
        state_values: dict[str, float],
        constraint_cards: list[dict],
        identity_confidence: float = 1.0,
    ) -> ValidationResult:
        """Validate constraints against state values.

        Args:
            state_values: Current state variable values.
            constraint_cards: Constraint card dicts (from DomainPack or hand-crafted).
            identity_confidence: Confidence in TwinObject identity (0.0-1.0).

        Returns:
            ValidationResult with pass/fail outcome and details.
        """
        return await self._engine.validate(
            state_values, constraint_cards, identity_confidence
        )

    # ── Bridge ─────────────────────────────────────────────────────────

    async def get_action_space(
        self,
        view_data: dict,
        domain_pack_id: str | None = None,
    ) -> BridgeOutput:
        """Generate action space for decision making.

        Args:
            view_data: BridgeDecisionView-compatible data dict.
            domain_pack_id: Optional DomainPack to use for action templates.

        Returns:
            BridgeOutput with four-category action space.

        Raises:
            RuntimeError: If Bridge is disabled in config.
        """
        if self._bridge_orchestrator is None:
            raise RuntimeError("Bridge is disabled in EngineConfig (enable_bridge=False)")

        dp: DomainPack | None = None
        if domain_pack_id:
            dp = self._registry.get(domain_pack_id)

        return await self._bridge_orchestrator.generate_action_space(
            view_data,
            dp.model_dump() if dp else None,
        )

    # ── Lab ────────────────────────────────────────────────────────────

    async def run_exploration(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> ExplorationResult:
        """Run Lab exploration across all modes.

        Args:
            data: LabExplorationView-compatible data dict.
            constraints: Constraint card dicts visible to Lab.
            budget: Resource budget (uses defaults if None).

        Returns:
            ExplorationResult with findings, counterexamples, and hypotheses.

        Raises:
            RuntimeError: If Lab is disabled in config.
        """
        if self._lab is None:
            raise RuntimeError("Lab is disabled in EngineConfig (enable_lab=False)")

        return await self._lab.run_full_exploration(data, constraints, budget)

    # ── DomainPack ─────────────────────────────────────────────────────

    def get_domain_pack(self, domain_id: str) -> DomainPack | None:
        """Get a loaded DomainPack by ID.

        Args:
            domain_id: The domain_id field of the DomainPack.

        Returns:
            The DomainPack instance, or None if not found.
        """
        return self._registry.get(domain_id)

    def list_domain_packs(self) -> list[str]:
        """List all loaded DomainPack IDs.

        Returns:
            List of domain_id strings.
        """
        return self._registry.list_all()

    # ── Identity ───────────────────────────────────────────────────────

    async def check_identity(
        self, obj_id: str, invariants: dict
    ) -> IdentityCheckResult:
        """Check identity drift for a TwinObject.

        Args:
            obj_id: TwinObject identifier.
            invariants: Map of invariant_name -> {"expected": float, "actual": float}.

        Returns:
            IdentityCheckResult with status (confirmed/uncertain/forked) and drift values.
        """
        return await self._identity_monitor.check_identity(obj_id, invariants)

    # ── Configuration access ───────────────────────────────────────────

    @property
    def config(self) -> EngineConfig:
        """Return the engine configuration (read-only access)."""
        return self._config
