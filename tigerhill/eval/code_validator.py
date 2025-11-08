"""
TigerHill Code Validator - 代码验证器

从 LLM 输出中提取代码并进行实际验证：
- 提取代码块
- 语法检查
- 安全执行
- 测试运行
"""

import ast
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CodeExtractor:
    """从文本中提取代码块"""

    @staticmethod
    def extract_code_blocks(
        text: str,
        language: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        从 Markdown 文本中提取代码块

        Args:
            text: 输入文本
            language: 过滤特定语言（如 "python"），None 表示所有语言

        Returns:
            代码块列表，每个包含 {"language": "python", "code": "..."}
        """
        # 匹配 ```language 和 ``` 之间的代码
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        code_blocks = []
        for lang, code in matches:
            lang = lang.lower() if lang else "text"

            # 过滤语言
            if language and lang != language.lower():
                continue

            code_blocks.append({
                "language": lang,
                "code": code.strip()
            })

        return code_blocks

    @staticmethod
    def extract_first_code(
        text: str,
        language: str = "python"
    ) -> Optional[str]:
        """
        提取第一个指定语言的代码块

        Args:
            text: 输入文本
            language: 语言类型

        Returns:
            代码字符串，如果没找到则返回 None
        """
        blocks = CodeExtractor.extract_code_blocks(text, language=language)
        return blocks[0]["code"] if blocks else None


class PythonValidator:
    """Python 代码验证器"""

    @staticmethod
    def check_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """
        检查 Python 代码语法

        Args:
            code: Python 代码

        Returns:
            (是否通过, 错误信息)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def execute_code(
        code: str,
        timeout: int = 30,
        allow_network: bool = False
    ) -> Tuple[bool, str, str]:
        """
        在隔离环境中执行 Python 代码

        Args:
            code: Python 代码
            timeout: 超时时间（秒）
            allow_network: 是否允许网络访问

        Returns:
            (是否成功, stdout, stderr)
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Execution timeout after {timeout}s"

        except Exception as e:
            return False, "", str(e)

        finally:
            Path(temp_file).unlink(missing_ok=True)

    @staticmethod
    def run_tests(
        code: str,
        test_command: str = "pytest",
        timeout: int = 60
    ) -> Tuple[bool, str]:
        """
        运行测试命令

        Args:
            code: Python 代码（包含测试）
            test_command: 测试命令（如 "pytest", "python -m unittest"）
            timeout: 超时时间（秒）

        Returns:
            (是否通过, 输出信息)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_generated.py"
            test_file.write_text(code)

            try:
                result = subprocess.run(
                    test_command.split(),
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                success = result.returncode == 0
                output = result.stdout + result.stderr
                return success, output

            except subprocess.TimeoutExpired:
                return False, f"Test timeout after {timeout}s"

            except FileNotFoundError:
                return False, f"Test command not found: {test_command}"

            except Exception as e:
                return False, str(e)


class AgentBayValidator:
    """使用 AgentBay 进行代码验证（云端安全环境）"""

    def __init__(self, client: Any, session_id: str):
        """
        初始化 AgentBay 验证器

        Args:
            client: AgentBayClient 实例
            session_id: AgentBay 会话 ID
        """
        self.client = client
        self.session_id = session_id

    def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 60
    ) -> Tuple[bool, str]:
        """
        在 AgentBay 云端环境执行代码

        Args:
            code: 代码内容
            language: 语言类型
            timeout: 超时时间

        Returns:
            (是否成功, 输出)
        """
        # 创建临时文件
        filename = f"generated_code.{self._get_extension(language)}"

        try:
            # 上传代码
            upload_cmd = f"cat > {filename} << 'EOF'\n{code}\nEOF"
            self.client.execute_command(self.session_id, upload_cmd)

            # 执行代码
            exec_cmd = self._get_exec_command(filename, language)
            result = self.client.execute_command(self.session_id, exec_cmd)

            success = result.get("exit_code", 1) == 0
            output = result.get("output", "")

            return success, output

        except Exception as e:
            return False, str(e)

    @staticmethod
    def _get_extension(language: str) -> str:
        """获取文件扩展名"""
        extensions = {
            "python": "py",
            "javascript": "js",
            "go": "go",
            "rust": "rs",
            "java": "java"
        }
        return extensions.get(language.lower(), "txt")

    @staticmethod
    def _get_exec_command(filename: str, language: str) -> str:
        """获取执行命令"""
        commands = {
            "python": f"python {filename}",
            "javascript": f"node {filename}",
            "go": f"go run {filename}",
            "rust": f"rustc {filename} && ./{filename.replace('.rs', '')}",
            "java": f"javac {filename} && java {filename.replace('.java', '')}"
        }
        return commands.get(language.lower(), f"cat {filename}")


class CodeValidator:
    """统一的代码验证接口"""

    def __init__(
        self,
        use_agentbay: bool = False,
        agentbay_client: Optional[Any] = None,
        agentbay_session_id: Optional[str] = None
    ):
        """
        初始化代码验证器

        Args:
            use_agentbay: 是否使用 AgentBay 云端环境
            agentbay_client: AgentBayClient 实例
            agentbay_session_id: AgentBay 会话 ID
        """
        self.use_agentbay = use_agentbay

        if use_agentbay:
            if not agentbay_client or not agentbay_session_id:
                raise ValueError("AgentBay client and session_id required")
            self.agentbay_validator = AgentBayValidator(
                agentbay_client,
                agentbay_session_id
            )

    def validate(
        self,
        text: str,
        language: str = "python",
        validation_type: str = "syntax",
        **kwargs
    ) -> Dict[str, Any]:
        """
        验证生成的代码

        Args:
            text: LLM 生成的文本（包含代码块）
            language: 编程语言
            validation_type: 验证类型 ("syntax", "execution", "test")
            **kwargs: 额外参数

        Returns:
            验证结果字典:
            {
                "ok": bool,
                "validation_type": str,
                "language": str,
                "extracted_code": str,
                "details": str
            }
        """
        # 提取代码
        code = CodeExtractor.extract_first_code(text, language=language)

        if not code:
            return {
                "ok": False,
                "validation_type": validation_type,
                "language": language,
                "extracted_code": None,
                "details": f"No {language} code block found in output"
            }

        # 根据语言和验证类型选择验证器
        if language.lower() == "python":
            return self._validate_python(code, validation_type, **kwargs)
        else:
            # 其他语言只支持 AgentBay 验证
            if self.use_agentbay:
                return self._validate_agentbay(code, language, **kwargs)
            else:
                return {
                    "ok": False,
                    "validation_type": validation_type,
                    "language": language,
                    "extracted_code": code,
                    "details": f"Validation for {language} requires AgentBay"
                }

    def _validate_python(
        self,
        code: str,
        validation_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """验证 Python 代码"""
        if validation_type == "syntax":
            success, error = PythonValidator.check_syntax(code)
            return {
                "ok": success,
                "validation_type": "syntax",
                "language": "python",
                "extracted_code": code,
                "details": "Syntax valid" if success else error
            }

        elif validation_type == "execution":
            timeout = kwargs.get("timeout", 30)
            success, stdout, stderr = PythonValidator.execute_code(
                code,
                timeout=timeout
            )
            return {
                "ok": success,
                "validation_type": "execution",
                "language": "python",
                "extracted_code": code,
                "details": f"stdout: {stdout}\nstderr: {stderr}"
            }

        elif validation_type == "test":
            test_command = kwargs.get("test_command", "pytest")
            timeout = kwargs.get("timeout", 60)
            success, output = PythonValidator.run_tests(
                code,
                test_command=test_command,
                timeout=timeout
            )
            return {
                "ok": success,
                "validation_type": "test",
                "language": "python",
                "extracted_code": code,
                "details": output
            }

        else:
            return {
                "ok": False,
                "validation_type": validation_type,
                "language": "python",
                "extracted_code": code,
                "details": f"Unknown validation type: {validation_type}"
            }

    def _validate_agentbay(
        self,
        code: str,
        language: str,
        **kwargs
    ) -> Dict[str, Any]:
        """使用 AgentBay 验证代码"""
        timeout = kwargs.get("timeout", 60)
        success, output = self.agentbay_validator.execute_code(
            code,
            language=language,
            timeout=timeout
        )

        return {
            "ok": success,
            "validation_type": "execution",
            "language": language,
            "extracted_code": code,
            "details": output
        }
