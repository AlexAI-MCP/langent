"""Tests for langent.agents.workflows — verifies ${} interpolation bug is fixed"""
import inspect
from langent.agents.workflows import LangentWorkflows, AgentState


class TestWorkflows:
    def test_agent_state_has_required_fields(self):
        hints = AgentState.__annotations__
        assert "query" in hints
        assert "context" in hints
        assert "answer" in hints
        assert "steps" in hints

    def test_node_generate_uses_python_fstrings(self):
        """Verify that ${query} interpolation bug (v2) is fixed."""
        source = inspect.getsource(LangentWorkflows.node_generate)
        # Must NOT contain ${query}, ${context}, or ${graph_str}
        assert "${query}" not in source, "Bug: ${query} found — should be {query}"
        assert "${context}" not in source, "Bug: ${context} found — should be {context}"
        assert "${graph_str}" not in source, "Bug: ${graph_str} found — should be {graph_str}"
        # Must contain proper Python f-string interpolation
        assert "{query}" in source
        assert "{context}" in source
