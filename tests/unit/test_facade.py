"""Tests for TwinObjectFacade: 12-rule access matrix, write permissions, frozen views, edge cases.

MUST include:
- 12 access-matrix tests (one per row)
- Write permission tests (core_runtime, bridge, lab, audit)
- View frozen return test
- Edge cases: unknown caller, unknown view_type, non-existent object_id
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from polytwin.tom.base_models import Identity, Lineage
from polytwin.tom.domain_models import (
    ActionState,
    ActionTemplate,
    AuditTrail,
    ChangeHistory,
    ConstraintEvaluation,
    ConstraintState,
    HumanRole,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    RigidityRule,
    SafeFallback,
    StateSemantics,
    TwinObjectInternal,
)
from polytwin.tom.exceptions import PermissionDeniedError
from polytwin.tom.facade import InMemoryTwinObjectStore, TwinObjectFacade
from polytwin.tom.types import CallerIdentity, ConstraintStatus, ObjectType, ViewType
from polytwin.tom.views import (
    AuditView,
    BridgeDecisionView,
    CoreCertificationView,
    CoreRuntimeView,
    LabExplorationView,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_internal(**overrides) -> TwinObjectInternal:
    """Build a TwinObjectInternal with sensible defaults."""
    defaults = dict(
        identity=Identity(type=ObjectType.DEVICE, name="test-device"),
        lineage=Lineage(creator_id="creator-001"),
        state_semantics=StateSemantics(
            variables={},
            current_values={"temperature": 42.0},
        ),
        constraint_state=ConstraintState(
            active_constraints=["c1"],
            last_evaluation=[
                ConstraintEvaluation(
                    constraint_id="c1",
                    status=ConstraintStatus.PASSED,
                    message="OK",
                ),
            ],
        ),
        identity_invariants=IdentityInvariants(identity_status="confirmed"),
        model_governance=ModelGovernanceState(active_links=["model-A"]),
        knowledge_state=KnowledgeState(admitted_lab_evidence=["ev-001"]),
        action_state=ActionState(
            current_safe_action_set=["act-cool"],
            fallback_available=True,
        ),
        audit_trail=AuditTrail(),
        action_templates=[ActionTemplate(template_id="at-1", name="Cool")],
        human_roles=[HumanRole(role_id="r-1", name="Op", permission_level="approve")],
        safe_fallback=SafeFallback(strategy="emergency_cool"),
        rigidity_rules=[RigidityRule(constraint_id="c1", rigidity="absolute")],
        audit_benchmark_reference="bench-ref-123",
        hidden_challenge_set_reference="hidden-challenge-456",
        public_eval_set_reference="public-eval-789",
        change_history=ChangeHistory(entries=[{"action": "created"}]),
    )
    defaults.update(overrides)
    return TwinObjectInternal(**defaults)


def _caller_core_runtime() -> CallerIdentity:
    return CallerIdentity(component="core", role="validator")


def _caller_core_certification() -> CallerIdentity:
    return CallerIdentity(component="core", role="certifier")


def _caller_lab() -> CallerIdentity:
    return CallerIdentity(component="lab", role="explorer")


def _caller_bridge() -> CallerIdentity:
    return CallerIdentity(component="bridge", role="decision_maker")


def _caller_audit() -> CallerIdentity:
    return CallerIdentity(component="audit", role="auditor")


@pytest.fixture()
def store_with_object() -> tuple[TwinObjectFacade, str]:
    """Return a facade with a pre-loaded TwinObject and its ID."""
    store = InMemoryTwinObjectStore()
    facade = TwinObjectFacade(store)
    obj = _make_internal()
    import asyncio

    asyncio.get_event_loop().run_until_complete(store.put(obj))
    return facade, obj.identity.id


# ── Async runner helper ──────────────────────────────────────────────

import asyncio  # noqa: E402


def _run(coro):
    """Run an async coroutine synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =====================================================================
# 1. ACCESS MATRIX TESTS (12 rules)
# =====================================================================


class TestAccessMatrixRule1:
    """Rule 1: core_runtime -> CORE_RUNTIME = ALLOW."""

    def test_core_runtime_can_access_core_runtime_view(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.CORE_RUNTIME, _caller_core_runtime()))
        assert isinstance(view, CoreRuntimeView)
        assert view.twin_object_id == obj_id


class TestAccessMatrixRule2:
    """Rule 2: core_runtime -> BRIDGE_DECISION = ALLOW."""

    def test_core_runtime_can_access_bridge_decision_view(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.BRIDGE_DECISION, _caller_core_runtime()))
        assert isinstance(view, BridgeDecisionView)


class TestAccessMatrixRule3:
    """Rule 3: core_runtime -> LAB_EXPLORATION = ALLOW."""

    def test_core_runtime_can_access_lab_exploration_view(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.LAB_EXPLORATION, _caller_core_runtime()))
        assert isinstance(view, LabExplorationView)


