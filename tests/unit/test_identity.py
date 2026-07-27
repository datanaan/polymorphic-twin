"""Tests for identity/lineage module: provenance tracing, trust scoring, entry addition."""

from __future__ import annotations

import pytest

from polytwin.tom.base_models import Identity, Lineage, ProvenanceEntry
from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.identity import add_provenance_entry, compute_trust, trace_provenance
from polytwin.tom.types import ObjectType


def _make_internal(provenance=None, **overrides) -> TwinObjectInternal:
    defaults = dict(
        identity=Identity(type=ObjectType.DEVICE, name="test-device"),
        lineage=Lineage(
            creator_id="creator-001",
            provenance=provenance or [],
        ),
    )
    defaults.update(overrides)
    return TwinObjectInternal(**defaults)


class TestTraceProvenance:
    def test_empty_provenance(self):
        obj = _make_internal()
        result = trace_provenance(obj)
        assert result == []

    def test_returns_provenance_chain(self):
        entries = [
            ProvenanceEntry(source="system", action="created", actor="core"),
            ProvenanceEntry(source="lab", action="updated", actor="explorer"),
        ]
        obj = _make_internal(provenance=entries)
        result = trace_provenance(obj)
        assert len(result) == 2
        assert result[0].source == "system"
        assert result[1].source == "lab"

    def test_returns_copy(self):
        entries = [
            ProvenanceEntry(source="system", action="created", actor="core"),
        ]
        obj = _make_internal(provenance=entries)
        result = trace_provenance(obj)
        # Modifying result should not affect the original
        assert result is not obj.lineage.provenance


class TestComputeTrust:
    def test_trust_is_1_for_depth_0(self):
        obj = _make_internal()
        assert compute_trust(obj) == 1.0

    def test_trust_decays_with_depth(self):
        entries = [
            ProvenanceEntry(source="s1", action="a1", actor="x"),
        ]
        obj = _make_internal(provenance=entries)
        trust = compute_trust(obj)
        assert trust == pytest.approx(0.95)

    def test_trust_decays_further(self):
        entries = [
            ProvenanceEntry(source="s1", action="a1", actor="x"),
            ProvenanceEntry(source="s2", action="a2", actor="y"),
        ]
        obj = _make_internal(provenance=entries)
        trust = compute_trust(obj)
        assert trust == pytest.approx(0.95**2)

    def test_trust_approaches_zero_at_large_depth(self):
        entries = [
            ProvenanceEntry(source="s", action="a", actor="x")
            for _ in range(100)
        ]
        obj = _make_internal(provenance=entries)
        trust = compute_trust(obj)
        assert trust < 0.01


class TestAddProvenanceEntry:
    def test_adds_entry_to_lineage(self):
        obj = _make_internal()
        assert len(obj.lineage.provenance) == 0
        add_provenance_entry(obj, source="core", action="validated", actor="core-engine")
        assert len(obj.lineage.provenance) == 1
        assert obj.lineage.provenance[0].source == "core"
        assert obj.lineage.provenance[0].action == "validated"
        assert obj.lineage.provenance[0].actor == "core-engine"

    def test_adds_multiple_entries(self):
        obj = _make_internal()
        add_provenance_entry(obj, source="core", action="created", actor="core")
        add_provenance_entry(obj, source="lab", action="explored", actor="lab-engine")
        assert len(obj.lineage.provenance) == 2

    def test_entry_has_timestamp(self):
        obj = _make_internal()
        add_provenance_entry(obj, source="core", action="created", actor="core")
        entry = obj.lineage.provenance[0]
        assert entry.timestamp is not None
        assert entry.timestamp.tzinfo is not None
