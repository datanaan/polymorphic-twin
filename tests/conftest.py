"""Shared test fixtures for the Polymorphic-Twin test suite."""


import pytest

from polytwin.tom.base_models import (
    Identity,
    Lineage,
    ProvenanceEntry,
    Relationship,
    State,
    TwinObjectBase,
)
from polytwin.tom.domain_models import (
    ActionState,
    AuditEvent,
    AuditTrail,
    ConstraintEvaluation,
    ConstraintState,
    IdentityInvariant,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    StateSemantics,
    StateVariable,
    TwinObjectInternal,
)
from polytwin.tom.types import (
    CallerIdentity,
    ConstraintStatus,
    HealthState,
    LifecycleState,
    ObjectType,
    RelationType,
)

# ── CallerIdentity fixtures ────────────────────────────────────────


@pytest.fixture
def caller_core() -> CallerIdentity:
    return CallerIdentity(component="core", role="validator")


@pytest.fixture
def caller_lab() -> CallerIdentity:
    return CallerIdentity(component="lab", role="explorer", session_id="sess-001")


@pytest.fixture
def caller_bridge() -> CallerIdentity:
    return CallerIdentity(component="bridge", role="decision_maker")


# ── Identity fixtures ──────────────────────────────────────────────


@pytest.fixture
def device_identity() -> Identity:
    return Identity(type=ObjectType.DEVICE, name="pump-001", tags=["rotating", "oil-rig"])


@pytest.fixture
def agent_identity() -> Identity:
    return Identity(type=ObjectType.AGENT, name="lab-explorer-01")


# ── Lineage fixtures ───────────────────────────────────────────────


@pytest.fixture
def sample_lineage() -> Lineage:
    return Lineage(
        creator_id="creator-001",
        parent_id="parent-001",
        provenance=[
            ProvenanceEntry(
                source="core",
                action="created",
                actor="system",
            )
        ],
    )


# ── Relationship fixtures ──────────────────────────────────────────


@pytest.fixture
def owns_relationship() -> Relationship:
    return Relationship(
        target_id="target-001",
        type=RelationType.OWNS,
        strength=1.0,
        bidirectional=False,
    )


@pytest.fixture
def supports_relationship() -> Relationship:
    return Relationship(
        target_id="hypothesis-001",
        type=RelationType.SUPPORTS,
        strength=0.85,
        metadata={"confidence": "high"},
    )


# ── State fixtures ─────────────────────────────────────────────────


@pytest.fixture
def active_healthy_state() -> State:
    return State(lifecycle=LifecycleState.ACTIVE, health=HealthState.HEALTHY)


@pytest.fixture
def creating_unknown_state() -> State:
    return State()


# ── TwinObjectBase fixture ─────────────────────────────────────────


@pytest.fixture
def minimal_twin_base(device_identity: Identity, sample_lineage: Lineage) -> TwinObjectBase:
    return TwinObjectBase(identity=device_identity, lineage=sample_lineage)


# ── Domain model fixtures ──────────────────────────────────────────


@pytest.fixture
def temperature_variable() -> StateVariable:
    return StateVariable(
        name="temperature",
        physical_meaning="Bearing temperature",
        unit="degC",
        range_min=-40.0,
        range_max=120.0,
        observability="direct",
        controllability="indirect",
        measurement_source="sensor_bearing_thermocouple",
        required=True,
    )


@pytest.fixture
def state_semantics(temperature_variable: StateVariable) -> StateSemantics:
    return StateSemantics(
        variables={"temperature": temperature_variable},
        current_values={"temperature": 65.3},
    )


@pytest.fixture
def constraint_evaluation_passed() -> ConstraintEvaluation:
    return ConstraintEvaluation(
        constraint_id="cc-temp-limit",
        status=ConstraintStatus.PASSED,
        actual_values={"temperature": 65.3},
        message="Temperature within safe range",
    )


@pytest.fixture
def constraint_evaluation_failed() -> ConstraintEvaluation:
    return ConstraintEvaluation(
        constraint_id="cc-temp-limit",
        status=ConstraintStatus.FAILED,
        actual_values={"temperature": 130.0},
        message="Temperature exceeds safe range",
    )


@pytest.fixture
def constraint_state(constraint_evaluation_passed: ConstraintEvaluation) -> ConstraintState:
    return ConstraintState(
        active_constraints=["cc-temp-limit", "cc-pressure-limit"],
        suspended_constraints=[],
        last_evaluation=[constraint_evaluation_passed],
    )


@pytest.fixture
def identity_invariants() -> IdentityInvariants:
    return IdentityInvariants(
        invariants=[
            IdentityInvariant(
                name="serial_number",
                expected_value="SN-12345",
                actual_value="SN-12345",
                confidence=1.0,
            )
        ],
        overall_confidence=1.0,
        identity_status="confirmed",
    )


@pytest.fixture
def model_governance() -> ModelGovernanceState:
    return ModelGovernanceState(
        active_links=["model-bearings-v2"],
        qualification_history=["qual-001"],
        active_certificates=["cert-001"],
    )


@pytest.fixture
def knowledge_state() -> KnowledgeState:
    return KnowledgeState(
        admitted_lab_evidence=["ev-001", "ev-002"],
        pending_submissions=["ev-003"],
    )


@pytest.fixture
def action_state() -> ActionState:
    return ActionState(
        current_safe_action_set=["action-shutdown", "action-reduce-load"],
        fallback_available=True,
    )


@pytest.fixture
def audit_trail() -> AuditTrail:
    return AuditTrail(
        events=[
            AuditEvent(
                event_type="constraint_evaluated",
                actor="core",
                detail={"constraint_id": "cc-temp-limit"},
            )
        ]
    )


# ── Full TwinObjectInternal fixture ────────────────────────────────


@pytest.fixture
def full_twin_internal(
    device_identity: Identity,
    sample_lineage: Lineage,
    state_semantics: StateSemantics,
    constraint_state: ConstraintState,
    identity_invariants: IdentityInvariants,
    model_governance: ModelGovernanceState,
    knowledge_state: KnowledgeState,
    action_state: ActionState,
    audit_trail: AuditTrail,
) -> TwinObjectInternal:
    return TwinObjectInternal(
        identity=device_identity,
        lineage=sample_lineage,
        state=State(lifecycle=LifecycleState.ACTIVE, health=HealthState.HEALTHY),
        state_semantics=state_semantics,
        constraint_state=constraint_state,
        identity_invariants=identity_invariants,
        model_governance=model_governance,
        knowledge_state=knowledge_state,
        action_state=action_state,
        audit_trail=audit_trail,
    )
