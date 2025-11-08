from typing import Any, Dict, List, Optional
from tigerhill.gateway.base import Message


class PromptBuilder:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def build(self, user_input: str, tools: Optional[List[Dict[str, Any]]] = None) -> List[Message]:
        tool_desc = ""
        if tools:
            names = [t.get("name", "tool") for t in tools]
            tool_names = [f"- {name}" for name in names]
            tool_desc = "\n\nTools available:\n" + "\n".join(tool_names)
        system_content = f"{self.system_prompt}{tool_desc}".strip()
        return [
            Message(role="system", content=system_content),
            Message(role="user", content=user_input),
        ]
