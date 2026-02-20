"""Output models for the agent.

This is a TEMPLATE. Customize these models for your domain.

The key pattern is:
1. Define Pydantic models for structured agent output
2. Use these models with the Claude SDK's output_format option
3. Store results in notes/sessions/ for feedback loop analysis
"""

from typing import TypedDict

from pydantic import BaseModel, Field

from lup.lib.metrics import MetricsSummary


class TokenUsage(TypedDict, total=False):
    """Token usage from Claude API responses."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


# =============================================================================
# CUSTOMIZE THESE FOR YOUR DOMAIN
# =============================================================================


class Factor(BaseModel):
    """A single factor influencing the output.

    Customize this for your domain. Examples:
    - For forecasting: text, direction (pro/con), weight
    - For coaching: insight, relevance, actionability
    - For game playing: consideration, evaluation, confidence
    """

    text: str = Field(description="Description of the factor")
    factor_type: str = Field(description="Type of factor (customize for your domain)")
    weight: float = Field(default=1.0, description="Relative importance (1-5 scale)")


class AgentOutput(BaseModel):
    """Structured output from the agent.

    Customize this for your domain. This model should capture:
    1. The main output/decision
    2. The reasoning that led to it
    3. Confidence or uncertainty measures

    Examples:

    For forecasting:
        probability: float
        summary: str
        factors: list[Factor]

    For coaching:
        response: str
        insights: list[str]
        suggested_actions: list[str]

    For game playing:
        move: str
        evaluation: float
        considerations: list[Factor]
    """

    summary: str = Field(description="Summary of the output/decision")
    factors: list[Factor] = Field(default_factory=list, description="Key factors")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the output (0-1)",
    )

    # TODO: Add domain-specific fields
    # probability: float  # For forecasting
    # move: str           # For game playing
    # response: str       # For coaching


class SessionResult(BaseModel):
    """Complete result of an agent session.

    This captures everything needed for the feedback loop:
    - The structured output
    - Metadata (timing, cost, token usage)
    - Tool metrics for analysis
    """

    session_id: str
    task_id: str | None = Field(default=None, description="Domain-specific task ID")
    agent_version: str = Field(
        default="", description="Agent version that produced this result"
    )
    timestamp: str
    output: AgentOutput
    reasoning: str = Field(default="", description="Raw reasoning text")
    sources_consulted: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    cost_usd: float | None = None
    token_usage: TokenUsage | None = None
    tool_metrics: MetricsSummary | None = None
    outcome: str | None = Field(default=None, description="Outcome after resolution")


# =============================================================================
# OUTPUT SCHEMA HELPER
# =============================================================================


def get_output_schema() -> dict:
    """Get the JSON schema for AgentOutput.

    Use this with ClaudeAgentOptions.output_format:

        options = ClaudeAgentOptions(
            output_format={
                "type": "json_schema",
                "schema": get_output_schema(),
            }
        )
    """
    return AgentOutput.model_json_schema()
