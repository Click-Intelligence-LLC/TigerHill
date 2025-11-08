"""
Multi-Language Agent Adapters

通用 Agent 适配器框架，支持测试任何语言编写的 Agent。
"""

import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from tigerhill.storage.trace_store import EventType


class AgentAdapter(ABC):
    """
    Agent 适配器基类

    所有 Agent 适配器的抽象基类，定义统一的调用接口。
    """

    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用 Agent 并获取响应

        Args:
            prompt: 输入提示
            **kwargs: 额外参数

        Returns:
            Agent 的响应文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        pass

    def cleanup(self):
        """
        清理资源

        释放 Agent 占用的资源（可选实现）。
        """
        pass

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


class HTTPAgentAdapter(AgentAdapter):
    """
    HTTP/REST API Agent 适配器

    适用于提供 HTTP 接口的 Agent（Node.js、Python Flask/FastAPI、Go HTTP 等）。

    Example:
        >>> adapter = HTTPAgentAdapter("http://localhost:3000", endpoint="/api/agent")
        >>> response = adapter.invoke("计算 1+1")
        >>> print(response)
    """

    def __init__(
        self,
        base_url: str,
        endpoint: str = "/api/agent",
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        初始化 HTTP Agent 适配器

        Args:
            base_url: Agent 服务的基础 URL
            endpoint: API 端点路径
            method: HTTP 方法（GET/POST）
            headers: 自定义 HTTP 头
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.method = method.upper()
        self.headers = headers or {}
        self.timeout = timeout

        logger.info(f"Initialized HTTP adapter: {self.base_url}{self.endpoint}")

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        通过 HTTP 调用 Agent

        Args:
            prompt: 输入提示
            **kwargs: 额外的请求参数

        Returns:
            Agent 响应文本
        """
        try:
            import requests
        except ImportError:
            raise ImportError("需要安装 requests 库: pip install requests")

        url = f"{self.base_url}{self.endpoint}"
        payload = {"prompt": prompt, **kwargs}

        logger.debug(f"HTTP {self.method} {url}")
        logger.debug(f"Payload: {payload}")

        try:
            if self.method == "POST":
                response = requests.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
            elif self.method == "GET":
                response = requests.get(
                    url,
                    params=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"不支持的 HTTP 方法: {self.method}")

            response.raise_for_status()

            data = response.json()

            # 尝试从多种可能的响应格式中提取输出
            if isinstance(data, str):
                return data
            elif "output" in data:
                return data["output"]
            elif "response" in data:
                return data["response"]
            elif "result" in data:
                return data["result"]
            else:
                return json.dumps(data)

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 请求失败: {e}")
            raise


class CLIAgentAdapter(AgentAdapter):
    """
    命令行 Agent 适配器

    适用于命令行工具形式的 Agent（Go、Rust、C++ 等编译型语言）。

    Example:
        >>> adapter = CLIAgentAdapter("./my_agent")
        >>> response = adapter.invoke("分析代码")
        >>> print(response)
    """

    def __init__(
        self,
        command: str,
        args_template: Optional[List[str]] = None,
        timeout: int = 30,
        encoding: str = "utf-8"
    ):
        """
        初始化 CLI Agent 适配器

        Args:
            command: Agent 可执行文件路径或命令
            args_template: 参数模板，{prompt} 会被替换为实际提示
            timeout: 执行超时时间（秒）
            encoding: 输出编码
        """
        self.command = command
        self.args_template = args_template or ["{prompt}"]
        self.timeout = timeout
        self.encoding = encoding

        logger.info(f"Initialized CLI adapter: {self.command}")

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        通过命令行调用 Agent

        Args:
            prompt: 输入提示
            **kwargs: 额外参数（可在 args_template 中使用）

        Returns:
            Agent 响应文本
        """
        # 构建命令参数
        args = [
            arg.format(prompt=prompt, **kwargs)
            for arg in self.args_template
        ]

        cmd = [self.command] + args
        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding=self.encoding
            )

            if result.returncode != 0:
                error_msg = f"命令执行失败 (exit code {result.returncode}): {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            output = result.stdout.strip()
            logger.debug(f"Output: {output[:200]}...")

            # 尝试解析 JSON 输出
            try:
                data = json.loads(output)
                if isinstance(data, dict) and "output" in data:
                    return data["output"]
            except json.JSONDecodeError:
                pass

            return output

        except subprocess.TimeoutExpired:
            error_msg = f"命令执行超时 ({self.timeout}秒)"
            logger.error(error_msg)
            raise TimeoutError(error_msg)
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            raise


