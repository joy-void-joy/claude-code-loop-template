# Claude Code Self-Improvement Loop Template

A template for building agents that review their own traces and improve over time. Based on the [Bitter Lesson](http://www.incompleteideas.net/IncsIdeas/BitterLesson.html): general methods that scale with computation beat hand-crafted solutions.

## Ready Out of the Box

**After cloning, this template is immediately usable with Claude Code.** The `.claude/` directory contains project-scoped configuration that provides:

- Pre-configured permissions for common operations
- Slash commands for the feedback loop workflow
- Hooks for code quality and TDD enforcement
- Official plugins for GitHub, pyright LSP, and Agent SDK development

No additional setup required — just clone, run `uv sync`, and start using the commands.

## The Core Idea

Instead of engineering solutions, give the agent capabilities and let it tell you what it needs. The feedback loop operates at three levels:

- **Object level**: The agent's behavior — tools, capabilities, data access
- **Meta level**: The agent's self-tracking — what it monitors about itself
- **Meta-meta level**: The feedback loop process — scripts, analysis methods, documentation

Each feedback loop session should touch all three levels.

## Quick Start

```bash
# Clone the template
git clone <this-repo> my-agent
cd my-agent

# Install dependencies
uv sync

# Initialize for your domain (in Claude Code)
/loop:init
```

The `/loop:init` command will ask about your domain and generate customized:
- `feedback_collect.py` — Session feedback collection
- `CLAUDE.md` sections — Project-specific instructions
- Model definitions — Output schemas for your domain

## Project Structure

```
.claude/
├── CLAUDE.md                    # Project instructions
├── settings.json                # Permissions and plugins
└── plugins/
    └── loop/                    # Self-improvement scaffolding
        ├── commands/            # Slash commands (/loop:*)
        │   ├── init.md          # Domain initialization wizard
        │   ├── feedback-loop.md # 3-level meta analysis
        │   ├── meta.md          # .claude structure review
        │   ├── add-command.md   # Create new commands
        │   ├── update-docs.md   # Update documentation
        │   ├── commit.md        # Atomic commit workflow
        │   └── rebase.md        # Rebase and PR workflow
        ├── hooks/               # Pre-tool-use hooks
        │   ├── hooks.json       # Hook configuration
        │   └── scripts/
        │       ├── pre_push_check.py  # Quality checks before push
        │       ├── check_plan_md.py   # PLAN.md warning for features
        │       └── protect_tests.py   # TDD test file protection
        └── scripts/             # CLI analysis tools
            ├── feedback_collect.py   # Session feedback
            ├── trace_analysis.py     # Trace inspection
            └── aggregate_metrics.py  # Cross-session metrics

src/
└── loop/                        # Main package
    ├── agent/                   # Agent code (feedback loop improves this)
    │   ├── core.py              # Main orchestration
    │   ├── config.py            # Configuration via pydantic-settings
    │   ├── models.py            # Output schemas
    │   ├── subagents.py         # Subagent definitions
    │   ├── tool_policy.py       # Conditional tool availability
    │   ├── hooks.py             # Hook utilities
    │   ├── history.py           # Session storage
    │   └── tools/
    │       └── metrics.py       # Tool tracking
    └── environment/             # Domain scaffolding (user interaction, game logic)
        └── client.py            # Entry point

notes/
├── sessions/                    # Saved session outputs
├── traces/                      # Reasoning traces
└── feedback_loop/               # Analysis results
```

## Claude Code Configuration (`.claude/`)

The `.claude/` directory provides project-scoped configuration that makes this template immediately functional.

### Slash Commands

All commands are prefixed with `/loop:` and provide workflows for the self-improvement cycle.

| Command | Description |
|---------|-------------|
| `/loop:init` | Initialize the feedback loop for a new domain. Interviews you about your agent's purpose, metrics, and feedback sources, then generates customized scaffolding. |
| `/loop:feedback-loop` | Run the full 3-level meta analysis: collect feedback, read traces, extract patterns, implement changes, and update documentation. |
| `/loop:meta` | Review and improve the `.claude/` structure itself. Brainstorm improvements interactively. |
| `/loop:add-command` | Create a new slash command in the loop plugin. Guides you through naming, purpose, and tool requirements. |
| `/loop:update-docs` | Update CLAUDE.md with learnings from the current session. Proposes specific changes for approval. |
| `/loop:commit` | Review all uncommitted changes and create atomic commits with conventional commit format. |
| `/loop:rebase` | Clean up commit history and create a pull request. Proposes a structure and guides you through rebasing. |

### Hooks

Hooks run automatically before certain tool calls to enforce quality standards.

| Hook | Trigger | Behavior |
|------|---------|----------|
| **Pre-push checks** | `git push` | Runs pyright, ruff, and pytest. Auto-fixes formatting where possible. Blocks push if checks fail. |
| **PLAN.md check** | `git push` on `feat/` branches | Warns if PLAN.md doesn't exist for feature branches. |
| **Test file protection** | Edit/Write to test files | Requires user approval for test modifications. Hard blocks when TDD mode is active (`.tdd-mode` file exists). |

#### TDD Mode

Create a `.tdd-mode` file in the project root to enforce strict TDD discipline:

```bash
touch .tdd-mode    # Enable TDD mode - blocks test file edits
rm .tdd-mode       # Disable TDD mode - allows test edits with approval
```

When active, Claude cannot modify test files and must report what changes are needed instead.

### Permissions

The template pre-configures safe permissions in `settings.json`:

**Allowed:**
- Web fetch from Claude docs and Pydantic AI docs
- Web search
- Running pyright, pytest, ruff via `uv run`
- Running feedback loop scripts
- Git add and commit operations

**Denied:**
- Reading `.local` files (secrets)
- Running arbitrary Python via `-c` or heredocs (The agent should be writing scripts in .claude/plugins/loop/scripts to be approved once and then can reuse them)
- Running Python directly (must use `uv run`)

**Ask (requires approval):**
- Editing `pyproject.toml`

### Enabled Plugins

| Plugin | Purpose |
|--------|---------|
| `loop@local` | This template's self-improvement loop |
| `github@claude-plugins-official` | GitHub CLI integration |
| `pyright-lsp@claude-plugins-official` | Type checking diagnostics |
| `agent-sdk-dev@claude-plugins-official` | Agent SDK development tools |
| `commit-commands@claude-plugins-official` | Git commit workflows |
| `claude-md-management@claude-plugins-official` | CLAUDE.md maintenance |

## The Feedback Loop

Run `/loop:feedback-loop` to:

1. **Collect ground truth** — Match sessions to outcomes when available
2. **Read traces deeply** — Don't skip to aggregates; read 5-10 sessions in detail
3. **Extract patterns** — Tool failures, capability requests, reasoning quality
4. **Implement changes** — Fix tools → Build requested capabilities → Simplify prompts
5. **Update documentation** — This process should improve itself

### What Gets Tracked

Every session saves:
- **Structured output** — Via Pydantic models
- **Reasoning trace** — Full agent thinking
- **Tool metrics** — Calls, durations, errors
- **Token usage** — For cost analysis

## Design Principles

### Bitter Lesson Application

| Do This | Not This |
|---------|----------|
| Add tools that provide data | Add prompt rules that constrain behavior |
| Apply general principles | Apply specific pattern patches |
| Create subagents for specialized work | Build complex pipelines in main agent |
| Let the agent tell you what it needs | Guess what the agent needs |

### When to Modify What

- **Add a tool**: When the agent repeatedly fails to get information it needs
- **Add a subagent**: When a task is distinct enough to warrant specialized prompting
- **Modify a prompt**: Only for general principles; never for specific patterns
- **Update CLAUDE.md**: When you learn something that should persist

### Anti-Patterns

- ❌ Adding numeric patches ("always subtract 10%")
- ❌ Adding rules the agent can't act on (no access to required data)
- ❌ Skipping trace analysis to jump to aggregates
- ❌ Over-engineering before running sessions

## Analysis Scripts

These scripts can be run directly or are used by `/loop:feedback-loop`:

```bash
# Feedback collection
uv run python .claude/plugins/loop/scripts/feedback_collect.py --all-time

# Trace analysis
uv run python .claude/plugins/loop/scripts/trace_analysis.py list
uv run python .claude/plugins/loop/scripts/trace_analysis.py show <session_id>
uv run python .claude/plugins/loop/scripts/trace_analysis.py errors

# Aggregate metrics
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py summary
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py tools
```

## Adapting for Your Domain

1. **Run `/loop:init`** — Answer questions about your domain
2. **Customize models** — Edit `src/loop/agent/models.py` for your output schema
3. **Add tools** — Create domain-specific tools in `src/loop/agent/tools/`
4. **Define subagents** — Add specialized agents in `src/loop/agent/subagents.py`
5. **Build environment** — Add user interaction/game logic in `src/loop/environment/`
6. **Run sessions** — Generate data for the feedback loop
7. **Iterate** — Let the feedback loop tell you what to build next

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://docs.claude.com/en/claude-code) for running commands

## License

MIT
