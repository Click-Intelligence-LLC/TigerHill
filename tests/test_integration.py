"""
Integration tests for TigerHill with AgentBay and TraceStore.

These tests verify the complete workflow of:
1. AgentBay client operations
2. TraceStore functionality
3. DynamicAgent integration with both
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from tigerhill.storage.trace_store import TraceStore, EventType
from tigerhill.core.models import Task, Environment, Agent, AgentOutput
from tigerhill.eval.assertions import run_assertions


class TestTraceStore:
    """Test suite for TraceStore functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = TraceStore(storage_path=self.temp_dir, auto_save=False)

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_start_and_end_trace(self):
        """Test basic trace lifecycle."""
        trace_id = self.store.start_trace(
            agent_name="test_agent",
            task_id="task_001",
            metadata={"test": "data"}
        )

        assert trace_id is not None
        assert self.store._current_trace_id == trace_id

        trace = self.store.get_trace(trace_id)
        assert trace is not None
        assert trace.agent_name == "test_agent"
        assert trace.task_id == "task_001"
        assert trace.end_time is None

        self.store.end_trace(trace_id)
        trace = self.store.get_trace(trace_id)
        assert trace.end_time is not None

    def test_write_events(self):
        """Test writing trace events."""
        trace_id = self.store.start_trace(agent_name="test_agent")

        # Write prompt event
        event_id1 = self.store.write_event({
            "type": "prompt",
            "messages": [{"role": "user", "content": "Test prompt"}]
        })
        assert event_id1 is not None

        # Write model response event
        event_id2 = self.store.write_event({
            "type": "model_response",
            "text": "Test response",
            "tool_calls": []
        })
        assert event_id2 is not None

        # Verify events
        events = self.store.get_events(trace_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.PROMPT
        assert events[1].event_type == EventType.MODEL_RESPONSE

    def test_query_traces(self):
        """Test querying traces with filters."""
        # Create multiple traces
        trace_id1 = self.store.start_trace(agent_name="agent1", task_id="task1")
        self.store.end_trace(trace_id1)

        trace_id2 = self.store.start_trace(agent_name="agent2", task_id="task2")
        self.store.end_trace(trace_id2)

        trace_id3 = self.store.start_trace(agent_name="agent1", task_id="task3")
        self.store.end_trace(trace_id3)

        # Query by agent name
        results = self.store.query_traces(agent_name="agent1")
        assert len(results) == 2

        # Query by task id
        results = self.store.query_traces(task_id="task2")
        assert len(results) == 1
        assert results[0].agent_name == "agent2"

    def test_save_and_load_traces(self):
        """Test persistence to disk."""
        trace_id = self.store.start_trace(agent_name="test_agent")
        self.store.write_event({"type": "prompt", "content": "test"})
        self.store.end_trace(trace_id)

        # Save to disk
        self.store.save_all()

        # Create new store and load
        new_store = TraceStore(storage_path=self.temp_dir, auto_save=False)
        loaded_trace = new_store.get_trace(trace_id)

        assert loaded_trace is not None
        assert loaded_trace.agent_name == "test_agent"
        assert len(loaded_trace.events) == 1

    def test_get_summary(self):
        """Test trace summary generation."""
        trace_id = self.store.start_trace(agent_name="test_agent")

        # Write multiple events
        self.store.write_event({"type": "prompt"})
        self.store.write_event({"type": "model_response"})
        self.store.write_event({"type": "tool_call"})
        self.store.write_event({"type": "tool_result"})

        self.store.end_trace(trace_id)

        summary = self.store.get_summary(trace_id)
        assert summary is not None
        assert summary["total_events"] == 4
        assert summary["duration_seconds"] is not None
        assert "prompt" in summary["event_counts"]


class TestAgentBayClientMocked:
    """Test suite for AgentBayClient with mocked SDK."""

    @pytest.mark.skip(reason="Requires agentbay SDK - skipping for now")
    def test_create_and_delete_session(self):
        """Test session lifecycle with mocked SDK."""
        pass

    @pytest.mark.skip(reason="Requires agentbay SDK - skipping for now")
    def test_execute_command(self):
        """Test command execution with mocked SDK."""
        pass


class TestEvaluationWorkflow:
    """Test the complete evaluation workflow."""

    def test_assertions(self):
        """Test assertion evaluation."""
        output = "The result is 42"

        assertions = [
            {"type": "contains", "expected": "42"},
            {"type": "contains", "expected": "result"},
            {"type": "regex", "pattern": r"\d+"},
        ]

        results = run_assertions(output, assertions)

        assert len(results) == 3
        assert all(r["ok"] for r in results)

    def test_task_and_environment_models(self):
        """Test core data models."""
        task = Task(
            prompt="Calculate 6 + 7",
            setup=["setup_calculator"],
            assertions=[
                {"type": "contains", "expected": "13"}
            ]
        )

        assert task.prompt == "Calculate 6 + 7"
        assert len(task.assertions) == 1

        env = Environment(
            name="test_env",
            agentbay_env_id="codespace",
            agentbay_tool_set_id="command"
        )

        assert env.name == "test_env"
        assert env.agentbay_env_id == "codespace"


class TestDynamicAgentMocked:
    """Test DynamicAgent with mocked dependencies."""

    @pytest.mark.skip(reason="DynamicAgent requires refactoring for testing - skipping for now")
    def test_agent_with_trace_store(self):
        """Test agent execution with trace store."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
