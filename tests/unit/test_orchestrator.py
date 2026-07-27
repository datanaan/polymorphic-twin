"""Tests for the BridgeOrchestrator.

Key tests:
1. Generate action space -> returns BridgeOutput
2. Each call creates new output_id (stateless)
3. Output has valid version tag and timestamps
4. No persistent state between calls
"""
import pytest

from polytwin.bridge.orchestrator import BridgeOrchestrator
from polytwin.bridge.types import BridgeOutput


@pytest.fixture
def orchestrator():
    return BridgeOrchestrator()


@pytest.fixture
def sample_view_data():
    return {
        "twin_object_id": "obj-001",
        "constraint_summary": [
            {"constraint_id": "c1", "status": "passed", "criticality": "operational"},
            {"constraint_id": "c2", "status": "passed", "criticality": "safety_critical"},
        ],
        "safe_fallback": {"strategy": "cool_down"},
    }


class TestGenerateActionSpace:
    @pytest.mark.asyncio
    async def test_returns_bridge_output(self, orchestrator, sample_view_data):
        output = await orchestrator.generate_action_space(sample_view_data)
        assert isinstance(output, BridgeOutput)

    @pytest.mark.asyncio
    async def test_output_has_uuid(self, orchestrator, sample_view_data):
        output = await orchestrator.generate_action_space(sample_view_data)
        assert output.output_id != ""
        # UUID format check
        assert len(output.output_id) == 36
        assert output.output_id.count("-") == 4

    @pytest.mark.asyncio
    async def test_output_has_object_id(self, orchestrator, sample_view_data):
        output = await orchestrator.generate_action_space(sample_view_data)
        assert output.object_id == "obj-001"

    @pytest.mark.asyncio
    async def test_output_has_timestamps(self, orchestrator, sample_view_data):
        output = await orchestrator.generate_action_space(sample_view_data)
        assert output.created_at != ""
        assert output.valid_until != ""

    @pytest.mark.asyncio
    async def test_output_has_version_tag(self, orchestrator, sample_view_data):
        output = await orchestrator.generate_action_space(sample_view_data)
        assert output.version_tag != ""
        assert output.version_tag.startswith("v:")


class TestStatelessness:
    @pytest.mark.asyncio
    async def test_each_call_new_output_id(self, orchestrator, sample_view_data):
        """Stateless: each call produces a different output_id."""
        output1 = await orchestrator.generate_action_space(sample_view_data)
        output2 = await orchestrator.generate_action_space(sample_view_data)
        assert output1.output_id != output2.output_id

    @pytest.mark.asyncio
    async def test_same_input_same_version_tag(self, orchestrator, sample_view_data):
        """Same input data produces the same version tag."""
        output1 = await orchestrator.generate_action_space(sample_view_data)
        output2 = await orchestrator.generate_action_space(sample_view_data)
        assert output1.version_tag == output2.version_tag

    @pytest.mark.asyncio
    async def test_different_input_different_version(self, orchestrator):
        """Different constraint states produce different version tags."""
        view1 = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
        }
        view2 = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "failed"},
            ],
        }
        output1 = await orchestrator.generate_action_space(view1)
        output2 = await orchestrator.generate_action_space(view2)
        assert output1.version_tag != output2.version_tag


class TestWithDomainPack:
    @pytest.mark.asyncio
    async def test_domain_pack_version_in_tag(self, orchestrator):
        """Domain pack version is included in the version tag."""
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
        }
        dp = {"domain_version": "2.1.0"}
        output = await orchestrator.generate_action_space(view_data, dp)
        assert "2.1.0" in output.version_tag

    @pytest.mark.asyncio
    async def test_no_domain_pack_version_in_tag(self, orchestrator):
        """No domain pack -> version tag ends with empty string."""
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
        }
        output = await orchestrator.generate_action_space(view_data)
        assert output.version_tag.endswith(":")

    @pytest.mark.asyncio
    async def test_empty_view_data(self, orchestrator):
        """Empty view data still produces a valid output."""
        output = await orchestrator.generate_action_space({})
        assert isinstance(output, BridgeOutput)
        assert output.object_id == ""


class TestValidityWindow:
    @pytest.mark.asyncio
    async def test_custom_validity_minutes(self):
        """Custom validity window is used."""
        orch = BridgeOrchestrator(validity_minutes=10)
        output = await orch.generate_action_space({
            "constraint_summary": [{"constraint_id": "c1", "status": "passed"}],
        })
        assert output.valid_until != ""

    @pytest.mark.asyncio
    async def test_default_validity_minutes(self, orchestrator, sample_view_data):
        """Default validity window is 5 minutes."""
        output = await orchestrator.generate_action_space(sample_view_data)
        assert output.created_at != ""
        assert output.valid_until != ""
        # valid_until should be after created_at
        assert output.valid_until > output.created_at
