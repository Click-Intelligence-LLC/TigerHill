from typing import Any, Dict, List, Optional
from tigerhill.core.models import Agent, AgentOutput, Task, Environment
from tigerhill.gateway.base import LLMClient, Message, ModelResponse
from tigerhill.tools.mcp_shim import ToolShimMCP
from tigerhill.storage.trace_store import TraceStore
from tigerhill.otel.telemetry import get_tracer
from tigerhill.agentbay.client import AgentBayClient
from .registry import agent_registry
from .prompt_builder import PromptBuilder


class DynamicAgent(Agent):
    name: str = "dynamic_agent"

    def __init__(self, client: LLMClient, tools: Optional[ToolShimMCP] = None, store: Optional[TraceStore] = None, agentbay_client: Optional[AgentBayClient] = None, system_prompt: str = "You are a helpful assistant."):
        super().__init__(name=self.name)
        self.client = client
        self.agentbay_client = agentbay_client
        self.system_prompt = system_prompt
        # If tools are not provided, initialize ToolShimMCP, potentially with AgentBayClient
        if tools is None:
            self.tools = ToolShimMCP(mode="agentbay_live" if agentbay_client else "replay", agentbay_client=agentbay_client)
        else:
            self.tools = tools
        self.store = store or TraceStore()
        self.tracer = get_tracer("dynamic_agent")

    def run(self, task: Task, env: Environment) -> AgentOutput:
        with self.tracer.start_as_current_span("agent.run"):
            # Handle AgentBay environment and tools if client is available
            agentbay_tools_list = []
            if self.agentbay_client:
                if env.agentbay_env_id:
                    print(f"DEBUG: Requesting AgentBay environment: {env.agentbay_env_id}")
                    # In a real scenario, we might need to handle the provisioning status
                    env_details = self.agentbay_client.request_environment(env.agentbay_env_id)
                    print(f"DEBUG: AgentBay environment details: {env_details}")

                if env.agentbay_tool_set_id:
                    print(f"DEBUG: Loading AgentBay tool set: {env.agentbay_tool_set_id}")
                    agentbay_tools_list = self.agentbay_client.load_tools(env.agentbay_tool_set_id)
                    print(f"DEBUG: Loaded AgentBay tools: {agentbay_tools_list}")
                    if self.tools:
                        for t in agentbay_tools_list:
                            # Assuming AgentBay tools come with 'name' and 'schema'
                            # We need to ensure 'schema' is present in the tool definition from AgentBay
                            if "name" in t and "schema" in t:
                                self.tools.register_tool(t["name"], t["schema"])
                            else:
                                print(f"WARNING: AgentBay tool {t} is missing 'name' or 'schema' and cannot be registered.")

            # For now, we'll assume a simple system prompt. This could be part of the Task or Agent config.
            pb = PromptBuilder(self.system_prompt)
            # Pass the tools obtained from AgentBay (if any) to the prompt builder
            messages = pb.build(task.prompt, agentbay_tools_list)

            self.store.write_event({"type": "prompt", "messages": [m.model_dump() for m in messages]})

            mr: ModelResponse = self.client.chat(messages)
            self.store.write_event({"type": "model_response", "text": mr.text, "tool_calls": [tc.model_dump() for tc in mr.tool_calls]})

            # Execute tool calls
            tool_results: List[Dict[str, Any]] = []
            if self.tools and mr.tool_calls:
                for tc in mr.tool_calls:
                    res = self.tools.call(tc.name, tc.arguments)
                    tool_results.append({"tool": tc.name, "args": tc.arguments, "result": res})
                    self.store.write_event({"type": "tool_result", "tool": tc.name, "args": tc.arguments, "result": res})

            return AgentOutput(text=mr.text, tool_calls=tool_results)


agent_registry.register(DynamicAgent)
