"""Tests for output models."""

from lup.agent.models import get_output_schema


class TestOutputSchema:
    """Tests for JSON schema generation."""

    def test_schema_has_required_fields(self) -> None:
        """Schema should include required fields."""
        schema = get_output_schema()

        assert "properties" in schema
        assert "summary" in schema["properties"]
        assert "confidence" in schema["properties"]
