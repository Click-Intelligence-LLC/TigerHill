"""
Prompt Analyzer - 自动分析捕获的 Prompt

提供以下分析功能：
- Token 使用分析
- Prompt 质量评估
- 性能分析
- 工具使用分析
- 优化建议
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Prompt 自动分析器

    分析捕获的 prompt 数据，提供洞察和优化建议。
    """

    def __init__(self, capture: Any):
        """
        初始化分析器

        Args:
            capture: PromptCapture 实例或捕获数据字典
        """
        if hasattr(capture, "captures"):
            # PromptCapture 实例
            self.captures = list(capture.captures.values())
        elif isinstance(capture, dict):
            # 单个捕获数据
            self.captures = [capture]
        elif isinstance(capture, list):
            # 捕获数据列表
            self.captures = capture
        else:
            raise ValueError("Invalid capture data")

        logger.info(f"Initialized analyzer with {len(self.captures)} captures")

    def analyze_all(self) -> Dict[str, Any]:
        """
        执行完整分析

        Returns:
            完整的分析报告
        """
        report = {
            "summary": self.get_summary(),
            "token_analysis": self.analyze_tokens(),
            "prompt_quality": self.analyze_prompt_quality(),
            "performance": self.analyze_performance(),
            "tool_usage": self.analyze_tool_usage(),
            "recommendations": self.generate_recommendations()
        }

        return report

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要信息"""
        total_captures = len(self.captures)
        total_requests = sum(len(c.get("requests", [])) for c in self.captures)
        total_responses = sum(len(c.get("responses", [])) for c in self.captures)

        # 统计不同的 agent
        agents = set(c.get("agent_name") for c in self.captures)

        # 统计不同的模型
        models = set()
        for capture in self.captures:
            for request in capture.get("requests", []):
                if "model" in request:
                    models.add(request["model"])

        return {
            "total_captures": total_captures,
            "total_requests": total_requests,
            "total_responses": total_responses,
            "unique_agents": len(agents),
            "unique_models": len(models),
            "agents": list(agents),
            "models": list(models)
        }

    def analyze_tokens(self) -> Dict[str, Any]:
        """
        分析 Token 使用情况

        Returns:
            Token 分析报告
        """
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        token_counts = []

        for capture in self.captures:
            for response in capture.get("responses", []):
                usage = response.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_tokens += prompt_tokens + completion_tokens

                if prompt_tokens + completion_tokens > 0:
                    token_counts.append(prompt_tokens + completion_tokens)

        # 计算平均值
        avg_tokens = total_tokens / len(token_counts) if token_counts else 0
        avg_prompt_tokens = total_prompt_tokens / len(token_counts) if token_counts else 0
        avg_completion_tokens = total_completion_tokens / len(token_counts) if token_counts else 0

        # 计算 token 效率（completion / prompt 比率）
        efficiency = (
            total_completion_tokens / total_prompt_tokens
            if total_prompt_tokens > 0
            else 0
        )

        return {
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "avg_tokens_per_request": avg_tokens,
            "avg_prompt_tokens": avg_prompt_tokens,
            "avg_completion_tokens": avg_completion_tokens,
            "token_efficiency_ratio": efficiency,
            "max_tokens": max(token_counts) if token_counts else 0,
            "min_tokens": min(token_counts) if token_counts else 0
        }

    def analyze_prompt_quality(self) -> Dict[str, Any]:
        """
        分析 Prompt 质量

        Returns:
            质量分析报告
        """
        prompts = []
        system_prompts = []

        for capture in self.captures:
            for request in capture.get("requests", []):
                if "prompt" in request:
                    prompts.append(request["prompt"])
                if "system_prompt" in request:
                    system_prompts.append(request["system_prompt"])

        # 分析 prompt 长度
        prompt_lengths = [len(str(p)) for p in prompts]
        avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0

        # 分析是否包含系统 prompt
        has_system_prompt_ratio = len(system_prompts) / len(prompts) if prompts else 0

        # 检测常见问题
        issues = self._detect_prompt_issues(prompts)

        # 分析指令清晰度
        clarity_score = self._calculate_clarity_score(prompts)

        return {
            "total_prompts": len(prompts),
            "avg_prompt_length": avg_prompt_length,
            "has_system_prompt_ratio": has_system_prompt_ratio,
            "clarity_score": clarity_score,
            "detected_issues": issues
        }

    def analyze_performance(self) -> Dict[str, Any]:
        """
        分析性能指标

        Returns:
            性能分析报告
        """
        durations = []

        for capture in self.captures:
            if "duration" in capture:
                durations.append(capture["duration"])

        if not durations:
            return {
                "avg_duration": 0,
                "max_duration": 0,
                "min_duration": 0,
                "total_duration": 0
            }

        return {
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations),
            "total_duration": sum(durations),
            "num_captures": len(durations)
        }

    def analyze_tool_usage(self) -> Dict[str, Any]:
        """
        分析工具使用情况

        Returns:
            工具使用分析报告
        """
        tool_calls = []
        tools_defined = []

        for capture in self.captures:
            # 收集定义的工具
            for request in capture.get("requests", []):
                if "tools" in request and request["tools"]:
                    tools_defined.extend(request["tools"])

            # 收集工具调用
            for response in capture.get("responses", []):
                if "tool_calls" in response and response["tool_calls"]:
                    tool_calls.extend(response["tool_calls"])

        # 统计工具名称
        tool_names_defined = [
            t.get("name", t.get("function_name", "unknown"))
            for t in tools_defined
            if isinstance(t, dict)
        ]

        tool_names_called = [
            tc.get("name", "unknown")
            for tc in tool_calls
            if isinstance(tc, dict)
        ]

        # 计数
        tool_counts = Counter(tool_names_called)

        # 计算工具使用率
        total_requests = sum(len(c.get("requests", [])) for c in self.captures)
        tool_usage_rate = len(tool_calls) / total_requests if total_requests > 0 else 0

        return {
            "total_tools_defined": len(tools_defined),
            "unique_tools_defined": len(set(tool_names_defined)),
            "total_tool_calls": len(tool_calls),
            "unique_tools_called": len(set(tool_names_called)),
            "tool_usage_rate": tool_usage_rate,
            "most_used_tools": tool_counts.most_common(5),
            "tools_defined_but_not_used": list(
                set(tool_names_defined) - set(tool_names_called)
            )
        }

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """
        生成优化建议

        Returns:
            建议列表
        """
        recommendations = []

        # Token 使用建议
        token_analysis = self.analyze_tokens()
        if token_analysis["avg_prompt_tokens"] > 2000:
            recommendations.append({
                "category": "token_optimization",
                "severity": "medium",
                "title": "Prompt 过长",
                "description": f"平均 prompt tokens: {token_analysis['avg_prompt_tokens']:.0f}",
                "suggestion": "考虑简化 prompt 或使用更短的示例。长 prompt 会增加成本和延迟。"
            })

        if token_analysis["token_efficiency_ratio"] < 0.5:
            recommendations.append({
                "category": "token_optimization",
                "severity": "low",
                "title": "Token 效率较低",
                "description": f"输出/输入比率: {token_analysis['token_efficiency_ratio']:.2f}",
                "suggestion": "输出相对输入较少，考虑是否可以简化 prompt 或要求更详细的输出。"
            })

        # Prompt 质量建议
        quality = self.analyze_prompt_quality()
        if quality["has_system_prompt_ratio"] < 0.5:
            recommendations.append({
                "category": "prompt_quality",
                "severity": "medium",
                "title": "缺少系统 Prompt",
                "description": f"只有 {quality['has_system_prompt_ratio']*100:.1f}% 的请求包含系统 prompt",
                "suggestion": "添加系统 prompt 可以提供更好的上下文和行为控制。"
            })

        if quality["clarity_score"] < 0.6:
            recommendations.append({
                "category": "prompt_quality",
                "severity": "high",
                "title": "Prompt 清晰度不足",
                "description": f"清晰度评分: {quality['clarity_score']:.2f}/1.0",
                "suggestion": "使用更明确的指令，包含具体的格式要求和示例。"
            })

        # 添加检测到的问题
        for issue in quality.get("detected_issues", []):
            recommendations.append({
                "category": "prompt_quality",
                "severity": "medium",
                "title": issue["type"],
                "description": issue["description"],
                "suggestion": issue["suggestion"]
            })

        # 工具使用建议
        tool_usage = self.analyze_tool_usage()
        if tool_usage["tools_defined_but_not_used"]:
            recommendations.append({
                "category": "tool_usage",
                "severity": "low",
                "title": "未使用的工具",
                "description": f"定义了 {len(tool_usage['tools_defined_but_not_used'])} 个从未被调用的工具",
                "suggestion": f"考虑移除这些工具: {', '.join(tool_usage['tools_defined_but_not_used'][:3])}"
            })

        # 性能建议
        performance = self.analyze_performance()
        if performance["avg_duration"] > 10:
            recommendations.append({
                "category": "performance",
                "severity": "high",
                "title": "响应时间过长",
                "description": f"平均响应时间: {performance['avg_duration']:.2f}s",
                "suggestion": "考虑简化 prompt、减少输出长度或使用更快的模型。"
            })

        return recommendations

    def _detect_prompt_issues(self, prompts: List[str]) -> List[Dict[str, str]]:
        """检测 prompt 中的常见问题"""
        issues = []

        for prompt in prompts:
            prompt_str = str(prompt)

            # 检测是否过于简短
            if len(prompt_str) < 20:
                issues.append({
                    "type": "too_short",
                    "description": "Prompt 过于简短，可能导致不明确的输出",
                    "suggestion": "提供更多上下文和具体要求"
                })

            # 检测是否缺少明确指令
            if not any(word in prompt_str.lower() for word in ["please", "请", "should", "必须", "需要"]):
                if not re.search(r'[\.\?!]', prompt_str):
                    issues.append({
                        "type": "lacks_clear_instruction",
                        "description": "缺少明确的指令或请求",
                        "suggestion": "使用明确的动词和要求，如 '请生成...'、'分析...' 等"
                    })

            # 检测是否包含示例
            if "example" not in prompt_str.lower() and "示例" not in prompt_str:
                if len(prompt_str) > 200:  # 只对复杂任务建议
                    issues.append({
                        "type": "lacks_examples",
                        "description": "复杂任务缺少示例",
                        "suggestion": "提供输入/输出示例可以显著提高输出质量"
                    })

        return issues[:5]  # 最多返回 5 个问题

    def _calculate_clarity_score(self, prompts: List[str]) -> float:
        """
        计算 prompt 清晰度评分

        基于以下因素：
        - 是否包含明确的指令动词
        - 是否有格式要求
        - 是否有示例
        - 是否有约束条件
        """
        if not prompts:
            return 0.0

        scores = []

        for prompt in prompts:
            prompt_str = str(prompt).lower()
            score = 0.0

            # 包含指令动词 (+0.3)
            instruction_verbs = ['generate', 'create', 'analyze', 'summarize', 'explain',
                                 '生成', '创建', '分析', '总结', '解释']
            if any(verb in prompt_str for verb in instruction_verbs):
                score += 0.3

            # 包含格式要求 (+0.2)
            if any(word in prompt_str for word in ['format', 'structure', 'json', 'markdown',
                                                     '格式', '结构']):
                score += 0.2

            # 包含示例 (+0.3)
            if any(word in prompt_str for word in ['example', 'for instance', 'such as',
                                                     '示例', '例如']):
                score += 0.3

            # 包含约束 (+0.2)
            if any(word in prompt_str for word in ['must', 'should', 'limit', 'maximum',
                                                     '必须', '应该', '限制', '最多']):
                score += 0.2

            scores.append(min(score, 1.0))

        return sum(scores) / len(scores)

    def print_report(self, report: Optional[Dict[str, Any]] = None) -> None:
        """
        打印分析报告

        Args:
            report: 分析报告，如果为 None 则执行完整分析
        """
        if report is None:
            report = self.analyze_all()

        print("\n" + "=" * 80)
        print("📊 TigerHill Prompt Analysis Report")
        print("=" * 80)

        # 摘要
        summary = report["summary"]
        print("\n📋 Summary:")
        print(f"   Total Captures: {summary['total_captures']}")
        print(f"   Total Requests: {summary['total_requests']}")
        print(f"   Total Responses: {summary['total_responses']}")
        print(f"   Agents: {', '.join(summary['agents'])}")
        print(f"   Models: {', '.join(summary['models'])}")

        # Token 分析
        tokens = report["token_analysis"]
        print("\n💰 Token Usage:")
        print(f"   Total Tokens: {tokens['total_tokens']:,}")
        print(f"   Average per Request: {tokens['avg_tokens_per_request']:.0f}")
        print(f"   Efficiency Ratio: {tokens['token_efficiency_ratio']:.2f}")

        # 质量分析
        quality = report["prompt_quality"]
        print("\n✨ Prompt Quality:")
        print(f"   Clarity Score: {quality['clarity_score']:.2f}/1.0")
        print(f"   Has System Prompt: {quality['has_system_prompt_ratio']*100:.1f}%")
        print(f"   Average Length: {quality['avg_prompt_length']:.0f} chars")

        # 性能
        perf = report["performance"]
        print("\n⚡ Performance:")
        print(f"   Average Duration: {perf['avg_duration']:.2f}s")
        print(f"   Max Duration: {perf['max_duration']:.2f}s")

        # 工具使用
        tools = report["tool_usage"]
        print("\n🛠️  Tool Usage:")
        print(f"   Total Calls: {tools['total_tool_calls']}")
        print(f"   Usage Rate: {tools['tool_usage_rate']*100:.1f}%")
        if tools['most_used_tools']:
            print(f"   Most Used: {tools['most_used_tools'][0][0]} ({tools['most_used_tools'][0][1]} calls)")

        # 建议
        recommendations = report["recommendations"]
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["severity"], "⚪")
                print(f"\n   [{i}] {severity_emoji} {rec['title']}")
                print(f"       {rec['description']}")
                print(f"       💬 {rec['suggestion']}")

        print("\n" + "=" * 80)
