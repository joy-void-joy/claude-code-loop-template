"""System prompts for the agent.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Use {date} placeholder for current date
2. Specify output format requirements and reasoning guidance
3. Include domain-specific guidance
4. Tools self-document via their descriptions — listing them here
   creates a second source of truth that drifts as tools change
   (see Tool Design Philosophy in CLAUDE.md)
"""

from datetime import datetime
from typing import Any


# Base system prompt template - customize for your domain
_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI agent. Today's date is {date}.

## Your Task

[Describe what the agent does]

## Output Format

Provide your output as structured JSON with:
- **summary**: Brief summary of your decision/output
- **factors**: Key factors that influenced your reasoning
- **confidence**: Your confidence level (0.0-1.0)

## Guidelines

1. Think step by step
2. Use your available tools to gather information before reasoning
3. Be explicit about uncertainty
4. Document your reasoning

[Add domain-specific guidelines here]
"""


def get_system_prompt(
    *,
    date: datetime | None = None,
    mcp_servers: dict[str, Any] | None = None,
) -> str:
    """Generate the system prompt.

    Args:
        date: Date to use as "today". If None, uses current date.
        mcp_servers: Optional dict of MCP servers to auto-generate tool docs.

    Returns:
        The formatted system prompt.
    """
    effective_date = date or datetime.now()
    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        date=effective_date.strftime("%Y-%m-%d")
    )

    # If MCP servers provided, append auto-generated tool docs
    if mcp_servers:
        tool_docs = generate_tool_docs(mcp_servers)
        prompt += f"\n\n{tool_docs}"

    return prompt


def generate_tool_docs(mcp_servers: dict[str, Any]) -> str:
    """Generate tool documentation from MCP server tool descriptions.

    Tool descriptions are the single source of truth for what each tool does,
    when to use it, and why it exists. This function passes them through
    untruncated — comprehensive descriptions are intentional.
    """
    lines = ["## Auto-Generated Tool Reference\n"]

    for server_name, server_config in mcp_servers.items():
        tools = getattr(server_config, "tools", [])
        if not tools:
            continue

        lines.append(f"### {server_name.title()}\n")

        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))
            tool_desc = getattr(tool, "description", "")

            if tool_desc:
                lines.append(f"- **{tool_name}**: {tool_desc}")
            else:
                lines.append(f"- **{tool_name}**")

        lines.append("")

    return "\n".join(lines)


# --- Example Type-Specific Guidance ---
# Customize these for your domain

BINARY_GUIDANCE = """\
## Binary Decision Guidance

Consider:
- What happens if nothing changes (status quo)?
- Strongest argument FOR this outcome
- Strongest argument AGAINST this outcome

Output probability as a decimal between 0.01 and 0.99.
"""

NUMERIC_GUIDANCE = """\
## Numeric Estimation Guidance

Consider:
- Current value and recent trend
- Historical range and volatility
- Expert/market expectations
- Scenarios for low and high outcomes

Provide estimates at multiple confidence levels.
"""


def get_task_guidance(task_type: str, context: dict | None = None) -> str:
    """Return task-specific guidance.

    Args:
        task_type: Type of task (binary, numeric, etc.)
        context: Optional context dict with task details

    Returns:
        Formatted guidance string.
    """
    if task_type == "binary":
        return BINARY_GUIDANCE
    elif task_type == "numeric":
        return NUMERIC_GUIDANCE
    return ""
