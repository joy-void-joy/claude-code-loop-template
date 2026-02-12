"""Tests for ToolPolicy class."""

from lup.agent.tool_policy import BUILTIN_TOOLS, ToolPolicy


class TestToolPolicyToolSets:
    """Tests for tool set constants."""

    def test_builtin_tools_present(self) -> None:
        """Built-in tools should be defined."""
        assert "WebSearch" in BUILTIN_TOOLS
        assert "WebFetch" in BUILTIN_TOOLS
        assert "Bash" in BUILTIN_TOOLS
        assert "Task" in BUILTIN_TOOLS


class TestToolPolicyConstruction:
    """Tests for ToolPolicy construction."""

    def test_default_construction(self) -> None:
        """Should construct with defaults."""
        policy = ToolPolicy()

        assert not policy.restricted_mode
        assert policy._excluded_tools == frozenset()

    def test_restricted_mode(self) -> None:
        """Should accept restricted mode flag."""
        policy = ToolPolicy(restricted_mode=True)

        assert policy.restricted_mode


class TestToolPolicyAllowedTools:
    """Tests for get_allowed_tools method."""

    def test_includes_builtin_tools(self) -> None:
        """Should include all built-in tools."""
        policy = ToolPolicy()
        allowed = policy.get_allowed_tools()

        for tool in BUILTIN_TOOLS:
            assert tool in allowed

    def test_returns_sorted_list(self) -> None:
        """Should return sorted list of tools."""
        policy = ToolPolicy()
        allowed = policy.get_allowed_tools()

        assert allowed == sorted(allowed)


class TestToolPolicyIsToolAvailable:
    """Tests for is_tool_available method."""

    def test_builtin_always_available(self) -> None:
        """Built-in tools should always be available."""
        policy = ToolPolicy()

        for tool in BUILTIN_TOOLS:
            assert policy.is_tool_available(tool)

    def test_unknown_tool_available(self) -> None:
        """Unknown tools should be available (not excluded)."""
        policy = ToolPolicy()

        assert policy.is_tool_available("mcp__custom__my_tool")
