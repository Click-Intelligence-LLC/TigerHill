"""
Real AgentBay integration tests.

These tests require:
1. AGENTBAY_API_KEY environment variable set
2. wuying-agentbay-sdk installed
3. Network connection to Alibaba Cloud

To run these tests:
    export AGENTBAY_API_KEY=your_api_key
    pytest tests/test_agentbay_real.py -v -s
"""

import os
import pytest
import time


def check_prerequisites():
    """Check if all prerequisites are met."""
    issues = []

    # Check API key
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        issues.append("AGENTBAY_API_KEY not set")

    # Check SDK installation
    try:
        import agentbay
    except ImportError:
        issues.append("wuying-agentbay-sdk not installed")

    return issues


# Check prerequisites before running tests
prerequisites = check_prerequisites()
skip_reason = "Missing prerequisites: " + ", ".join(prerequisites) if prerequisites else ""
should_skip = len(prerequisites) > 0


@pytest.mark.skipif(should_skip, reason=skip_reason or "No prerequisites issues")
class TestAgentBayReal:
    """Real integration tests with AgentBay platform."""

    def test_client_initialization(self):
        """Test AgentBay client can be initialized with API key."""
        from tigerhill.agentbay.client import AgentBayClient

        print("\n[TEST] Initializing AgentBay client...")
        client = AgentBayClient()

        assert client is not None
        assert client.api_key is not None
        print("✓ Client initialized successfully")

    def test_create_and_delete_session(self):
        """Test creating and deleting an AgentBay session."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        print("\n[TEST] Creating AgentBay session...")
        client = AgentBayClient()

        # Create session
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        print(f"✓ Session created: {session['session_id']}")
        print(f"  - Status: {session['status']}")
        print(f"  - Environment: {session['env_type']}")

        assert session["session_id"] is not None
        assert session["status"] == "active"

        session_id = session["session_id"]

        # Wait a moment for session to be ready
        time.sleep(1)

        # Delete session
        print(f"[TEST] Deleting session {session_id}...")
        success = client.delete_session(session_id)

        assert success is True
        print("✓ Session deleted successfully")

    def test_execute_command(self):
        """Test executing a command in AgentBay environment."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        print("\n[TEST] Executing command in AgentBay...")
        client = AgentBayClient()

        # Create session
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        session_id = session["session_id"]
        print(f"✓ Session created: {session_id}")

        try:
            # Wait for session to be ready
            time.sleep(2)

            # Execute command
            print("[TEST] Running command: echo 'Hello from TigerHill!'")
            result = client.execute_command(
                session_id,
                "echo 'Hello from TigerHill!'"
            )

            print(f"✓ Command executed")
            print(f"  - Output: {result['output']}")
            print(f"  - Exit Code: {result['exit_code']}")

            assert result["output"] is not None
            assert "Hello from TigerHill!" in result["output"]
            assert result["exit_code"] == 0

        finally:
            # Cleanup
            client.delete_session(session_id)
            print("✓ Session cleaned up")

    def test_execute_python_code(self):
        """Test executing Python code in AgentBay environment."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        print("\n[TEST] Executing Python code in AgentBay...")
        client = AgentBayClient()

        # Create session
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        session_id = session["session_id"]
        print(f"✓ Session created: {session_id}")

        try:
            # Wait for session to be ready
            time.sleep(2)

            # Execute Python code
            python_code = "print(f'6 + 7 = {6 + 7}')"
            print(f"[TEST] Running Python: {python_code}")
            result = client.execute_command(
                session_id,
                f"python -c \"{python_code}\""
            )

            print(f"✓ Python executed")
            print(f"  - Output: {result['output']}")

            assert "6 + 7 = 13" in result["output"]

        finally:
            # Cleanup
            client.delete_session(session_id)
            print("✓ Session cleaned up")

    def test_context_manager(self):
        """Test AgentBay client context manager."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        print("\n[TEST] Testing context manager...")

        with AgentBayClient() as client:
            print("✓ Entered context manager")

            # Create multiple sessions
            session1 = client.create_session(env_type=EnvironmentType.CODESPACE)
            print(f"✓ Created session 1: {session1['session_id']}")

            session2 = client.create_session(env_type=EnvironmentType.CODESPACE)
            print(f"✓ Created session 2: {session2['session_id']}")

            assert len(client._sessions) == 2

        # All sessions should be cleaned up automatically
        print("✓ Exited context manager (sessions auto-cleaned)")

    def test_load_tools(self):
        """Test loading tool definitions."""
        from tigerhill.agentbay.client import AgentBayClient

        print("\n[TEST] Loading tool definitions...")
        client = AgentBayClient()

        # Load command tools
        tools = client.load_tools("command")
        print(f"✓ Loaded 'command' tools: {len(tools)} tools")

        assert len(tools) > 0
        assert any(t["name"] == "execute_command" for t in tools)

        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

    def test_get_session_status(self):
        """Test getting session status."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        print("\n[TEST] Getting session status...")
        client = AgentBayClient()

        # Create session
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        session_id = session["session_id"]

        try:
            # Get status
            status = client.get_session_status(session_id)
            print(f"✓ Retrieved session status")
            print(f"  - Session ID: {status['session_id']}")
            print(f"  - Status: {status['status']}")
            print(f"  - Env Type: {status['env_type']}")

            assert status["session_id"] == session_id
            assert status["status"] == "active"

        finally:
            client.delete_session(session_id)


@pytest.mark.skipif(should_skip, reason=skip_reason or "No prerequisites issues")
class TestAgentBayWithTraceStore:
    """Test AgentBay integration with TraceStore."""

    def test_trace_agentbay_execution(self):
        """Test tracing AgentBay command execution."""
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType
        from tigerhill.storage.trace_store import TraceStore, EventType
        import tempfile
        import shutil

        print("\n[TEST] Tracing AgentBay execution...")

        # Create trace store
        temp_dir = tempfile.mkdtemp()

        try:
            store = TraceStore(storage_path=temp_dir, auto_save=True)
            client = AgentBayClient()

            # Start trace
            trace_id = store.start_trace(
                agent_name="agentbay_test",
                task_id="command_test",
                metadata={"test": "agentbay_integration"}
            )
            print(f"✓ Started trace: {trace_id}")

            # Create session
            session = client.create_session(env_type=EnvironmentType.CODESPACE)
            session_id = session["session_id"]

            # Record session creation
            store.write_event({
                "type": "custom",
                "event": "session_created",
                "session_id": session_id
            })
            print("✓ Recorded session creation")

            try:
                time.sleep(2)

                # Execute command
                result = client.execute_command(session_id, "echo 'test'")

                # Record command execution
                store.write_event({
                    "type": "tool_call",
                    "tool": "execute_command",
                    "args": {"command": "echo 'test'"}
                })

                store.write_event({
                    "type": "tool_result",
                    "tool": "execute_command",
                    "result": result["output"]
                })
                print("✓ Recorded command execution")

            finally:
                client.delete_session(session_id)

                # Record session deletion
                store.write_event({
                    "type": "custom",
                    "event": "session_deleted",
                    "session_id": session_id
                })

            # End trace
            store.end_trace(trace_id)
            print("✓ Ended trace")

            # Verify trace
            summary = store.get_summary(trace_id)
            print(f"\nTrace Summary:")
            print(f"  - Total Events: {summary['total_events']}")
            print(f"  - Duration: {summary['duration_seconds']:.2f}s")
            print(f"  - Event Counts: {summary['event_counts']}")

            assert summary["total_events"] >= 4  # At least 4 events

        finally:
            shutil.rmtree(temp_dir)


def print_setup_instructions():
    """Print setup instructions if prerequisites are missing."""
    issues = check_prerequisites()

    if not issues:
        print("\n✓ All prerequisites met! Ready to run tests.\n")
        return

    print("\n" + "="*70)
    print("⚠ AgentBay Real Tests - Prerequisites Missing")
    print("="*70)

    for issue in issues:
        print(f"  ✗ {issue}")

    print("\n" + "-"*70)
    print("Setup Instructions:")
    print("-"*70)

    if "AGENTBAY_API_KEY not set" in issues:
        print("\n1. Get your AgentBay API Key:")
        print("   - Visit: https://agentbay.console.aliyun.com/service-management")
        print("   - Create or copy your API key")
        print("   - Set environment variable:")
        print("     export AGENTBAY_API_KEY=your_api_key_here")

    if "wuying-agentbay-sdk not installed" in issues:
        print("\n2. Install AgentBay SDK:")
        print("   pip install wuying-agentbay-sdk")

    print("\n" + "-"*70)
    print("After setup, run tests with:")
    print("  pytest tests/test_agentbay_real.py -v -s")
    print("="*70 + "\n")


if __name__ == "__main__":
    print_setup_instructions()

    if not check_prerequisites():
        print("Running tests...\n")
        pytest.main([__file__, "-v", "-s"])
