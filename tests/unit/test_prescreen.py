"""Tests for PrescreenLibrary: stateless constraint verification.

Test cases:
1. Prescreen returns results for each constraint
2. All PrescreenResult have is_authoritative=False
3. Prescreen uses same validation logic as Core evaluator
"""

from polytwin.core.prescreen import PrescreenLibrary
from polytwin.tom.types import ConstraintStatus


def _card(
    constraint_id: str = "c_temp",
    variable: str = "temperature",
    method: str = "range_check",
    config: dict | None = None,
    criticality: str = "operational",
) -> dict:
    """Build a minimal constraint card dict."""
    if config is None:
        config = {"variable": variable, "max": 180.0}
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": criticality,
        "validation": {"method": method, "config": config},
    }


# ── Test 1: Returns results for each constraint ────────────────────


class TestPrescreenResults:
    def test_returns_result_per_constraint(self):
        """Prescreen returns one result per constraint card."""
        lib = PrescreenLibrary()
        cards = [
            _card("c1", config={"variable": "temperature", "max": 180.0}),
            _card("c2", config={"variable": "pressure", "max": 100.0}),
            _card("c3", config={"variable": "flow_rate", "max": 50.0}),
        ]
        results = lib.prescreen({"temperature": 150, "pressure": 80, "flow_rate": 30}, cards)
        assert len(results) == 3

    def test_empty_cards_returns_empty(self):
        """No constraint cards -> empty result list."""
        lib = PrescreenLibrary()
        results = lib.prescreen({"temperature": 150}, [])
        assert results == []


# ── Test 2: is_authoritative always False ───────────────────────────


class TestNotAuthoritative:
    def test_all_results_not_authoritative(self):
        """All PrescreenResult have is_authoritative=False."""
        lib = PrescreenLibrary()
        cards = [
            _card("c1", config={"variable": "temperature", "max": 180.0}),
            _card("c2", config={"variable": "pressure", "max": 100.0}),
        ]
        results = lib.prescreen({"temperature": 150, "pressure": 80}, cards)
        for r in results:
            assert r.is_authoritative is False

    def test_failed_result_still_not_authoritative(self):
        """Even a FAILED result is not authoritative."""
        lib = PrescreenLibrary()
        card = _card(config={"variable": "temperature", "max": 180.0})
        results = lib.prescreen({"temperature": 200}, [card])
        assert results[0].status == ConstraintStatus.FAILED
        assert results[0].is_authoritative is False


# ── Test 3: Same validation logic as Core evaluator ────────────────


class TestSameLogic:
    def test_passed_matches_evaluator(self):
        """Prescreen PASSED matches what evaluator would return."""
        lib = PrescreenLibrary()
        card = _card(config={"variable": "temperature", "max": 180.0})
        results = lib.prescreen({"temperature": 150.0}, [card])
        assert results[0].status == ConstraintStatus.PASSED

    def test_failed_matches_evaluator(self):
        """Prescreen FAILED matches what evaluator would return."""
        lib = PrescreenLibrary()
        card = _card(config={"variable": "temperature", "max": 180.0})
        results = lib.prescreen({"temperature": 190.0}, [card])
        assert results[0].status == ConstraintStatus.FAILED

    def test_uncertain_matches_evaluator(self):
        """Prescreen UNCERTAIN for missing variable."""
        lib = PrescreenLibrary()
        card = _card(config={"variable": "nonexistent", "max": 100.0})
        results = lib.prescreen({"temperature": 150.0}, [card])
        assert results[0].status == ConstraintStatus.UNCERTAIN
