"""Main agent orchestration.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Use ClaudeAgentOptions with structured output
2. Create MCP servers with create_mcp_server()
3. Track tool metrics with the @tracked decorator
4. Save sessions for feedback loop analysis
5. Use hooks for permission control
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import cast

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)

from claude_agent_sdk import create_sdk_mcp_server

from loop.agent.config import settings
from loop.agent.models import AgentOutput, SessionResult, TokenUsage, get_output_schema
from loop.agent.prompts import get_system_prompt
from loop.agent.subagents import SUBAGENTS
from loop.agent.tool_policy import ToolPolicy
from loop.agent.tools.example import EXAMPLE_TOOLS
from loop.lib import (
    HooksConfig,
    TraceLogger,
    create_permission_hooks,
    get_metrics_summary,
    log_metrics_summary,
    print_block,
    reset_metrics,
    save_session,
    setup_notes,
)

logger = logging.getLogger(__name__)

# Base paths
NOTES_PATH = Path("./notes")
TRACES_PATH = NOTES_PATH / "traces"


async def run_agent(
    task: str,
    *,
    session_id: str | None = None,
    task_id: str | None = None,
) -> SessionResult:
    """Run the agent on a task.

    Args:
        task: The task/prompt for the agent.
        session_id: Unique identifier for this session. Auto-generated if None.
        task_id: Optional task identifier (e.g., question ID for forecasting).

    Returns:
        SessionResult with the agent's output and metadata.
    """
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("Starting session %s", session_id)

    # Reset metrics for this session
    reset_metrics()

    # Setup notes folder structure
    notes = setup_notes(session_id, task_id or "0")

    # Setup trace logging
    trace_path = TRACES_PATH / session_id / f"{datetime.now().strftime('%H%M%S')}.md"
    trace_logger = TraceLogger(trace_path=trace_path, title=f"Session {session_id}")

    collected_text: list[str] = []
    assistant_messages: list[AssistantMessage] = []
    result: ResultMessage | None = None

    # Create MCP servers for your tools
    # TODO: Replace with your actual tool servers
    example_server = create_sdk_mcp_server(
        name="example",
        version="1.0.0",
        tools=EXAMPLE_TOOLS,
    )

    # Get tool policy (conditional availability based on API keys)
    policy = ToolPolicy.from_settings(settings)

    # Create permission hooks from notes directories
    permission_hooks = create_permission_hooks(notes.rw, notes.ro)

    # Merge with any additional hooks
    hooks: HooksConfig = permission_hooks
    # Example: hooks = merge_hooks(permission_hooks, quality_hooks)

    options = ClaudeAgentOptions(
        model=settings.model,
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": get_system_prompt(),
        },
        max_thinking_tokens=settings.max_thinking_tokens or (64_000 - 1),
        permission_mode="bypassPermissions",
        hooks=hooks,  # type: ignore[arg-type]
        sandbox={
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
        },
        mcp_servers=policy.get_mcp_servers(example_server),
        agents=SUBAGENTS,
        add_dirs=[str(d) for d in notes.all_dirs],
        allowed_tools=policy.get_allowed_tools(),
        output_format={
            "type": "json_schema",
            "schema": get_output_schema(),
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(task)

        async for message in client.receive_response():
            match message:
                case AssistantMessage():
                    assistant_messages.append(message)
                    for block in message.content:
                        print_block(block)
                        trace_logger.log_block(block)
                        if isinstance(block, TextBlock):
                            collected_text.append(block.text)

                case ResultMessage():
                    result = message
                    if message.is_error:
                        raise RuntimeError(f"Agent error: {message.result}")

                case SystemMessage():
                    logger.info("System [%s]: %s", message.subtype, message.data)

                case UserMessage():
                    if isinstance(message.content, list):
                        for block in message.content:
                            print_block(block)
                            trace_logger.log_block(block)

    if result is None:
        raise RuntimeError("No result received from agent")

    # Save trace
    trace_logger.save()

    # Log metrics
    log_metrics_summary()
    metrics = get_metrics_summary()

    # Extract structured output
    output = AgentOutput(summary="No output produced", factors=[], confidence=0.5)

    if result.structured_output:
        output = AgentOutput.model_validate(result.structured_output)

    # Build session result
    session_result = SessionResult(
        session_id=session_id,
        task_id=task_id,
        timestamp=datetime.now().isoformat(),
        output=output,
        reasoning="".join(collected_text),
        sources_consulted=_extract_sources(assistant_messages),
        duration_seconds=(result.duration_ms / 1000) if result.duration_ms else None,
        cost_usd=result.total_cost_usd,
        token_usage=cast(TokenUsage, result.usage) if result.usage else None,
        tool_metrics=metrics,
    )

    # Save session for feedback loop
    save_session(session_result)

    return session_result


def _extract_sources(messages: list[AssistantMessage]) -> list[str]:
    """Extract sources from tool use blocks."""
    sources = []
    for msg in messages:
        for block in msg.content:
            if isinstance(block, ToolUseBlock) and block.name in ("WebSearch", "WebFetch"):
                if isinstance(block.input, dict):
                    source = block.input.get("url") or block.input.get("query")
                    if source:
                        sources.append(str(source))
    return sources
