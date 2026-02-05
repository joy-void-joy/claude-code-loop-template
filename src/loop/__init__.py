"""Self-improving agent template.

This package provides the core scaffolding for building agents that can
review their own traces and improve over time.

Structure:
- loop/agent/: Agent code (feedback loop improves this)
  - core.py: Main agent orchestration
  - config.py: Configuration via pydantic-settings
  - history.py: Session storage and retrieval
  - models.py: Output models
  - subagents.py: Subagent definitions
  - tool_policy.py: Conditional tool availability
  - notes_access.py: RO/RW notes directory structure
  - hooks.py: Hook utilities and composition
  - tools/metrics.py: Tool call tracking

- loop/environment/: Domain scaffolding (user interaction, game logic, etc.)
  - client.py: Entry point for running agent sessions
"""
