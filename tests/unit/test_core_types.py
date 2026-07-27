"""Tests for core/types.py — result model instantiation and defaults."""


from polytwin.core.types import (
    DriftSample,
    EvidenceAdmissionResult,
    FallbackResult,
    HardGateCheckResult,
    HardGateResult,
    IdentityCheckResult,
    PrescreenResult,
    QuarantineRejection,
    SingleConstraintResult,
    ValidationResult,
)
from polytwin.tom.types import ConstraintStatus, Criticality, Rigidity

# ── SingleConstraintResult ──────────────────────────────────────────


class TestSingleConstraintResult:
    def test_defaults(self):
        r = SingleConstraintResult(constraint_id="c1")
        assert r.constraint_id == "c1"
        assert r.status == ConstraintStatus.UNCERTAIN
        assert r.actual_values == {}
        assert r.threshold == {}
        assert r.rigidity == Rigidity.ABSOLUTE
        assert r.criticality == Criticality.OPERATIONAL
        assert r.message == ""

    def test_full_construction(self):
        r = SingleConstraintResult(
            constraint_id="c2",
            status=ConstraintStatus.FAILED,
            actual_values={"temp": 190.0},
            threshold={"max": 180.0},
            rigidity=Rigidity.ABSOLUTE,
            criticality=Criticality.SAFETY_CRITICAL,
            message="Over temperature",
        )
        assert r.status == ConstraintStatus.FAILED
        assert r.actual_values["temp"] == 190.0
        assert r.criticality == Criticality.SAFETY_CRITICAL


# ── ValidationResult ───────────────────────────────────────────────


class TestValidationResult:
    def test_defaults(self):
        r = ValidationResult()
        assert r.passed is False
        assert r.individual_results == []
        assert r.combination_logic == "and"
        assert r.requires_human_review is False
        assert r.safety_fallback_triggered is False
        assert r.evaluated_count == 0

    def test_with_results(self):
        sr = SingleConstraintResult(
            constraint_id="c1", status=ConstraintStatus.PASSED
        )
        r = ValidationResult(passed=True, individual_results=[sr], evaluated_count=1)
        assert r.passed is True
        assert len(r.individual_results) == 1
        assert r.evaluated_count == 1


# ── HardGateCheckResult / HardGateResult ────────────────────────────


class TestHardGate:
    def test_check_result(self):
        r = HardGateCheckResult(check_name="qualification", passed=True)
        assert r.check_name == "qualification"
        assert r.passed is True

    def test_gate_result(self):
        r = HardGateResult(
            granted_links=["model_a"], degraded_links=[], denied_links=["model_b"]
        )
        assert "model_a" in r.granted_links
        assert "model_b" in r.denied_links


# ── FallbackResult ──────────────────────────────────────────────────


class TestFallbackResult:
    def test_defaults(self):
        r = FallbackResult()
        assert r.strategy_used == ""
        assert r.object_id == ""

    def test_with_values(self):
        r = FallbackResult(
            strategy_used="safe_shutdown", object_id="obj1", violated_constraint="c1"
        )
        assert r.strategy_used == "safe_shutdown"


# ── PrescreenResult ─────────────────────────────────────────────────


class TestPrescreenResult:
    def test_is_never_authoritative(self):
        r = PrescreenResult(status=ConstraintStatus.PASSED)
        assert r.is_authoritative is False

    def test_default_status(self):
        r = PrescreenResult()
        assert r.status == ConstraintStatus.UNCERTAIN
        assert r.is_authoritative is False


# ── QuarantineRejection ─────────────────────────────────────────────


class TestQuarantineRejection:
    def test_defaults(self):
        r = QuarantineRejection()
        assert r.rejected is False
        assert r.reason == ""

    def test_rejected(self):
        r = QuarantineRejection(
            rejected=True, reason="identity_drift", detail="drift > 0.1"
        )
        assert r.rejected is True


# ── EvidenceAdmissionResult ─────────────────────────────────────────


class TestEvidenceAdmissionResult:
    def test_defaults(self):
        r = EvidenceAdmissionResult(item_id="e1")
        assert r.admitted is False
        assert r.reason == ""

    def test_admitted(self):
        r = EvidenceAdmissionResult(item_id="e1", admitted=True, reason="meets criteria")
        assert r.admitted is True


# ── IdentityCheckResult / DriftSample ──────────────────────────────


class TestIdentityTypes:
    def test_identity_check(self):
        r = IdentityCheckResult(
            identity_status="confirmed",
            drift_values={"invariant_1": 0.02},
            timestamp="2026-01-01T00:00:00Z",
        )
        assert r.identity_status == "confirmed"
        assert r.drift_values["invariant_1"] == 0.02

    def test_drift_sample(self):
        d = DriftSample(invariant_name="mass_balance", drift=0.03)
        assert d.invariant_name == "mass_balance"
        assert d.drift == 0.03


# ── Serialization round-trip ───────────────────────────────────────


class TestSerialization:
    def test_single_constraint_result_json(self):
        r = SingleConstraintResult(
            constraint_id="c1", status=ConstraintStatus.PASSED
        )
        data = r.model_dump()
        r2 = SingleConstraintResult(**data)
        assert r2 == r

    def test_validation_result_json(self):
        r = ValidationResult(
            passed=True,
            individual_results=[
                SingleConstraintResult(constraint_id="c1", status=ConstraintStatus.PASSED)
            ],
            evaluated_count=1,
        )
        data = r.model_dump()
        r2 = ValidationResult(**data)
        assert r2.passed is True
        assert r2.evaluated_count == 1
