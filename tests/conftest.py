"""Shared test fixtures.

Add fixtures here that are used across multiple test files.
"""

import pytest

from loop.agent.models import AgentOutput, Factor, SessionResult


@pytest.fixture
def sample_output() -> AgentOutput:
    """Sample agent output for testing."""
    return AgentOutput(
        summary="Test summary",
        factors=[
            Factor(text="Factor 1", factor_type="consideration"),
            Factor(text="Factor 2", factor_type="evidence"),
        ],
        confidence=0.75,
    )


@pytest.fixture
def sample_session(sample_output: AgentOutput) -> SessionResult:
    """Sample session result for testing."""
    return SessionResult(
        session_id="test-session-123",
        timestamp="2026-01-01T12:00:00",
        output=sample_output,
        reasoning="This is the reasoning text.",
        sources_consulted=["https://example.com"],
        duration_seconds=10.5,
        cost_usd=0.05,
    )
