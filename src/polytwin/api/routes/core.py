"""Core routes: constraint validation, hard-gate, quarantine, fallback, and audit.

These endpoints expose the Core constraint governance engine.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from polytwin.api.deps import (
    get_audit,
    get_certification,
    get_engine,
    get_evidence,
    get_fallback,
    get_hardgate,
    get_identity_monitor,
    get_prescreen,
    get_quarantine,
)
from polytwin.tom.types import CallerIdentity

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────


class ValidateRequest(BaseModel):
    """Request body for constraint validation."""

    state_values: dict[str, float] = Field(default_factory=dict)
    constraint_cards: list[dict] = Field(default_factory=list)
    identity_confidence: float = 1.0
    sensor_status: dict | None = None
    domain_pack: dict | None = None


class HardGateRequest(BaseModel):
    """Request body for HardGate evaluation."""

    obj_view: dict = Field(default_factory=dict)
    constraints: list[dict] = Field(default_factory=list)
    domain_pack: dict = Field(default_factory=dict)


class QuarantineSubmitRequest(BaseModel):
    """Request body for quarantine submission."""

    submission: dict = Field(default_factory=dict)
    caller_component: str = "lab"
    caller_role: str = "explorer"
    caller_session_id: str | None = None


class FallbackExecuteRequest(BaseModel):
    """Request body for safety fallback execution."""

    obj: dict = Field(default_factory=dict)
    constraint_result: dict = Field(default_factory=dict)
    domain_pack: dict = Field(default_factory=dict)


class CertifyRequest(BaseModel):
    """Request body for model certification."""

    model_id: str
    score: float
    evidence: list | None = None


class EvidenceAdmitRequest(BaseModel):
    """Request body for evidence admission."""

    items: list[dict] = Field(default_factory=list)
    validation_results: dict = Field(default_factory=dict)


class IdentityCheckRequest(BaseModel):
    """Request body for identity drift check."""

    obj_id: str
    invariants: dict = Field(default_factory=dict)


class AuditQueryRequest(BaseModel):
    """Request body for audit trail query."""

    filters: dict | None = None


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/validate")
async def validate(body: ValidateRequest) -> dict:
    """Run constraint validation through the Core engine."""
    engine = get_engine()
    # Override domain_pack if provided
    if body.domain_pack:
        engine.domain_pack = body.domain_pack
    result = await engine.validate(
        state_values=body.state_values,
        constraint_cards=body.constraint_cards,
        identity_confidence=body.identity_confidence,
        sensor_status=body.sensor_status,
    )
    return result.model_dump()


@router.post("/hardgate")
async def hardgate(body: HardGateRequest) -> dict:
    """Run HardGate six-check evaluation."""
    gate = get_hardgate()
    result = await gate.evaluate(
        obj_view=body.obj_view,
        constraints=body.constraints,
        domain_pack=body.domain_pack,
    )
    return result.model_dump()


@router.post("/quarantine/submit")
async def quarantine_submit(body: QuarantineSubmitRequest) -> dict:
    """Submit a Lab payload to the quarantine check."""
    quarantine = get_quarantine()
    caller = CallerIdentity(
        component=body.caller_component,
        role=body.caller_role,
        session_id=body.caller_session_id,
    )
    result = await quarantine.submit(body.submission, caller)
    return result.model_dump()


@router.post("/fallback/execute")
async def fallback_execute(body: FallbackExecuteRequest) -> dict:
    """Execute safety fallback."""
    fb = get_fallback()
    result = await fb.execute(body.obj, body.constraint_result, body.domain_pack)
    return result.model_dump()


@router.post("/certify")
async def certify(body: CertifyRequest) -> dict:
    """Issue or deny a model certification."""
    cert = get_certification()
    result = await cert.certify(body.model_id, body.score, body.evidence)
    return result.model_dump()


@router.post("/evidence/admit")
async def evidence_admit(body: EvidenceAdmitRequest) -> dict:
    """Admit or reject evidence items."""
    ev = get_evidence()
    results = await ev.admit_batch(body.items, body.validation_results)
    feedback = ev.desensitize_feedback(results)
    return {
        "feedback": feedback,
        "items": [r.model_dump() for r in results],
    }


@router.post("/identity/check")
async def identity_check(body: IdentityCheckRequest) -> dict:
    """Check identity drift for a TwinObject."""
    monitor = get_identity_monitor()
    result = await monitor.check_identity(body.obj_id, body.invariants)
    return result.model_dump()


@router.get("/audit")
async def audit_query(
    event_type: str | None = None,
    actor: str | None = None,
) -> dict:
    """Query the audit trail."""
    audit = get_audit()
    filters = {}
    if event_type:
        filters["event_type"] = event_type
    if actor:
        filters["actor"] = actor
    events = await audit.query(filters or None)
    return {"events": events, "count": len(events)}


@router.post("/prescreen")
async def prescreen(
    state_values: dict[str, float],
    constraint_cards: list[dict],
) -> dict:
    """Run non-authoritative constraint prescreen (Lab advisory only)."""
    ps = get_prescreen()
    results = ps.prescreen(state_values, constraint_cards)
    return {
        "results": [r.model_dump() for r in results],
        "is_authoritative": False,
    }
