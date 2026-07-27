"""Tests for FailureAnalyzer: failure correlation analysis.

Key tests:
1. Empty logs return no correlations
2. Single event returns no correlations
3. Sequential events with shared variables produce correlations
4. Correlation strength is computed correctly
"""
import pytest

from polytwin.lab.failure_analyzer import FailureAnalyzer
from polytwin.lab.types import CorrelationFinding, ExplorationBudget


class TestFailureAnalyzerEmpty:
    @pytest.mark.asyncio
    async def test_empty_logs(self):
        analyzer = FailureAnalyzer()
        result = await analyzer.analyze([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_event(self):
        analyzer = FailureAnalyzer()
        result = await analyzer.analyze([{"variables": {"temp": 100}}])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_shared_variables(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"pressure": 50}},
        ]
        result = await analyzer.analyze(logs)
        assert result == []


class TestFailureAnalyzerCorrelation:
    @pytest.mark.asyncio
    async def test_correlated_events(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100, "pressure": 50}},
            {"variables": {"temperature": 105, "pressure": 52}},
        ]
        result = await analyzer.analyze(logs)
        assert len(result) > 0
        assert all(isinstance(cf, CorrelationFinding) for cf in result)

    @pytest.mark.asyncio
    async def test_correlation_strength_positive(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
        ]
        result = await analyzer.analyze(logs)
        assert all(cf.correlation_strength > 0 for cf in result)

    @pytest.mark.asyncio
    async def test_event_sequence_length(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
        ]
        result = await analyzer.analyze(logs)
        assert all(len(cf.event_sequence) == 2 for cf in result)

    @pytest.mark.asyncio
    async def test_three_events_two_correlations(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
            {"variables": {"temperature": 110}},
        ]
        result = await analyzer.analyze(logs)
        assert len(result) == 2


class TestFailureAnalyzerBudget:
    @pytest.mark.asyncio
    async def test_with_budget(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
        ]
        result = await analyzer.analyze(logs, ExplorationBudget())
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_without_budget(self):
        analyzer = FailureAnalyzer()
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
        ]
        result = await analyzer.analyze(logs, None)
        assert len(result) > 0
