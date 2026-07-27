"""Dependency injection singletons for the Polymorphic-Twin API layer.

All components are instantiated once and reused across requests. In
test_mode, no external dependencies (PostgreSQL, filesystem) are required.
"""

from __future__ import annotations

from polytwin.bridge.human_response import HumanResponseHandler
from polytwin.bridge.orchestrator import BridgeOrchestrator
from polytwin.bridge.validity import ValidityManager
from polytwin.core.audit import AuditLogWriter
from polytwin.core.certification import ModelCertification
from polytwin.core.engine import ConstraintEngine
from polytwin.core.evidence import EvidenceAdmission
from polytwin.core.fallback import SafetyFallback
from polytwin.core.hardgate import HardGate
from polytwin.core.identity_monitor import IdentityMonitor
from polytwin.core.prescreen import PrescreenLibrary
from polytwin.core.quarantine import SubmissionQuarantine
from polytwin.domainpack.registry import DomainPackRegistry
from polytwin.lab.data_release import DataReleaseManager
from polytwin.lab.explorer import LabExplorer
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.submission import SubmissionChain
from polytwin.tom.facade import InMemoryTwinObjectStore, TwinObjectFacade

# ── Module-level singletons (replaced per-process) ──────────────────

_store: InMemoryTwinObjectStore | None = None
_facade: TwinObjectFacade | None = None
_engine: ConstraintEngine | None = None
_hardgate: HardGate | None = None
_fallback: SafetyFallback | None = None
_audit: AuditLogWriter | None = None
_quarantine: SubmissionQuarantine | None = None
_evidence: EvidenceAdmission | None = None
_identity_monitor: IdentityMonitor | None = None
_certification: ModelCertification | None = None
_prescreen: PrescreenLibrary | None = None
_registry: DomainPackRegistry | None = None
_explorer: LabExplorer | None = None
_data_release: DataReleaseManager | None = None
_submission_chain: SubmissionChain | None = None
_orchestrator: BridgeOrchestrator | None = None
_validity: ValidityManager | None = None
_human_response: HumanResponseHandler | None = None


def _reset() -> None:
    """Reset all singletons. Used between test sessions."""
    global _store, _facade, _engine, _hardgate, _fallback, _audit
    global _quarantine, _evidence, _identity_monitor, _certification
    global _prescreen, _registry, _explorer, _data_release
    global _submission_chain, _orchestrator, _validity, _human_response
    _store = None
    _facade = None
    _engine = None
    _hardgate = None
    _fallback = None
    _audit = None
    _quarantine = None
    _evidence = None
    _identity_monitor = None
    _certification = None
    _prescreen = None
    _registry = None
    _explorer = None
    _data_release = None
    _submission_chain = None
    _orchestrator = None
    _validity = None
    _human_response = None


def get_store() -> InMemoryTwinObjectStore:
    """Return the shared in-memory TwinObject store."""
    global _store
    if _store is None:
        _store = InMemoryTwinObjectStore()
    return _store


def get_facade() -> TwinObjectFacade:
    """Return the shared TwinObject facade."""
    global _facade
    if _facade is None:
        _facade = TwinObjectFacade(get_store())
    return _facade


def get_audit() -> AuditLogWriter:
    """Return the shared audit log writer."""
    global _audit
    if _audit is None:
        _audit = AuditLogWriter()
    return _audit


def get_fallback() -> SafetyFallback:
    """Return the shared safety fallback handler."""
    global _fallback
    if _fallback is None:
        _fallback = SafetyFallback()
    return _fallback


def get_engine() -> ConstraintEngine:
    """Return the shared constraint engine."""
    global _engine
    if _engine is None:
        _engine = ConstraintEngine(
            audit_writer=get_audit(),
            fallback_handler=get_fallback(),
        )
    return _engine


def get_hardgate() -> HardGate:
    """Return the shared HardGate instance."""
    global _hardgate
    if _hardgate is None:
        _hardgate = HardGate()
    return _hardgate


def get_quarantine() -> SubmissionQuarantine:
    """Return the shared submission quarantine."""
    global _quarantine
    if _quarantine is None:
        _quarantine = SubmissionQuarantine()
    return _quarantine


def get_evidence() -> EvidenceAdmission:
    """Return the shared evidence admission handler."""
    global _evidence
    if _evidence is None:
        _evidence = EvidenceAdmission()
    return _evidence


def get_identity_monitor() -> IdentityMonitor:
    """Return the shared identity monitor."""
    global _identity_monitor
    if _identity_monitor is None:
        _identity_monitor = IdentityMonitor()
    return _identity_monitor


def get_certification() -> ModelCertification:
    """Return the shared model certification manager."""
    global _certification
    if _certification is None:
        _certification = ModelCertification()
    return _certification


def get_prescreen() -> PrescreenLibrary:
    """Return the shared prescreen library."""
    global _prescreen
    if _prescreen is None:
        _prescreen = PrescreenLibrary()
    return _prescreen


def get_registry() -> DomainPackRegistry:
    """Return the shared DomainPack registry."""
    global _registry
    if _registry is None:
        _registry = DomainPackRegistry()
    return _registry


def get_explorer() -> LabExplorer:
    """Return the shared Lab explorer."""
    global _explorer
    if _explorer is None:
        _explorer = LabExplorer(strategy=AlgorithmicStrategy())
    return _explorer


def get_data_release() -> DataReleaseManager:
    """Return the shared data release manager."""
    global _data_release
    if _data_release is None:
        _data_release = DataReleaseManager()
    return _data_release


def get_submission_chain() -> SubmissionChain:
    """Return the shared submission chain."""
    global _submission_chain
    if _submission_chain is None:
        _submission_chain = SubmissionChain(quarantine=get_quarantine())
    return _submission_chain


def get_orchestrator() -> BridgeOrchestrator:
    """Return the shared Bridge orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BridgeOrchestrator()
    return _orchestrator


def get_validity() -> ValidityManager:
    """Return the shared validity manager."""
    global _validity
    if _validity is None:
        _validity = ValidityManager()
    return _validity


def get_human_response() -> HumanResponseHandler:
    """Return the shared human response handler."""
    global _human_response
    if _human_response is None:
        _human_response = HumanResponseHandler()
    return _human_response