class STDIOAgentAdapter(AgentAdapter):
    """
    标准输入/输出 Agent 适配器

    适用于通过 STDIN/STDOUT 交互的 Agent，支持长期运行的进程。

    Example:
        >>> adapter = STDIOAgentAdapter("java -jar agent.jar")
        >>> response = adapter.invoke("问题1")
        >>> response = adapter.invoke("问题2")  # 复用同一进程
        >>> adapter.cleanup()
    """

    def __init__(
        self,
        command: str,
        end_marker: str = "\n",
        init_timeout: int = 10,
        response_timeout: int = 30,
        encoding: str = "utf-8"
    ):
        """
        初始化 STDIO Agent 适配器

        Args:
            command: 启动 Agent 的命令
            end_marker: 响应结束标记
            init_timeout: 初始化超时时间（秒）
            response_timeout: 响应超时时间（秒）
            encoding: 编码格式
        """
        self.command = command
        self.end_marker = end_marker
        self.init_timeout = init_timeout
        self.response_timeout = response_timeout
        self.encoding = encoding
        self.process: Optional[subprocess.Popen] = None

        logger.info(f"Initialized STDIO adapter: {self.command}")

    def _ensure_process(self):
        """确保进程已启动"""
        if self.process is None or self.process.poll() is not None:
            logger.debug("Starting agent process...")
            self.process = subprocess.Popen(
                self.command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding=self.encoding
            )
            time.sleep(0.5)  # 等待进程启动

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        通过 STDIO 调用 Agent

        Args:
            prompt: 输入提示
            **kwargs: 额外参数（会以 JSON 格式发送）

        Returns:
            Agent 响应文本
        """
        self._ensure_process()

        if not self.process:
            raise RuntimeError("无法启动 Agent 进程")

        # 发送提示
        try:
            if kwargs:
                data = {"prompt": prompt, **kwargs}
                input_str = json.dumps(data, ensure_ascii=False) + self.end_marker
            else:
                input_str = prompt + self.end_marker

            logger.debug(f"Sending: {input_str[:200]}...")
            self.process.stdin.write(input_str)
            self.process.stdin.flush()

            # 读取响应
            output_lines = []
            start_time = time.time()

            while True:
                if time.time() - start_time > self.response_timeout:
                    raise TimeoutError(f"响应超时 ({self.response_timeout}秒)")

                line = self.process.stdout.readline()
                if not line:
                    break

                output_lines.append(line.rstrip('\n'))

                # 检查是否是完整响应
                if line.endswith('\n'):
                    break

            output = '\n'.join(output_lines)
            logger.debug(f"Received: {output[:200]}...")

            return output

        except Exception as e:
            logger.error(f"STDIO 通信失败: {e}")
            self.cleanup()
            raise

    def cleanup(self):
        """终止 Agent 进程"""
        if self.process:
            logger.debug("Terminating agent process...")
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"进程清理警告: {e}")
                self.process.kill()
            finally:
                self.process = None


class AgentBayAdapter(AgentAdapter):
    """
    AgentBay 云环境 Agent 适配器

    适用于需要在 AgentBay 云环境中运行的 Agent，支持任何语言。

    Example:
        >>> from tigerhill.agentbay.client import AgentBayClient
        >>> client = AgentBayClient()
        >>> session = client.create_session()
        >>> adapter = AgentBayAdapter(client, session["session_id"], "./agent")
        >>> response = adapter.invoke("测试")
        >>> adapter.cleanup()
    """

    def __init__(
        self,
        client: Any,  # AgentBayClient
        session_id: str,
        agent_command: str,
        setup_commands: Optional[List[str]] = None
    ):
        """
        初始化 AgentBay Agent 适配器

        Args:
            client: AgentBayClient 实例
            session_id: AgentBay 会话 ID
            agent_command: Agent 执行命令模板（{prompt} 会被替换）
            setup_commands: 环境准备命令列表
        """
        self.client = client
        self.session_id = session_id
        self.agent_command = agent_command
        self.setup_commands = setup_commands or []
        self._initialized = False

        logger.info(f"Initialized AgentBay adapter: session={session_id}")

    def _setup_environment(self):
        """准备云环境"""
        if self._initialized:
            return

        logger.debug("Setting up AgentBay environment...")
        for cmd in self.setup_commands:
            logger.debug(f"Setup: {cmd}")
            result = self.client.execute_command(self.session_id, cmd)
            if result.get("exit_code", 0) != 0:
                raise RuntimeError(f"环境准备失败: {result.get('output', '')}")

        self._initialized = True

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        在 AgentBay 云环境中调用 Agent

        Args:
            prompt: 输入提示
            **kwargs: 额外参数

        Returns:
            Agent 响应文本
        """
        self._setup_environment()

        # 构建命令
        command = self.agent_command.format(prompt=prompt, **kwargs)
        logger.debug(f"AgentBay executing: {command}")

        try:
            result = self.client.execute_command(self.session_id, command)

            if result.get("exit_code", 0) != 0:
                error_msg = f"Agent 执行失败: {result.get('output', '')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            output = result.get("output", "").strip()
            logger.debug(f"AgentBay output: {output[:200]}...")

            return output

        except Exception as e:
            logger.error(f"AgentBay 执行失败: {e}")
            raise

    def cleanup(self):
        """清理 AgentBay 会话"""
        try:
            logger.debug(f"Cleaning up AgentBay session: {self.session_id}")
            self.client.delete_session(self.session_id)
        except Exception as e:
            logger.warning(f"会话清理警告: {e}")