class TestAccessMatrixRule4:
    """Rule 4: core_runtime -> CORE_CERTIFICATION = DENY."""

    def test_core_runtime_denied_core_certification(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_view(obj_id, ViewType.CORE_CERTIFICATION, _caller_core_runtime()))


class TestAccessMatrixRule5:
    """Rule 5: core_runtime -> AUDIT = DENY."""

    def test_core_runtime_denied_audit(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_view(obj_id, ViewType.AUDIT, _caller_core_runtime()))


class TestAccessMatrixRule6:
    """Rule 6: core_certification -> CORE_RUNTIME = ALLOW."""

    def test_core_certification_can_access_core_runtime(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.CORE_RUNTIME, _caller_core_certification()))
        assert isinstance(view, CoreRuntimeView)


class TestAccessMatrixRule7:
    """Rule 7: core_certification -> CORE_CERTIFICATION = ALLOW."""

    def test_core_certification_can_access_core_certification(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.CORE_CERTIFICATION, _caller_core_certification()))
        assert isinstance(view, CoreCertificationView)
        assert view.audit_benchmark_reference == "bench-ref-123"


class TestAccessMatrixRule8:
    """Rule 8: lab -> LAB_EXPLORATION = ALLOW."""

    def test_lab_can_access_lab_exploration(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.LAB_EXPLORATION, _caller_lab()))
        assert isinstance(view, LabExplorationView)
        assert view.public_eval_set_reference == "public-eval-789"


class TestAccessMatrixRule9:
    """Rule 9: lab -> CORE_RUNTIME = DENY."""

    def test_lab_denied_core_runtime(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_view(obj_id, ViewType.CORE_RUNTIME, _caller_lab()))


class TestAccessMatrixRule10:
    """Rule 10: lab -> CORE_CERTIFICATION = DENY."""

    def test_lab_denied_core_certification(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_view(obj_id, ViewType.CORE_CERTIFICATION, _caller_lab()))


class TestAccessMatrixRule11:
    """Rule 11: bridge -> BRIDGE_DECISION = ALLOW."""

    def test_bridge_can_access_bridge_decision(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.BRIDGE_DECISION, _caller_bridge()))
        assert isinstance(view, BridgeDecisionView)


class TestAccessMatrixRule12:
    """Rule 12: audit -> AUDIT = ALLOW."""

    def test_audit_can_access_audit(self, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, ViewType.AUDIT, _caller_audit()))
        assert isinstance(view, AuditView)
        assert view.change_history is not None


# =====================================================================
# 2. WRITE PERMISSION TESTS
# =====================================================================


class TestWritePermissions:
    """Verify write permission matrix for each caller."""

    def test_core_runtime_write_succeeds(self, store_with_object):
        facade, obj_id = store_with_object
        changes = {"version": "2.0.0"}
        _run(facade.update(obj_id, changes, _caller_core_runtime()))
        # Verify the update stuck
        _run(facade.get_view(obj_id, ViewType.CORE_RUNTIME, _caller_core_runtime()))
        # version is on the base model, not the view; check store directly
        updated = _run(facade._store.get(obj_id))
        assert updated.version == "2.0.0"

    def test_bridge_write_succeeds(self, store_with_object):
        facade, obj_id = store_with_object
        changes = {"version": "3.0.0"}
        _run(facade.update(obj_id, changes, _caller_bridge()))

    def test_lab_write_denied(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.update(obj_id, {"version": "2.0.0"}, _caller_lab()))

    def test_audit_write_denied(self, store_with_object):
        facade, obj_id = store_with_object
        with pytest.raises(PermissionDeniedError):
            _run(facade.update(obj_id, {"version": "2.0.0"}, _caller_audit()))


# =====================================================================
# 3. VIEW FROZEN RETURN TEST
# =====================================================================


class TestViewFrozenReturn:
    """Any returned view must be frozen (mutation raises ValidationError)."""

    @pytest.mark.parametrize(
        "caller_fn, view_type",
        [
            (_caller_core_runtime, ViewType.CORE_RUNTIME),
            (_caller_core_certification, ViewType.CORE_CERTIFICATION),
            (_caller_bridge, ViewType.BRIDGE_DECISION),
            (_caller_lab, ViewType.LAB_EXPLORATION),
            (_caller_audit, ViewType.AUDIT),
        ],
    )
    def test_returned_view_is_frozen(self, caller_fn, view_type, store_with_object):
        facade, obj_id = store_with_object
        view = _run(facade.get_view(obj_id, view_type, caller_fn()))
        with pytest.raises(ValidationError):
            view.twin_object_id = "tampered"


# =====================================================================
# 4. EDGE CASES
# =====================================================================


