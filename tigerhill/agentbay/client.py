"""
AgentBay Client module for interacting with the AgentBay platform.

This module wraps the official wuying-agentbay-sdk and provides
a TigerHill-specific interface for managing AgentBay sessions,
environments, and tool execution.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EnvironmentType(str, Enum):
    """Supported AgentBay environment types."""
    BROWSER = "browser"
    COMPUTER = "computer"
    MOBILE = "mobile"
    CODESPACE = "codespace"


class SessionStatus(str, Enum):
    """AgentBay session status."""
    CREATING = "creating"
    ACTIVE = "active"
    TERMINATED = "terminated"
    ERROR = "error"


class AgentBayClient:
    """
    Client for interacting with the AgentBay platform.

    This client wraps the official wuying-agentbay-sdk and provides
    session management, environment provisioning, and tool execution
    capabilities for TigerHill's evaluation workflows.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the AgentBayClient.

        Args:
            api_key: The API key for AgentBay. If not provided, it will try to
                    read from AGENTBAY_API_KEY environment variable.

        Raises:
            ValueError: If no API key is provided or found in environment.
            ImportError: If wuying-agentbay-sdk is not installed.
        """
        self.api_key = api_key or os.getenv("AGENTBAY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "AgentBay API key is not provided. Please set it via constructor "
                "or AGENTBAY_API_KEY environment variable. "
                "Get your API key at: https://agentbay.console.aliyun.com/service-management"
            )

        # Set environment variable for SDK
        os.environ["AGENTBAY_API_KEY"] = self.api_key

        # Import and initialize SDK
        try:
            from agentbay import AgentBay
            self._sdk = AgentBay()
            self._sessions: Dict[str, Any] = {}  # session_id -> session object
            logger.info("AgentBay SDK initialized successfully")
        except ImportError as e:
            raise ImportError(
                "Failed to import wuying-agentbay-sdk. "
                "Please install it: pip install wuying-agentbay-sdk"
            ) from e

    def create_session(
        self,
        env_type: Optional[EnvironmentType] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new AgentBay session with specified environment.

        Args:
            env_type: Type of environment (browser, computer, mobile, codespace).
            config: Optional configuration for the environment.

        Returns:
            A dictionary containing session details:
            {
                "session_id": str,
                "session": object,  # Internal session object
                "status": str,
                "env_type": str,
                "created_at": str
            }

        Raises:
            RuntimeError: If session creation fails.
        """
        try:
            logger.info(f"Creating AgentBay session with env_type={env_type}, config={config}")

            # Create session using SDK
            session_result = self._sdk.create()
            session = session_result.session
            session_id = id(session)  # Use object id as session identifier

            # Store session
            self._sessions[str(session_id)] = {
                "session": session,
                "env_type": env_type,
                "config": config,
                "status": SessionStatus.ACTIVE
            }

            logger.info(f"Session created successfully: {session_id}")

            return {
                "session_id": str(session_id),
                "session": session,
                "status": SessionStatus.ACTIVE,
                "env_type": env_type.value if env_type else "default",
                "created_at": "now"  # TODO: Add actual timestamp
            }

        except Exception as e:
            logger.error(f"Failed to create AgentBay session: {e}")
            raise RuntimeError(f"Session creation failed: {e}") from e

    def delete_session(self, session_id: str) -> bool:
        """
        Deletes an AgentBay session and cleans up resources.

        Args:
            session_id: The ID of the session to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return False

            session_data = self._sessions[session_id]
            session = session_data["session"]

            logger.info(f"Deleting session {session_id}")
            self._sdk.delete(session)

            # Update status and remove from cache
            session_data["status"] = SessionStatus.TERMINATED
            del self._sessions[session_id]

            logger.info(f"Session {session_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a command in an AgentBay session.

        Args:
            session_id: The ID of the session.
            command: The command to execute.
            timeout: Optional timeout in seconds.

        Returns:
            A dictionary containing command execution result:
            {
                "output": str,
                "exit_code": int,
                "error": Optional[str]
            }

        Raises:
            ValueError: If session not found.
            RuntimeError: If command execution fails.
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        try:
            session_data = self._sessions[session_id]
            session = session_data["session"]

            logger.info(f"Executing command in session {session_id}: {command}")

            result = session.command.execute_command(command)

            return {
                "output": result.output if hasattr(result, 'output') else str(result),
                "exit_code": getattr(result, 'exit_code', 0),
                "error": getattr(result, 'error', None)
            }

        except Exception as e:
            logger.error(f"Command execution failed in session {session_id}: {e}")
            raise RuntimeError(f"Command execution failed: {e}") from e

    def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a specific tool within an AgentBay environment.

        This method maps TigerHill tool calls to AgentBay SDK operations.

        Args:
            tool_name: The name of the tool to execute.
            tool_args: The arguments for the tool.
            session_id: Optional session ID. If not provided, creates a temporary session.

        Returns:
            A dictionary containing the tool execution result.

        Raises:
            ValueError: If tool_name is not supported.
        """
        # Determine if we need to create a temporary session
        temp_session = False
        if session_id is None:
            logger.info("No session provided, creating temporary session for tool execution")
            session_result = self.create_session()
            session_id = session_result["session_id"]
            temp_session = True

        try:
            # Map tool names to AgentBay operations
            if tool_name in ["command", "terminal", "bash", "shell"]:
                # Execute as shell command
                cmd = tool_args.get("command") or tool_args.get("cmd")
                if not cmd:
                    raise ValueError(f"Missing 'command' argument for tool {tool_name}")

                result = self.execute_command(session_id, cmd)
                return {"tool_name": tool_name, "result": result["output"]}

            elif tool_name in ["file", "file_read", "file_write"]:
                # File operations
                logger.warning(f"File tool '{tool_name}' not yet fully implemented")
                return {
                    "tool_name": tool_name,
                    "result": f"File operation {tool_name} with args {tool_args}"
                }

            else:
                raise ValueError(f"Unsupported tool: {tool_name}")

        finally:
            # Clean up temporary session
            if temp_session:
                self.delete_session(session_id)

    def request_environment(
        self,
        env_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Requests an environment from AgentBay.

        This is a compatibility method that creates a session with specific environment type.

        Args:
            env_id: The type of environment (browser/computer/mobile/codespace).
            config: Optional configuration for the environment.

        Returns:
            A dictionary containing environment details.
        """
        try:
            env_type = EnvironmentType(env_id.lower())
        except ValueError:
            logger.warning(f"Unknown environment type: {env_id}, using default")
            env_type = None

        return self.create_session(env_type=env_type, config=config)

    def load_tools(self, tool_set_id: str) -> List[Dict[str, Any]]:
        """
        Loads a set of tools from AgentBay.

        Returns the available tools for the specified tool set.

        Args:
            tool_set_id: The ID of the tool set to load.

        Returns:
            A list of dictionaries, each representing a tool with name and schema.
        """
        # Standard AgentBay tools
        standard_tools = {
            "browser": [
                {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL in the browser",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"}
                        },
                        "required": ["url"]
                    }
                }
            ],
            "command": [
                {
                    "name": "execute_command",
                    "description": "Execute a shell command",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        },
                        "required": ["command"]
                    }
                }
            ],
            "file": [
                {
                    "name": "file_read",
                    "description": "Read a file",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                }
            ]
        }

        return standard_tools.get(tool_set_id, [])

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Gets the status of an AgentBay session.

        Args:
            session_id: The ID of the session.

        Returns:
            A dictionary containing session status information.
        """
        if session_id not in self._sessions:
            return {"session_id": session_id, "status": SessionStatus.ERROR, "error": "Session not found"}

        session_data = self._sessions[session_id]
        return {
            "session_id": session_id,
            "status": session_data["status"],
            "env_type": session_data.get("env_type"),
            "config": session_data.get("config")
        }

    def cleanup_all_sessions(self) -> int:
        """
        Cleans up all active sessions.

        Returns:
            Number of sessions successfully cleaned up.
        """
        session_ids = list(self._sessions.keys())
        cleaned = 0

        for session_id in session_ids:
            if self.delete_session(session_id):
                cleaned += 1

        logger.info(f"Cleaned up {cleaned}/{len(session_ids)} sessions")
        return cleaned

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all sessions."""
        self.cleanup_all_sessions()
        return False