class UniversalAgentTester:
    """
    通用 Agent 测试器

    提供统一的测试接口，可测试任何语言、任何协议的 Agent。

    Example:
        >>> from tigerhill.adapters import UniversalAgentTester, HTTPAgentAdapter
        >>> from tigerhill.storage.trace_store import TraceStore
        >>>
        >>> store = TraceStore()
        >>> adapter = HTTPAgentAdapter("http://localhost:3000")
        >>> tester = UniversalAgentTester(adapter, store)
        >>>
        >>> result = tester.test(
        ...     task={"prompt": "计算 1+1", "assertions": [{"type": "contains", "expected": "2"}]},
        ...     agent_name="nodejs_agent"
        ... )
        >>> print(f"通过: {result['passed']}/{result['total']}")
    """

    def __init__(self, adapter: AgentAdapter, store: Any):
        """
        初始化通用测试器

        Args:
            adapter: Agent 适配器实例
            store: TraceStore 实例
        """
        self.adapter = adapter
        self.store = store

        logger.info(f"Initialized UniversalAgentTester with {type(adapter).__name__}")

    def test(
        self,
        task: Dict[str, Any],
        agent_name: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行单个测试

        Args:
            task: 测试任务字典，包含 'prompt' 和可选的 'assertions'
            agent_name: Agent 名称
            task_id: 任务 ID（可选）
            metadata: 额外元数据（可选）

        Returns:
            测试结果字典，包含:
                - trace_id: 追踪 ID
                - output: Agent 输出
                - passed: 通过的断言数
                - total: 总断言数
                - results: 详细断言结果
                - duration: 执行时长（秒）
        """
        from tigerhill.eval.assertions import run_assertions

        prompt = task.get("prompt", "")
        assertions = task.get("assertions", [])

        if not prompt:
            raise ValueError("task 必须包含 'prompt' 字段")

        # 开始追踪
        metadata = metadata or task.get("trace_metadata")

        trace_id = self.store.start_trace(
            agent_name=agent_name,
            task_id=task_id,
            metadata=metadata
        )

        start_time = time.time()

        try:
            # 记录提示
            prompt_event = {
                "type": "prompt",
                "content": prompt
            }
            messages = task.get("messages")
            if messages:
                prompt_event["messages"] = messages

            self.store.write_event(
                prompt_event,
                event_type=EventType.PROMPT
            )

            # 调用 Agent
            logger.info(f"Testing {agent_name}: {prompt[:50]}...")
            output = self.adapter.invoke(prompt)

            # 记录响应
            self.store.write_event(
                {
                    "type": "model_response",
                    "text": output,
                    "adapter_type": type(self.adapter).__name__
                },
                event_type=EventType.MODEL_RESPONSE
            )

            # 评估断言
            results = run_assertions(output, assertions) if assertions else []
            passed = sum(1 for r in results if r.get("ok", False))

            duration = time.time() - start_time

            # 记录评估结果
            self.store.write_event(
                {
                    "type": "evaluation",
                    "passed": passed,
                    "total": len(results),
                    "duration_seconds": duration,
                    "assertions": results,
                },
                event_type=EventType.CUSTOM
            )

            logger.info(f"Test completed: {passed}/{len(results)} passed in {duration:.2f}s")

            return {
                "trace_id": trace_id,
                "output": output,
                "passed": passed,
                "total": len(results),
                "results": results,
                "duration": duration,
                "success": True
            }

        except Exception as e:
            duration = time.time() - start_time

            logger.error(f"Test failed: {e}")

            # 记录错误
            self.store.write_event(
                {
                    "type": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                event_type=EventType.ERROR
            )

            return {
                "trace_id": trace_id,
                "output": None,
                "passed": 0,
                "total": len(assertions),
                "results": [],
                "duration": duration,
                "success": False,
                "error": str(e)
            }

        finally:
            self.store.end_trace(trace_id)

    def test_batch(
        self,
        tasks: List[Dict[str, Any]],
        agent_name: str,
        cleanup_between_tests: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量测试多个任务

        Args:
            tasks: 任务列表
            agent_name: Agent 名称
            cleanup_between_tests: 是否在测试间清理 adapter

        Returns:
            测试结果列表
        """
        results = []

        for i, task in enumerate(tasks, 1):
            logger.info(f"Running test {i}/{len(tasks)}")

            result = self.test(
                task=task,
                agent_name=agent_name,
                task_id=f"batch_{i}"
            )

            results.append(result)

            if cleanup_between_tests:
                self.adapter.cleanup()

        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成测试报告

        Args:
            results: 测试结果列表

        Returns:
            汇总报告
        """
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success", False))
        total_passed = sum(r.get("passed", 0) for r in results)
        total_assertions = sum(r.get("total", 0) for r in results)
        total_duration = sum(r.get("duration", 0) for r in results)

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
            "total_assertions": total_assertions,
            "passed_assertions": total_passed,
            "assertion_pass_rate": total_passed / total_assertions * 100 if total_assertions > 0 else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / total_tests if total_tests > 0 else 0
        }
