"""Tests for output models."""

from lup.agent.models import AgentOutput, Factor, SessionResult, get_output_schema


class TestAgentOutput:
    """Tests for AgentOutput model."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        output = AgentOutput(summary="Test summary")

        assert output.summary == "Test summary"
        assert output.factors == []
        assert output.confidence == 0.5

    def test_with_factors(self) -> None:
        """Should accept factors."""
        factor = Factor(text="Test factor", factor_type="consideration")
        output = AgentOutput(
            summary="Test",
            factors=[factor],
            confidence=0.8,
        )

        assert len(output.factors) == 1
        assert output.factors[0].text == "Test factor"
        assert output.confidence == 0.8

    def test_confidence_bounds(self) -> None:
        """Confidence should be between 0 and 1."""
        output = AgentOutput(summary="Test", confidence=0.0)
        assert output.confidence == 0.0

        output = AgentOutput(summary="Test", confidence=1.0)
        assert output.confidence == 1.0


class TestSessionResult:
    """Tests for SessionResult model."""

    def test_minimal_creation(self) -> None:
        """Should create with minimal fields."""
        output = AgentOutput(summary="Test")
        result = SessionResult(
            session_id="test-123",
            timestamp="2026-01-01T00:00:00",
            output=output,
        )

        assert result.session_id == "test-123"
        assert result.output.summary == "Test"
        assert result.reasoning == ""
        assert result.sources_consulted == []


class TestOutputSchema:
    """Tests for JSON schema generation."""

    def test_schema_has_required_fields(self) -> None:
        """Schema should include required fields."""
        schema = get_output_schema()

        assert "properties" in schema
        assert "summary" in schema["properties"]
        assert "confidence" in schema["properties"]
