"""Subagent definitions.

This is a TEMPLATE. Define subagents for specialized tasks in your domain.

Subagents are spawned by the main agent to perform focused work.
Each subagent has:
- A specialized prompt
- A subset of tools
- Its own model (can be cheaper for simpler tasks)

Examples from different domains:

Forecasting:
- deep-researcher: Extensive research on a topic
- estimator: Fermi estimation with code execution
- fact-checker: Cross-validate claims

Coaching:
- empathy-agent: Understand user's emotional state
- action-planner: Create actionable next steps
- accountability-tracker: Follow up on commitments

Game Playing:
- position-evaluator: Assess current position
- move-generator: Generate candidate moves
- opponent-modeler: Predict opponent behavior
"""

from claude_agent_sdk import AgentDefinition

# =============================================================================
# TOOL LISTS (customize for your domain)
# =============================================================================
#
# Use functions (not constants) so tool lists can be computed at runtime
# based on available API keys, session context, etc.
#
# Example with conditional inclusion:
#   def _research_tools() -> list[str]:
#       from lup.agent.config import settings
#       tools = ["WebSearch", "WebFetch", "Read", "Glob"]
#       if settings.exa_api_key:
#           tools.append("mcp__search__search_exa")
#       return tools


def _research_tools() -> list[str]:
    """Tools for research subagents."""
    return [
        "WebSearch",
        "WebFetch",
        "Read",
        "Glob",
        # Add domain-specific tools
    ]


def _analysis_tools() -> list[str]:
    """Tools for analysis subagents."""
    return [
        "Read",
        "Glob",
        # Add analysis tools
    ]


# =============================================================================
# SUBAGENT DEFINITIONS (customize for your domain)
# =============================================================================


RESEARCHER_PROMPT = """\
You are a research assistant gathering information on a topic.

## Your Task
Research the topic/question given to you. Your output should be thorough and factual.

## Approach
1. Search for relevant information
2. Verify facts across multiple sources
3. Note any uncertainties or contradictions
4. Organize findings clearly

## Output Format (JSON)
```json
{
  "key_facts": ["Fact 1 with source", "Fact 2 with source"],
  "uncertainties": ["What we don't know"],
  "sources": [{"title": "...", "url": "..."}],
  "summary": "Brief synthesis of findings"
}
```
"""

researcher = AgentDefinition(
    description=(
        "Research agent for gathering information. Searches multiple sources, "
        "verifies facts, and returns organized findings."
    ),
    prompt=RESEARCHER_PROMPT,
    tools=_research_tools(),
    model="haiku",  # Use cheaper model for research tasks
)


ANALYZER_PROMPT = """\
You are an analysis assistant examining data or content.

## Your Task
Analyze the given data/content and extract insights.

## Approach
1. Understand what you're analyzing
2. Identify patterns and anomalies
3. Draw conclusions
4. Note confidence levels

## Output Format (JSON)
```json
{
  "insights": ["Insight 1", "Insight 2"],
  "patterns": ["Pattern observed"],
  "anomalies": ["Unusual finding"],
  "confidence": 0.8,
  "summary": "Brief analysis summary"
}
```
"""

analyzer = AgentDefinition(
    description=(
        "Analysis agent for examining data and extracting insights. "
        "Identifies patterns, anomalies, and draws conclusions."
    ),
    prompt=ANALYZER_PROMPT,
    tools=_analysis_tools(),
    model="haiku",
)


# =============================================================================
# EXPORTED SUBAGENTS
# =============================================================================


def get_subagents() -> dict[str, AgentDefinition]:
    """Build subagent definitions at runtime.

    Using a factory function (not a module constant) allows:
    - Tool lists computed from current settings/API keys
    - Context-dependent subagent configuration
    - Runtime reconfiguration between sessions
    """
    return {
        "researcher": researcher,
        "analyzer": analyzer,
        # Add more subagents for your domain
    }
