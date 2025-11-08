import json
from typing import Any, Dict, Optional
from jsonschema import Draft202012Validator, ValidationError
from tigerhill.agentbay.client import AgentBayClient


class ToolSpec:
    def __init__(self, name: str, schema: Dict[str, Any]):
        self.name = name
        self.schema = schema
        self.validator = Draft202012Validator(schema)


class ToolShimMCP:
    def __init__(self, mode: str = "replay", agentbay_client: Optional[AgentBayClient] = None):
        self.mode = mode
        self._tools: Dict[str, ToolSpec] = {}
        self._replay: Dict[str, Any] = {}
        self.agentbay_client = agentbay_client

    def register_tool(self, name: str, schema: Dict[str, Any]):
        self._tools[name] = ToolSpec(name, schema)

    def load_replay(self, mapping: Dict[str, Any]):
        self._replay = dict(mapping)

    def validate_args(self, name: str, args: Dict[str, Any]) -> Optional[str]:
        spec = self._tools.get(name)
        if not spec:
            return f"tool '{name}' not registered"
        try:
            spec.validator.validate(args)
            return None
        except ValidationError as e:
            return f"schema violation: {e.message}"

    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        err = self.validate_args(name, args)
        if err:
            return {"error": err}

        if self.mode == "replay":
            key = f"{name}:{str(args)}"
            result = self._replay.get(key)
            if result is None:
                alt_key = f"{name}:{json.dumps(args, ensure_ascii=False, sort_keys=True)}"
                result = self._replay.get(alt_key)
                key = alt_key
            if result is None:
                result = f"(no replay) {key}"
            return {"result": result}
        elif self.mode == "agentbay_live":
            if not self.agentbay_client:
                return {"error": "AgentBay client not provided for agentbay_live mode"}
            # Assuming AgentBayClient has an execute_tool method that takes tool_name and tool_args
            try:
                # In a real scenario, we might need to pass an env_id here if the tool execution is environment-specific
                # For now, we'll assume the client handles the context or it's not strictly required for direct tool execution
                return self.agentbay_client.execute_tool(tool_name=name, tool_args=args)
            except Exception as e:
                return {"error": f"AgentBay tool execution failed: {e}"}

        return {"error": f"Unsupported mode: {self.mode}"}
