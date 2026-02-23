"""Self-improving agent template.

This package provides the core scaffolding for building agents that can
review their own traces and improve over time.

Structure:
- lup/agent/: Agent code (feedback loop improves this)
  - core.py: Main agent orchestration
  - config.py: Configuration via pydantic-settings
  - history.py: Session storage and retrieval
  - models.py: Output models
  - subagents.py: Subagent definitions
  - tool_policy.py: Conditional tool availability
  - notes_access.py: RO/RW notes directory structure
  - hooks.py: Hook utilities and composition
  - tools/metrics.py: Tool call tracking

- lup/environment/: Domain scaffolding (user interaction, game logic, etc.)
  - client.py: Entry point for running agent sessions

- lup/lib/: Library utilities for self-improving agents.
  - client.py: Agent SDK client (build_client, run_query, one_shot)
  - history.py: Session storage and retrieval
  - hooks.py: Hook utilities and composition
  - metrics.py: Tool call tracking
  - mcp.py: MCP server creation utilities
  - notes.py: RO/RW directory structure
  - paths.py: Centralized version-aware path constants and helpers
  - realtime.py: Scheduler for persistent agents (sleep/wake, debounce)
  - reflect.py: Reflection gate (enforce reflect-before-output)
  - responses.py: MCP response formatting
  - retry.py: Retry decorator with backoff
  - sandbox.py: Docker-based Python sandbox for isolated code execution
  - trace.py: Trace logging, color-coded console display
"""
