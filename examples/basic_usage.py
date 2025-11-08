"""
Basic usage example for TigerHill evaluation platform.

This example demonstrates:
1. Creating and using TraceStore
2. Defining tasks and environments
3. Running assertions
4. Working with AgentBay client (if API key is available)
"""

import os
from tigerhill.storage.trace_store import TraceStore, EventType
from tigerhill.core.models import Task, Environment
from tigerhill.eval.assertions import run_assertions


def example_1_trace_store():
    """Example: Using TraceStore to record agent execution."""
    print("\n" + "="*60)
    print("Example 1: TraceStore Usage")
    print("="*60)

    # Create a trace store
    store = TraceStore(storage_path="./example_traces", auto_save=True)

    # Start a new trace
    trace_id = store.start_trace(
        agent_name="calculator_agent",
        task_id="addition_task",
        metadata={"version": "1.0", "environment": "test"}
    )
    print(f"✓ Started trace: {trace_id}")

    # Write events
    store.write_event({
        "type": "prompt",
        "messages": [
            {"role": "system", "content": "You are a calculator."},
            {"role": "user", "content": "What is 6 + 7?"}
        ]
    })
    print("✓ Recorded prompt event")

    store.write_event({
        "type": "model_response",
        "text": "The result is 13.",
        "tool_calls": []
    })
    print("✓ Recorded model response")

    # End trace
    store.end_trace(trace_id)
    print("✓ Ended trace")

    # Get summary
    summary = store.get_summary(trace_id)
    print(f"\nTrace Summary:")
    print(f"  - Agent: {summary['agent_name']}")
    print(f"  - Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"  - Total Events: {summary['total_events']}")
    print(f"  - Event Counts: {summary['event_counts']}")


def example_2_tasks_and_environments():
    """Example: Defining tasks and environments."""
    print("\n" + "="*60)
    print("Example 2: Tasks and Environments")
    print("="*60)

    # Define a task with assertions
    task = Task(
        prompt="Calculate the sum of 6 and 7",
        setup=["initialize_calculator"],
        assertions=[
            {"type": "contains", "expected": "13"},
            {"type": "regex", "pattern": r"\d+"},
        ]
    )
    print(f"✓ Created task: '{task.prompt}'")
    print(f"  - Assertions: {len(task.assertions)}")

    # Define an environment with AgentBay integration
    env = Environment(
        name="calculator_env",
        agentbay_env_id="codespace",
        agentbay_tool_set_id="command"
    )
    print(f"✓ Created environment: '{env.name}'")
    print(f"  - AgentBay Env: {env.agentbay_env_id}")
    print(f"  - Tool Set: {env.agentbay_tool_set_id}")


def example_3_assertions():
    """Example: Running assertions on agent output."""
    print("\n" + "="*60)
    print("Example 3: Running Assertions")
    print("="*60)

    # Simulate agent output
    agent_output = "The result of 6 + 7 is 13. This is a simple addition."

    # Define assertions
    assertions = [
        {"type": "contains", "expected": "13"},
        {"type": "contains", "expected": "result"},
        {"type": "regex", "pattern": r"\d+"},
        {"type": "starts_with", "expected": "The result"},
        {"type": "ends_with", "expected": "addition."},
    ]

    # Run assertions
    results = run_assertions(agent_output, assertions)

    print(f"Agent output: {agent_output}")
    print(f"\nAssertion Results:")
    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result["ok"] else "✗ FAIL"
        print(f"  {i}. {status} - {result['type']}")
        if not result["ok"]:
            print(f"     Message: {result['message']}")

    # Calculate pass rate
    pass_count = sum(1 for r in results if r["ok"])
    pass_rate = (pass_count / len(results)) * 100
    print(f"\nPass Rate: {pass_rate:.1f}% ({pass_count}/{len(results)})")


def example_4_agentbay_client():
    """Example: Using AgentBay client (requires API key)."""
    print("\n" + "="*60)
    print("Example 4: AgentBay Client")
    print("="*60)

    # Check if API key is available
    api_key = os.getenv("AGENTBAY_API_KEY")

    if not api_key:
        print("⚠ SKIPPED: No AGENTBAY_API_KEY found in environment")
        print("  To use AgentBay, set your API key:")
        print("  export AGENTBAY_API_KEY=your_api_key")
        print("  Get your key at: https://agentbay.console.aliyun.com/service-management")
        return

    try:
        from tigerhill.agentbay.client import AgentBayClient, EnvironmentType

        # Create client
        client = AgentBayClient()
        print("✓ AgentBay client initialized")

        # Create a session
        session = client.create_session(env_type=EnvironmentType.CODESPACE)
        print(f"✓ Created session: {session['session_id']}")
        print(f"  - Status: {session['status']}")
        print(f"  - Environment: {session['env_type']}")

        # Execute a command
        result = client.execute_command(
            session["session_id"],
            "echo 'Hello from TigerHill!'"
        )
        print(f"✓ Executed command")
        print(f"  - Output: {result['output']}")

        # Clean up
        client.delete_session(session["session_id"])
        print(f"✓ Cleaned up session")

    except ImportError:
        print("⚠ AgentBay SDK not installed")
        print("  Install it: pip install wuying-agentbay-sdk")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_5_query_traces():
    """Example: Querying stored traces."""
    print("\n" + "="*60)
    print("Example 5: Querying Traces")
    print("="*60)

    store = TraceStore(storage_path="./example_traces", auto_save=False)

    # Create multiple traces
    for i in range(3):
        trace_id = store.start_trace(
            agent_name=f"agent_{i % 2}",
            task_id=f"task_{i}"
        )
        store.write_event({"type": "prompt", "content": f"Test {i}"})
        store.end_trace(trace_id)

    print(f"✓ Created 3 test traces")

    # Query all traces
    all_traces = store.get_all_traces()
    print(f"\nTotal traces: {len(all_traces)}")

    # Query by agent name
    agent_0_traces = store.query_traces(agent_name="agent_0")
    print(f"Traces for 'agent_0': {len(agent_0_traces)}")

    agent_1_traces = store.query_traces(agent_name="agent_1")
    print(f"Traces for 'agent_1': {len(agent_1_traces)}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print(" TigerHill - AI Agent Evaluation Platform")
    print(" Basic Usage Examples")
    print("="*60)

    example_1_trace_store()
    example_2_tasks_and_environments()
    example_3_assertions()
    example_4_agentbay_client()
    example_5_query_traces()

    print("\n" + "="*60)
    print("✓ All examples completed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Set AGENTBAY_API_KEY to use AgentBay features")
    print("2. Check ./example_traces directory for saved traces")
    print("3. See tests/test_integration.py for more examples")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
