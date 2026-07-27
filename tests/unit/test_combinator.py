"""Tests for the constraint result combinator.

Test cases:
1. AND: 3 pass -> pass
2. AND: 2 pass + 1 fail -> fail
3. OR: 1 pass + 2 fail -> pass
4. weighted: 0.5 pass + 0.5 fail = 0.5, threshold 0.6 -> fail
5. priority: safety fail -> overall fail
6. identity_critical fail -> requires_human_review=True
"""


from polytwin.core.rules.combinator import combine
from polytwin.core.types import SingleConstraintResult
from polytwin.tom.types import ConstraintStatus, Criticality


def _result(
    cid: str,
    status: ConstraintStatus = ConstraintStatus.PASSED,
    criticality: Criticality = Criticality.OPERATIONAL,
) -> SingleConstraintResult:
    return SingleConstraintResult(
        constraint_id=cid, status=status, criticality=criticality
    )


# ── AND mode ────────────────────────────────────────────────────────


class TestCombineAnd:
    # Test 1: AND: 3 pass -> pass
    def test_all_pass(self):
        results = [_result("c1"), _result("c2"), _result("c3")]
        vr = combine(results, mode="and")
        assert vr.passed is True
        assert vr.evaluated_count == 3

    # Test 2: AND: 2 pass + 1 fail -> fail
    def test_two_pass_one_fail(self):
        results = [
            _result("c1"),
            _result("c2", status=ConstraintStatus.FAILED),
            _result("c3"),
        ]
        vr = combine(results, mode="and")
        assert vr.passed is False

    # NOT_APPLICABLE counts as pass in AND mode
    def test_not_applicable_counts_as_pass(self):
        results = [
            _result("c1"),
            _result("c2", status=ConstraintStatus.NOT_APPLICABLE),
        ]
        vr = combine(results, mode="and")
        assert vr.passed is True


# ── OR mode ─────────────────────────────────────────────────────────


class TestCombineOr:
    # Test 3: OR: 1 pass + 2 fail -> pass
    def test_one_pass_among_failures(self):
        results = [
            _result("c1", status=ConstraintStatus.FAILED),
            _result("c2"),  # PASSED
            _result("c3", status=ConstraintStatus.FAILED),
        ]
        vr = combine(results, mode="or")
        assert vr.passed is True

    def test_all_fail(self):
        results = [
            _result("c1", status=ConstraintStatus.FAILED),
            _result("c2", status=ConstraintStatus.FAILED),
        ]
        vr = combine(results, mode="or")
        assert vr.passed is False


# ── Weighted mode ───────────────────────────────────────────────────


class TestCombineWeighted:
    # Test 4: weighted: 0.5 pass + 0.5 fail = 0.5, threshold 0.6 -> fail
    def test_weighted_below_threshold(self):
        results = [
            _result("c1"),  # PASSED, weight=0.5
            _result("c2", status=ConstraintStatus.FAILED),  # weight=0.5
        ]
        weights = {"c1": 0.5, "c2": 0.5}
        vr = combine(results, mode="weighted", weights=weights, threshold=0.6)
        assert vr.passed is False

    def test_weighted_meets_threshold(self):
        results = [
            _result("c1"),  # PASSED, weight=0.4
            _result("c2"),  # PASSED, weight=0.3
            _result("c3", status=ConstraintStatus.FAILED),  # weight=0.3
        ]
        weights = {"c1": 0.4, "c2": 0.3, "c3": 0.3}
        vr = combine(results, mode="weighted", weights=weights, threshold=0.6)
        assert vr.passed is True  # 0.4 + 0.3 = 0.7 >= 0.6


# ── Priority mode ───────────────────────────────────────────────────


class TestCombinePriority:
    # Test 5: priority: safety fail -> overall fail
    def test_safety_fail_overall_fail(self):
        results = [
            _result("c_op", criticality=Criticality.OPERATIONAL),
            _result(
                "c_safety",
                status=ConstraintStatus.FAILED,
                criticality=Criticality.SAFETY_CRITICAL,
            ),
        ]
        vr = combine(results, mode="priority")
        assert vr.passed is False

    def test_all_critical_pass(self):
        results = [
            _result("c_safety", criticality=Criticality.SAFETY_CRITICAL),
            _result("c_identity", criticality=Criticality.IDENTITY_CRITICAL),
            _result("c_op", criticality=Criticality.OPERATIONAL),
        ]
        vr = combine(results, mode="priority")
        assert vr.passed is True


# ── Human review / safety fallback flags ────────────────────────────


class TestCombinatorFlags:
    # Test 6: identity_critical fail -> requires_human_review=True
    def test_identity_critical_fail_requires_human(self):
        results = [
            _result("c1", criticality=Criticality.OPERATIONAL),
            _result(
                "c2",
                status=ConstraintStatus.FAILED,
                criticality=Criticality.IDENTITY_CRITICAL,
            ),
        ]
        vr = combine(results, mode="and")
        assert vr.requires_human_review is True

    def test_no_identity_fail_no_human_review(self):
        results = [
            _result("c1"),
            _result("c2", status=ConstraintStatus.FAILED, criticality=Criticality.OPERATIONAL),
        ]
        vr = combine(results, mode="and")
        assert vr.requires_human_review is False

    def test_safety_critical_fail_triggers_fallback(self):
        results = [
            _result(
                "c1",
                status=ConstraintStatus.FAILED,
                criticality=Criticality.SAFETY_CRITICAL,
            ),
        ]
        vr = combine(results, mode="and")
        assert vr.safety_fallback_triggered is True


# ── Edge cases ──────────────────────────────────────────────────────


class TestCombinatorEdge:
    def test_empty_results_and(self):
        vr = combine([], mode="and")
        assert vr.passed is True  # vacuously true
        assert vr.evaluated_count == 0

    def test_unknown_mode_falls_back_to_and(self):
        results = [_result("c1")]
        vr = combine(results, mode="unknown_mode")
        assert vr.passed is True
        assert vr.combination_logic == "unknown_mode"

    def test_combination_logic_recorded(self):
        vr = combine([_result("c1")], mode="or")
        assert vr.combination_logic == "or"
