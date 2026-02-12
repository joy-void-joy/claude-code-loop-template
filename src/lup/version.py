"""Agent version tracking.

AGENT_VERSION tracks the agent's behavior — prompts, tools, subagents,
scoring logic. Bump this when agent behavior changes, NOT for data
commits, dependency updates, or infrastructure changes.

Bump rules:
- Patch (0.1.x): bug fixes, config tweaks, tool fixes
- Minor (0.x.0): prompt changes, new tools, subagent modifications
- Major (x.0.0): architecture changes (new LLM, new framework)
"""

AGENT_VERSION = "0.1.0"
