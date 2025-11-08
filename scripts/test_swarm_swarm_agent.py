#!/usr/bin/env python3
"""
Run the OpenAI Swarm demo under TigerHill prompt capture.

This script monkey-patches the Swarm client's Chat Completions calls so that
every request/response is recorded via PromptCapture. It is intended for
manual smoke tests, not production instrumentation.
"""

from __future__ import annotations

import os
import sys
import json
from typing import Any, Dict, List

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tigerhill.observer.capture import PromptCapture


def _build_request_record(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI chat.create params into a capture-friendly payload."""
    messages: List[Dict[str, Any]] = params.get("messages", [])
    system_messages = [m["content"] for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    record: Dict[str, Any] = {
        "model": params.get("model"),
        "messages": messages,
        "prompt": non_system_messages,
        "system_prompt": "\n\n".join(system_messages),
        "tools": params.get("tools"),
        "tool_choice": params.get("tool_choice"),
        "parallel_tool_calls": params.get("parallel_tool_calls"),
        "stream": params.get("stream", False),
    }

    # keep raw params for debugging
    record["raw_request"] = params
    return record


def _build_response_record(response: Any) -> Dict[str, Any]:
    """Extract high-level data from an OpenAI ChatCompletion."""
    response_data: Dict[str, Any] = {}

    try:
        first_choice = response.choices[0]
    except (AttributeError, IndexError, KeyError):
        first_choice = None

    if first_choice is not None:
        message = getattr(first_choice, "message", None)
        if message is not None:
            response_data["text"] = getattr(message, "content", "") or ""
            if getattr(message, "tool_calls", None):
                response_data["tool_calls"] = [
                    {
                        "id": getattr(tool_call, "id", None),
                        "type": getattr(tool_call, "type", None),
                        "function": {
                            "name": getattr(getattr(tool_call, "function", None), "name", None),
                            "arguments": getattr(
                                getattr(tool_call, "function", None), "arguments", None
                            ),
                        },
                    }
                    for tool_call in message.tool_calls
                ]
        response_data["finish_reason"] = getattr(first_choice, "finish_reason", None)

    usage = getattr(response, "usage", None)
    if usage is not None:
        # usage is a pydantic model in the OpenAI SDK
        if hasattr(usage, "model_dump"):
            response_data["usage"] = usage.model_dump()
        else:
            response_data["usage"] = dict(usage)

    # keep raw response for debugging
    if hasattr(response, "model_dump"):
        response_data["raw_response"] = response.model_dump()
    else:
        response_data["raw_response"] = response

    if not response_data.get("text"):
        response_data["text"] = ""

    return response_data


def main() -> None:
    try:
        from swarm import Swarm, Agent
        from swarm.types import Result
    except ImportError as exc:
        raise SystemExit(
            "Failed to import Swarm. Activate the swarm virtual environment before running this script."
        ) from exc

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Export it before running the Swarm demo.")

    default_capture_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "prompt_captures", "swarm_agent")
    )
    capture_path = os.environ.get("TIGERHILL_CAPTURE_PATH", default_capture_path)

    capture = PromptCapture(storage_path=capture_path, auto_save=True)
    capture_id = capture.start_capture("swarm_agent")

    client = Swarm()

    original_create = client.client.chat.completions.create

    def wrapped_create(*args: Any, **kwargs: Any):
        params = kwargs.copy()
        request_record = _build_request_record(params)
        capture.capture_request(capture_id, request_record)

        response = original_create(*args, **kwargs)

        response_record = _build_response_record(response)
        capture.capture_response(capture_id, response_record)

        return response

    client.client.chat.completions.create = wrapped_create  # type: ignore[assignment]

    def transfer_to_agent_b():
        return agent_b

    agent_a = Agent(
        name="Agent A",
        instructions="You are a helpful agent that always greets the user before routing.",
        functions=[transfer_to_agent_b],
    )

    agent_b = Agent(
        name="Agent B",
        instructions="You are a poetic assistant. Reply in haiku form.",
    )

    def lookup_order(order_id: str, issue: str, context_variables: Dict[str, Any] | None = None):
        """Mock tool returning structured order info."""
        ctx = context_variables or {}
        payload = {
            "order_id": order_id,
            "customer": ctx.get("customer_name", "customer"),
            "issue": issue,
            "status": "delivered - damage reported",
        }
        return Result(
            value=json.dumps(payload, ensure_ascii=False),
            context_variables={"order_status": payload["status"]},
        )

    def authorize_refund(
        order_id: str,
        amount: float,
        justification: str,
        context_variables: Dict[str, Any] | None = None,
    ):
        """Approve refund and attach note."""
        ctx = context_variables or {}
        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            # fall back to parsing numeric characters
            try:
                amount_value = float(str(amount).strip("$"))
            except ValueError:
                amount_value = 0.0
        note = (
            f"Approved refund of ${amount_value:.2f} for order {order_id}. "
            f"Reason: {justification}. Contact: {ctx.get('customer_name', 'customer')}"
        )
        return Result(
            value=json.dumps({"approved": True, "note": note}, ensure_ascii=False),
            context_variables={"refund_note": note},
        )

    support_agent = Agent(
        name="Support Agent",
        instructions=(
            "You are a senior customer support agent. "
            "Always acknowledge the customer by name using the `customer_name` context variable. "
            "You must call the `lookup_order` tool exactly once with the order id and the issue text "
            "before responding. After you receive the tool output, call `authorize_refund` exactly once "
            "to approve the refund. Finally, summarize the actions you took, reference the order status "
            "and refund note, and reassure the customer."
        ),
        functions=[lookup_order, authorize_refund],
    )

    try:
        response = client.run(
            agent=agent_a,
            messages=[{"role": "user", "content": "Please hand me over to your poetic friend."}],
        )
    except Exception as exc:
        capture.end_capture(capture_id)
        raise SystemExit(f"Swarm run failed: {exc}") from exc

    final_payload = {
        "messages": response.messages,
        "context_variables": getattr(response, "context_variables", {}),
    }
    capture.capture_response(
        capture_id,
        {
            "text": response.messages[-1]["content"] or "",
            "raw_response": final_payload,
        },
    )

    print("\nConversation transcript (handoff demo):")
    for message in response.messages:
        role = message.get("role")
        content = message.get("content")
        print(f"{role:>10}: {content}")

    try:
        complex_response = client.run(
            agent=support_agent,
            messages=[
                {
                    "role": "user",
                    "content": "Order A123 arrived with a cracked screen. I paid 249.99 and need a refund.",
                }
            ],
            context_variables={"customer_name": "Alice Chen"},
        )
    except Exception as exc:
        capture.end_capture(capture_id)
        raise SystemExit(f"Complex Swarm run failed: {exc}") from exc

    complex_payload = {
        "messages": complex_response.messages,
        "context_variables": getattr(complex_response, "context_variables", {}),
    }
    capture.capture_response(
        capture_id,
        {
            "text": complex_response.messages[-1]["content"] or "",
            "raw_response": complex_payload,
        },
    )

    capture.end_capture(capture_id)

    print("\nConversation transcript (support workflow):")
    for message in complex_response.messages:
        role = message.get("role")
        content = message.get("content")
        print(f"{role:>10}: {content}")


if __name__ == "__main__":
    main()