class TestEdgeCases:
    """Unknown caller, unknown view_type, non-existent object_id."""

    def test_unknown_caller_denied(self, store_with_object):
        """A caller with an unrecognised component has no access rules."""
        facade, obj_id = store_with_object
        unknown = CallerIdentity(component="unknown_subsystem", role="admin")
        with pytest.raises(PermissionDeniedError) as exc_info:
            _run(facade.get_view(obj_id, ViewType.CORE_RUNTIME, unknown))
        assert "No access rule defined" in exc_info.value.reason

    def test_nonexistent_object_id_raises(self, store_with_object):
        """Requesting a view for a non-existent object raises PermissionDeniedError."""
        facade, _ = store_with_object
        with pytest.raises(PermissionDeniedError) as exc_info:
            _run(facade.get_view("nonexistent-id", ViewType.CORE_RUNTIME, _caller_core_runtime()))
        assert "not found" in exc_info.value.reason

    def test_create_only_core_runtime_and_api(self):
        """Only core_runtime and api can create TwinObjects."""
        store = InMemoryTwinObjectStore()
        facade = TwinObjectFacade(store)

        # lab cannot create
        with pytest.raises(PermissionDeniedError):
            _run(facade.create(
                {"identity": {"type": "device", "name": "x"}, "lineage": {"creator_id": "c1"}},
                _caller_lab(),
            ))

        # core_runtime can create
        obj_id = _run(facade.create(
            {"identity": {"type": "device", "name": "x"}, "lineage": {"creator_id": "c1"}},
            _caller_core_runtime(),
        ))
        assert isinstance(obj_id, str)

    def test_snapshot_only_core_and_audit(self, store_with_object):
        """Only core_runtime, core_certification, and audit can create/get snapshots."""
        facade, obj_id = store_with_object

        # lab cannot create snapshot
        with pytest.raises(PermissionDeniedError):
            _run(facade.create_snapshot(obj_id, _caller_lab()))

        # core_runtime can create snapshot
        snap_id = _run(facade.create_snapshot(obj_id, _caller_core_runtime()))
        assert snap_id.startswith("snap-")

        # core_certification can create snapshot
        snap_id2 = _run(facade.create_snapshot(obj_id, _caller_core_certification()))
        assert snap_id2.startswith("snap-")

        # audit can create snapshot
        snap_id3 = _run(facade.create_snapshot(obj_id, _caller_audit()))
        assert snap_id3.startswith("snap-")

        # bridge cannot read snapshot
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_snapshot(snap_id, _caller_bridge()))

        # core_runtime can read snapshot
        snap_obj = _run(facade.get_snapshot(snap_id, _caller_core_runtime()))
        assert isinstance(snap_obj, TwinObjectInternal)

    def test_change_history_only_audit(self, store_with_object):
        """Only audit can read change history."""
        facade, obj_id = store_with_object

        # First do an update to create a change record
        _run(facade.update(obj_id, {"version": "2.0.0"}, _caller_core_runtime()))

        # core_runtime cannot read history
        with pytest.raises(PermissionDeniedError):
            _run(facade.get_change_history(obj_id, _caller_core_runtime()))

        # audit can read history
        history = _run(facade.get_change_history(obj_id, _caller_audit()))
        assert len(history) == 1
        assert history[0]["action"] == "update"
        assert history[0]["caller_component"] == "core_runtime"

    def test_update_nonexistent_object_raises(self):
        """Updating a non-existent object raises PermissionDeniedError."""
        facade = TwinObjectFacade(InMemoryTwinObjectStore())
        with pytest.raises(PermissionDeniedError) as exc_info:
            _run(facade.update("no-such-id", {"version": "2.0.0"}, _caller_core_runtime()))
        assert "not found" in exc_info.value.reason

    def test_create_snapshot_nonexistent_object_raises(self):
        """Creating a snapshot for a non-existent object raises PermissionDeniedError."""
        facade = TwinObjectFacade(InMemoryTwinObjectStore())
        with pytest.raises(PermissionDeniedError) as exc_info:
            _run(facade.create_snapshot("no-such-id", _caller_core_runtime()))
        assert "not found" in exc_info.value.reason

    def test_get_snapshot_nonexistent_raises(self):
        """Getting a non-existent snapshot raises PermissionDeniedError."""
        facade = TwinObjectFacade(InMemoryTwinObjectStore())
        with pytest.raises(PermissionDeniedError) as exc_info:
            _run(facade.get_snapshot("no-such-snap", _caller_core_runtime()))
        assert "not found" in exc_info.value.reason

    def test_permission_denied_error_attributes(self):
        """PermissionDeniedError stores caller, view_type, reason."""
        err = PermissionDeniedError(
            caller="lab",
            view_type="core_runtime",
            reason="Access denied by view isolation policy",
        )
        assert err.caller == "lab"
        assert err.view_type == "core_runtime"
        assert err.reason == "Access denied by view isolation policy"
        assert "lab" in str(err)
        assert "core_runtime" in str(err)
