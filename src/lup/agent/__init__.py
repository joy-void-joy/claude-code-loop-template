"""Agent module for the self-improving loop.

This subpackage contains the core agent code that the feedback loop improves:
- core.py: Main agent orchestration
- config.py: Configuration via pydantic-settings
- models.py: Output models
- subagents.py: Subagent definitions
- tool_policy.py: Conditional tool availability
- hooks.py: Hook utilities and composition
- notes_access.py: RO/RW notes directory structure
- history.py: Session storage and retrieval
- tools/metrics.py: Tool call tracking
"""
