"""
TigerHill Code Validation Example - 代码验证示例

展示如何验证 LLM 生成的代码：
1. 提取代码块
2. 语法检查
3. 实际执行
4. 集成到测试流程
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure TigerHill is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tigerhill.eval.code_validator import CodeExtractor, PythonValidator, CodeValidator
from tigerhill.eval.assertions import run_assertions


def demo_1_extract_code():
    """示例 1: 提取代码块"""
    print("=" * 80)
    print("示例 1: 从 LLM 输出中提取代码块")
    print("=" * 80)

    llm_output = """
Here's a Python function to calculate factorial:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))
```

And here's a JavaScript version:

```javascript
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
console.log(factorial(5));
```
"""

    # 提取所有代码块
    all_blocks = CodeExtractor.extract_code_blocks(llm_output)
    print(f"\n找到 {len(all_blocks)} 个代码块:")
    for i, block in enumerate(all_blocks, 1):
        print(f"\n[{i}] {block['language']}:")
        print(block['code'][:100] + "...")

    # 提取特定语言
    python_code = CodeExtractor.extract_first_code(llm_output, language="python")
    print(f"\n提取的 Python 代码:\n{python_code}")


def demo_2_syntax_check():
    """示例 2: 语法检查"""
    print("\n" + "=" * 80)
    print("示例 2: Python 语法检查")
    print("=" * 80)

    # 正确的代码
    good_code = """
def greet(name):
    return f"Hello, {name}!"

print(greet("TigerHill"))
"""

    print("\n✅ 检查正确的代码:")
    success, error = PythonValidator.check_syntax(good_code)
    print(f"   结果: {'通过' if success else '失败'}")
    if error:
        print(f"   错误: {error}")

    # 有语法错误的代码
    bad_code = """
def greet(name)  # 缺少冒号
    return f"Hello, {name}!"
"""

    print("\n❌ 检查有错误的代码:")
    success, error = PythonValidator.check_syntax(bad_code)
    print(f"   结果: {'通过' if success else '失败'}")
    if error:
        print(f"   错误: {error}")


def demo_3_execute_code():
    """示例 3: 实际执行代码"""
    print("\n" + "=" * 80)
    print("示例 3: 在隔离环境中执行 Python 代码")
    print("=" * 80)

    code = """
def add(a, b):
    return a + b

result = add(10, 20)
print(f"10 + 20 = {result}")
"""

    print("\n执行代码:")
    success, stdout, stderr = PythonValidator.execute_code(code, timeout=10)

    print(f"   结果: {'成功' if success else '失败'}")
    if stdout:
        print(f"   输出: {stdout.strip()}")
    if stderr:
        print(f"   错误: {stderr.strip()}")


def demo_4_assertion_integration():
    """示例 4: 集成到断言系统"""
    print("\n" + "=" * 80)
    print("示例 4: 使用 code_validation 断言类型")
    print("=" * 80)

    # 模拟 LLM 生成包含代码的输出
    llm_output = """
Here's a function to check if a number is prime:

```python
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

# Test
print(is_prime(17))  # Should print True
print(is_prime(18))  # Should print False
```

This implementation is efficient and correct.
"""

    # 定义断言（包含代码验证）
    assertions = [
        # 1. 检查文本内容
        {
            "type": "contains",
            "expected": "is_prime"
        },
        # 2. 验证代码语法
        {
            "type": "code_validation",
            "language": "python",
            "validation_type": "syntax"
        },
        # 3. 实际执行代码
        {
            "type": "code_validation",
            "language": "python",
            "validation_type": "execution",
            "timeout": 10
        }
    ]

    # 运行断言
    print("\n运行断言:")
    results = run_assertions(llm_output, assertions)

    for i, result in enumerate(results, 1):
        status = "✅" if result["ok"] else "❌"
        print(f"\n[{i}] {status} {result['type']}")
        print(f"    期望: {result['expected']}")
        if not result["ok"] and result["message"]:
            print(f"    错误: {result['message']}")

    passed = sum(1 for r in results if r["ok"])
    print(f"\n总结: {passed}/{len(results)} 个断言通过")


def demo_5_test_gemini_output():
    """示例 5: 验证 Gemini CLI 生成的代码"""
    print("\n" + "=" * 80)
    print("示例 5: 验证真实 LLM 输出的代码")
    print("=" * 80)

    # 这是从 test_gemini_cli.py 获得的实际输出（简化版）
    gemini_output = """
```python
import os
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import tool

@tool
def web_scraper(url: str) -> str:
    \"\"\"Scrapes the content of a given URL and returns the text.\"\"\"
    try:
        import requests
        from bs4 import BeautifulSoup
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.get_text()
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"

def create_crawling_agent():
    \"\"\"Creates a LangChain agent for web crawling and data extraction.\"\"\"
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-1106")
    tools = [web_scraper]
    prompt_template = \"\"\"
    You are a web crawling agent. You can use the web_scraper tool to get the content of a URL.
    Answer the following question: {input}
    \"\"\"
    prompt = ChatPromptTemplate.from_template(prompt_template)
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
```
"""

    # 定义验证断言
    assertions = [
        # 检查关键概念是否出现
        {"type": "contains", "expected": "langchain"},
        {"type": "contains", "expected": "web_scraper"},
        {"type": "contains", "expected": "BeautifulSoup"},

        # 验证代码语法
        {
            "type": "code_validation",
            "language": "python",
            "validation_type": "syntax"
        }
        # 注意：不执行代码，因为需要外部依赖（langchain, bs4 等）
    ]

    print("\n运行验证:")
    results = run_assertions(gemini_output, assertions)

    for i, result in enumerate(results, 1):
        status = "✅" if result["ok"] else "❌"
        print(f"[{i}] {status} {result['type']}: {result.get('message', 'OK')}")

    passed = sum(1 for r in results if r["ok"])
    print(f"\n✅ 代码质量验证: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("🎉 生成的代码格式正确且语法有效！")


def main():
    """运行所有示例"""
    print("\n🐯 TigerHill Code Validation Examples\n")

    demo_1_extract_code()
    demo_2_syntax_check()
    demo_3_execute_code()
    demo_4_assertion_integration()
    demo_5_test_gemini_output()

    print("\n" + "=" * 80)
    print("✅ 所有示例运行完成")
    print("=" * 80)
    print("\n💡 下一步:")
    print("   1. 在你的测试中使用 'code_validation' 断言")
    print("   2. 结合 AgentBay 在云端安全执行代码")
    print("   3. 验证生成代码的测试覆盖率")
    print()


if __name__ == "__main__":
    main()
