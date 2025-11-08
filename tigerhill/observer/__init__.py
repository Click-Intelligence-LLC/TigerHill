"""
TigerHill Observer SDK - Debug Mode Support

提供 LLM SDK 的无侵入式 instrumentation，捕获 prompt、response 和工具调用。

支持：
- Google Generative AI (Node.js/Python)
- OpenAI API (Python)
- 自定义扩展

主要功能：
- Prompt 捕获
- Response 记录
- 工具调用追踪
- 自动分析
"""

from tigerhill.observer.capture import PromptCapture
from tigerhill.observer.analyzer import PromptAnalyzer
from tigerhill.observer.python_observer import wrap_generative_model as wrap_python_model

__all__ = [
    "PromptCapture",
    "PromptAnalyzer",
    "wrap_python_model",
]

__version__ = "0.0.3"
