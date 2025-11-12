"""
Diff View - Incremental Visualization

Displays only the changes between consecutive turns,
hiding repeated content to improve readability.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing import List, Optional
from tigerhill.analyzer.models import (
    TurnDiff,
    PromptStructure,
    PromptComponent,
    PromptComponentType,
    TurnIntentAnalysis,
    IntentUnit,
    IntentType
)
from tigerhill.observer.conversation_models import ConversationTurn as Turn

# 临时定义LLMSession类，用于解决导入问题
class LLMSession:
    def __init__(self, session_id: str, turns: List[Turn], total_tokens: int, start_time: str, end_time: str):
        self.session_id = session_id
        self.turns = turns
        self.total_tokens = total_tokens
        self.start_time = start_time
        self.end_time = end_time


class DiffView:
    """生成 Diff 视图"""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize DiffView.

        Args:
            console: Rich Console instance (creates new one if not provided)
        """
        self.console = console or Console()

    def render(self, *args, **kwargs):
        """
        渲染 diff 视图（兼容两种调用方式）

        支持：
        1) render(diff, from_structure, to_structure, show_unchanged=True, show_content=True)
        2) render(from_turn, to_turn, from_turn_num, to_turn_num, show_unchanged=False, show_intent_diffs=False)
        """
        # 解析参数模式
        if args and isinstance(args[0], TurnDiff):
            # 模式1：使用 TurnDiff + PromptStructure
            diff: TurnDiff = args[0]
            from_structure: PromptStructure = args[1]
            to_structure: PromptStructure = args[2]
            show_unchanged: bool = kwargs.get('show_unchanged', False)
            show_content: bool = kwargs.get('show_content', True)
            show_intent_diffs: bool = kwargs.get('show_intent_diffs', False)

            # 标题与摘要
            self._render_summary(diff, from_turn=diff.from_turn, to_turn=diff.to_turn)

            # 未变化组件
            if show_unchanged:
                unchanged = self._get_unchanged_components(from_structure, to_structure)
                if unchanged:
                    self.console.print(f"\n[dim]未变化的组件 ({len(unchanged)}):[/dim]")
                    for component in unchanged:
                        self._render_component(component, "unchanged", show_content=show_content)

            # 新增/移除/修改组件
            if diff.added_components:
                self.console.print(f"\n[bold green]添加的组件 ({len(diff.added_components)}):[/bold green]")
                for component in diff.added_components:
                    self._render_component(component, "added", show_content=show_content)

            if diff.removed_components:
                self.console.print(f"\n[bold red]移除的组件 ({len(diff.removed_components)}):[/bold red]")
                for component in diff.removed_components:
                    self._render_component(component, "removed", show_content=show_content)

            if diff.modified_components:
                self.console.print(f"\n[bold yellow]修改的组件 ({len(diff.modified_components)}):[/bold yellow]")
                for component in diff.modified_components:
                    self._render_modified_component(component, show_content=show_content)

            # 意图差异（可选详细展示）
            if show_intent_diffs and hasattr(from_structure, 'intent_analysis') and hasattr(to_structure, 'intent_analysis'):
                self.render_intent_diff(
                    getattr(from_structure, 'intent_analysis', None),
                    getattr(to_structure, 'intent_analysis', None),
                    diff.from_turn,
                    diff.to_turn
                )
                self.render_intent_transition(
                    getattr(from_structure, 'intent_analysis', None),
                    getattr(to_structure, 'intent_analysis', None),
                    diff.from_turn,
                    diff.to_turn
                )

            return

        # 模式2：旧签名，使用 Turn 对象
        from_turn = args[0]
        to_turn = args[1]
        from_turn_num: int = args[2]
        to_turn_num: int = args[3]
        show_unchanged: bool = kwargs.get('show_unchanged', False)
        show_intent_diffs: bool = kwargs.get('show_intent_diffs', False)

        # 创建差异对象并渲染
        diff = self._create_turn_diff(from_turn, to_turn, from_turn_num, to_turn_num)
        self._render_summary(diff, from_turn=from_turn_num, to_turn=to_turn_num)

        if diff.added_components:
            self.console.print(f"\n[bold green]添加的组件 ({len(diff.added_components)}):[/bold green]")
            for component in diff.added_components:
                self._render_component(component, "+")

        if diff.removed_components:
            self.console.print(f"\n[bold red]移除的组件 ({len(diff.removed_components)}):[/bold red]")
            for component in diff.removed_components:
                self._render_component(component, "-")

        if diff.modified_components:
            self.console.print(f"\n[bold yellow]修改的组件 ({len(diff.modified_components)}):[/bold yellow]")
            for component in diff.modified_components:
                self._render_modified_component(component)

        if show_unchanged and diff.unchanged_components:
            self.console.print(f"\n[dim]未变化的组件 ({len(diff.unchanged_components)}):[/dim]")
            for component in diff.unchanged_components:
                self._render_component(component, " ")

        if show_intent_diffs and hasattr(from_turn, 'intent_analysis') and hasattr(to_turn, 'intent_analysis'):
            self.render_intent_diff(
                from_turn.intent_analysis,
                to_turn.intent_analysis,
                from_turn_num,
                to_turn_num
            )
            self.render_intent_transition(
                from_turn.intent_analysis,
                to_turn.intent_analysis,
                from_turn_num,
                to_turn_num
            )

    def _render_component(
        self,
        comp: PromptComponent,
        status: str,
        show_content: bool = True
    ):
        """
        渲染单个组件

        Args:
            comp: 组件对象
            status: "added", "removed", "unchanged"
            show_content: 是否显示内容
        """
        # Icon and color mapping
        icons = {
            "added": ("➕", "green"),
            "removed": ("➖", "red"),
            "unchanged": ("⚪", "dim"),
            "modified": ("🔄", "yellow")
        }

        icon, color = icons.get(status, ("•", "white"))

        # Header
        # Handle both enum and string types (Pydantic may convert enum to string)
        comp_type = comp.type.value if hasattr(comp.type, 'value') else comp.type
        header = f"{comp_type.title()} ({status.upper()}, {comp.tokens} tokens)"
        if comp.role:
            header += f" [{comp.role}]"

        self.console.print(f"[{color}]{icon} {header}[/{color}]")

        # Content
        if show_content:
            content = self._truncate_content(comp.content, max_lines=8, max_chars=100)
            panel = Panel(
                content,
                border_style=color,
                padding=(0, 1),
                expand=False
            )
            self.console.print(panel)

        self.console.print()

    def _render_modified_component(
        self,
        mod: dict,
        show_content: bool = True
    ):
        """渲染修改的组件"""
        old_comp = mod["old"]
        new_comp = mod["new"]
        changes = mod.get("changes", [])

        icon = "🔄"
        comp_type = old_comp.type.value if hasattr(old_comp.type, 'value') else old_comp.type
        header = f"{comp_type.title()} (MODIFIED)"
        self.console.print(f"[yellow]{icon} {header}[/yellow]")

        if show_content and changes:
            # Show diff details
            added_lines = [c for c in changes if c["type"] == "added"]
            removed_lines = [c for c in changes if c["type"] == "removed"]

            summary = f"  +{len(added_lines)} lines, -{len(removed_lines)} lines"
            self.console.print(f"[dim]{summary}[/dim]")

            # Show first few changes
            if len(added_lines) > 0:
                self.console.print("[green]  Added:[/green]")
                for change in added_lines[:3]:
                    content = change.get("content", "")[:80]
                    self.console.print(f"[green]  + {content}[/green]")

            if len(removed_lines) > 0:
                self.console.print("[red]  Removed:[/red]")
                for change in removed_lines[:3]:
                    content = change.get("content", "")[:80]
                    self.console.print(f"[red]  - {content}[/red]")

        self.console.print()

    def _render_summary(self, diff: TurnDiff, from_turn: int, to_turn: int):
        """渲染差异摘要"""
        total_changes = len(diff.added_components) + len(diff.removed_components) + len(diff.modified_components)
        
        self.console.print(f"\n[bold cyan]差异摘要:[/bold cyan]")
        self.console.print(f"轮次: {from_turn} → {to_turn}")
        self.console.print(f"总变化: {total_changes}")
        self.console.print(f"  添加: [green]{len(diff.added_components)}[/green]")
        self.console.print(f"  移除: [red]{len(diff.removed_components)}[/red]")
        self.console.print(f"  修改: [yellow]{len(diff.modified_components)}[/yellow]")
        
        # 令牌变化
        if hasattr(diff, 'token_changes') and diff.token_changes:
            self.console.print(f"令牌变化: {diff.token_changes}")
        
        # 组件变化统计
        if hasattr(diff, 'component_stats') and diff.component_stats:
            self.console.print(f"组件统计: {diff.component_stats}")
        
        # 意图差异
        if hasattr(diff, 'intent_diff') and diff.intent_diff:
            self.console.print(f"意图差异: {diff.intent_diff}")

    def _create_turn_diff(
        self,
        from_turn: Turn,
        to_turn: Turn,
        from_turn_num: int,
        to_turn_num: int
    ) -> TurnDiff:
        """创建轮次差异对象"""
        # 这里简化实现，实际应该比较两个轮次的具体组件
        # 现在创建一个基础的差异对象
        return TurnDiff(
            from_turn=from_turn_num,
            to_turn=to_turn_num,
            added_components=[],
            removed_components=[],
            modified_components=[],
            unchanged_components=[],
            token_changes=to_turn.total_tokens - from_turn.total_tokens if hasattr(to_turn, 'total_tokens') and hasattr(from_turn, 'total_tokens') else 0,
            component_stats={},
            intent_diff=None
        )

    def _get_unchanged_components(
        self,
        from_structure: PromptStructure,
        to_structure: PromptStructure
    ) -> List[PromptComponent]:
        """获取未变化的组件"""
        unchanged = []

        from_map = {
            (c.type, c.content): c
            for c in from_structure.components
        }

        for comp in to_structure.components:
            key = (comp.type, comp.content)
            if key in from_map:
                unchanged.append(comp)

        return unchanged

    def _truncate_content(
        self,
        content: str,
        max_lines: int = 5,
        max_chars: int = 80
    ) -> str:
        """截断内容"""
        lines = content.split('\n')

        if len(lines) > max_lines:
            truncated_lines = lines[:max_lines]
            remaining = len(lines) - max_lines
            truncated_lines.append(f"... ({remaining} more lines)")
            lines = truncated_lines

        # 截断每行
        lines = [
            line[:max_chars] + "..." if len(line) > max_chars else line
            for line in lines
        ]

        return '\n'.join(lines)

    def render_intent_diff(
        self,
        from_analysis: Optional[TurnIntentAnalysis],
        to_analysis: Optional[TurnIntentAnalysis],
        from_turn: int,
        to_turn: int
    ):
        """
        渲染意图差异分析

        Args:
            from_analysis: 源意图分析
            to_analysis: 目标意图分析
            from_turn: 源轮次
            to_turn: 目标轮次
        """
        self.console.print(f"\n[bold cyan]═══ Intent Diff: Turn {from_turn} → Turn {to_turn} ═══[/bold cyan]\n")

        # 检查意图分析是否可用
        if not from_analysis and not to_analysis:
            self.console.print("[dim]No intent analysis available for both turns[/dim]")
            return

        if not from_analysis:
            self.console.print(f"[dim]No intent analysis for turn {from_turn}[/dim]")
            self._render_intent_analysis_summary(to_analysis, "New Intent Analysis")
            return

        if not to_analysis:
            self.console.print(f"[dim]No intent analysis for turn {to_turn}[/dim]")
            self._render_intent_analysis_summary(from_analysis, "Previous Intent Analysis")
            return

        # 比较意图变化
        intent_changed = from_analysis.primary_intent != to_analysis.primary_intent
        confidence_change = to_analysis.intent_confidence - from_analysis.intent_confidence
        complexity_change = to_analysis.complexity_score - from_analysis.complexity_score

        # 显示主要意图变化
        if intent_changed:
            self.console.print(f"[bold]Intent Change:[/bold]")
            self.console.print(f"  From: [yellow]{from_analysis.primary_intent.value}[/yellow]")
            self.console.print(f"  To:   [green]{to_analysis.primary_intent.value}[/green]")
        else:
            self.console.print(f"[bold]Intent:[/bold] [cyan]{from_analysis.primary_intent.value}[/cyan] (unchanged)")

        # 显示置信度变化
        confidence_color = "green" if confidence_change > 0 else "red" if confidence_change < 0 else "yellow"
        confidence_symbol = "↗" if confidence_change > 0 else "↘" if confidence_change < 0 else "→"
        self.console.print(f"[bold]Confidence:[/bold] {from_analysis.intent_confidence:.2f} → "
                          f"[{confidence_color}]{to_analysis.intent_confidence:.2f} "
                          f"({confidence_symbol} {confidence_change:+.2f})[/{confidence_color}]")

        # 显示复杂度变化
        complexity_color = "green" if complexity_change < 0 else "red" if complexity_change > 0 else "yellow"
        complexity_symbol = "↘" if complexity_change < 0 else "↗" if complexity_change > 0 else "→"
        self.console.print(f"[bold]Complexity:[/bold] {from_analysis.complexity_score:.2f} → "
                          f"[{complexity_color}]{to_analysis.complexity_score:.2f} "
                          f"({complexity_symbol} {complexity_change:+.2f})[/{complexity_color}]")

        # 显示意图单元差异
        self._render_intent_units_diff(from_analysis, to_analysis)

        # 显示转换分析
        self._render_intent_transition_analysis(from_analysis, to_analysis)

    def _render_intent_analysis_summary(self, analysis: TurnIntentAnalysis, title: str):
        """渲染意图分析摘要"""
        self.console.print(f"\n[bold]{title}:[/bold]")
        self.console.print(f"  Intent: [cyan]{analysis.primary_intent.value}[/cyan]")
        self.console.print(f"  Confidence: [green]{analysis.intent_confidence:.2f}[/green]")
        self.console.print(f"  Complexity: [yellow]{analysis.complexity_score:.2f}[/yellow]")
        self.console.print(f"  Units: [magenta]{len(analysis.intent_units)}[/magenta]")

    def _render_intent_units_diff(
        self,
        from_analysis: TurnIntentAnalysis,
        to_analysis: TurnIntentAnalysis
    ):
        """渲染意图单元差异"""
        if not from_analysis.intent_units and not to_analysis.intent_units:
            return

        self.console.print(f"\n[bold]Intent Units Analysis:[/bold]")

        # 统计意图单元类型
        from_unit_types = {unit.intent_type.value for unit in from_analysis.intent_units}
        to_unit_types = {unit.intent_type.value for unit in to_analysis.intent_units}

        added_types = to_unit_types - from_unit_types
        removed_types = from_unit_types - to_unit_types
        common_types = from_unit_types & to_unit_types

        if added_types:
            self.console.print(f"[green]  Added Types:[/green] {', '.join(added_types)}")
        if removed_types:
            self.console.print(f"[red]  Removed Types:[/red] {', '.join(removed_types)}")
        if common_types:
            self.console.print(f"[dim]  Common Types:[/dim] {', '.join(common_types)}")

        # 显示详细单元比较
        if len(from_analysis.intent_units) > 0 or len(to_analysis.intent_units) > 0:
            self.console.print(f"\n[dim]  Unit Count: {len(from_analysis.intent_units)} → {len(to_analysis.intent_units)}[/dim]")

    def _render_intent_transition_analysis(
        self,
        from_analysis: TurnIntentAnalysis,
        to_analysis: TurnIntentAnalysis
    ):
        """渲染意图转换分析"""
        if from_analysis.primary_intent == to_analysis.primary_intent:
            return

        self.console.print(f"\n[bold]Intent Transition Analysis:[/bold]")
        
        # 简单的转换质量评估
        confidence_stability = abs(to_analysis.intent_confidence - from_analysis.intent_confidence) < 0.2
        complexity_reasonable = abs(to_analysis.complexity_score - from_analysis.complexity_score) < 0.3

        if confidence_stability and complexity_reasonable:
            self.console.print("[green]  ✓ Smooth transition[/green]")
        else:
            self.console.print("[yellow]  ⚠ Significant change detected[/yellow]")

        # 转换类型分析
        transition_type = self._analyze_transition_type(from_analysis, to_analysis)
        if transition_type:
            self.console.print(f"  Transition Type: [cyan]{transition_type}[/cyan]")

    def _analyze_transition_type(
        self,
        from_analysis: TurnIntentAnalysis,
        to_analysis: TurnIntentAnalysis
    ) -> str:
        """分析转换类型"""
        from_intent = from_analysis.primary_intent.value
        to_intent = to_analysis.primary_intent.value

        # 常见转换模式
        transitions = {
            ("task_execution", "validation"): "Implementation → Verification",
            ("validation", "task_execution"): "Verification → Implementation", 
            ("question", "clarification"): "Question → Clarification",
            ("clarification", "question"): "Clarification → Question",
            ("task_execution", "refinement"): "Implementation → Refinement",
            ("refinement", "validation"): "Refinement → Verification"
        }

        return transitions.get((from_intent, to_intent), "Complex transition")

    def render_intent_transition(
        self,
        from_analysis: Optional[TurnIntentAnalysis],
        to_analysis: Optional[TurnIntentAnalysis],
        from_turn: int,
        to_turn: int
    ):
        """
        渲染意图转换可视化

        Args:
            from_analysis: 源意图分析
            to_analysis: 目标意图分析
            from_turn: 源轮次
            to_turn: 目标轮次
        """
        self.console.print(f"\n[bold magenta]═══ Intent Transition: Turn {from_turn} → Turn {to_turn} ═══[/bold magenta]\n")

        if not from_analysis or not to_analysis:
            self.console.print("[dim]Insufficient data for transition analysis[/dim]")
            return

        # 创建转换可视化
        from_intent = from_analysis.primary_intent.value
        to_intent = to_analysis.primary_intent.value
        
        # 显示转换箭头
        self.console.print(f"[cyan]{from_intent}[/cyan] [bold]→[/bold] [green]{to_intent}[/green]")
        
        # 显示转换质量指标
        confidence_change = to_analysis.intent_confidence - from_analysis.intent_confidence
        complexity_change = to_analysis.complexity_score - from_analysis.complexity_score
        
        # 转换流畅度评估
        flow_score = self._calculate_flow_score(from_analysis, to_analysis)
        
        self.console.print(f"\n[bold]Transition Quality:[/bold]")
        self.console.print(f"  Flow Score: [yellow]{flow_score:.2f}/1.0[/yellow]")
        
        if flow_score > 0.8:
            self.console.print("  Status: [green]✓ Smooth transition[/green]")
        elif flow_score > 0.5:
            self.console.print("  Status: [yellow]⚠ Moderate change[/yellow]")
        else:
            self.console.print("  Status: [red]✗ Abrupt transition[/red]")

        # 显示详细指标变化
        self.console.print(f"\n[bold]Metric Changes:[/bold]")
        self.console.print(f"  Confidence: {from_analysis.intent_confidence:.2f} → {to_analysis.intent_confidence:.2f} "
                          f"({confidence_change:+.2f})")
        self.console.print(f"  Complexity: {from_analysis.complexity_score:.2f} → {to_analysis.complexity_score:.2f} "
                          f"({complexity_change:+.2f})")
        self.console.print(f"  Units: {len(from_analysis.intent_units)} → {len(to_analysis.intent_units)} "
                          f"({len(to_analysis.intent_units) - len(from_analysis.intent_units):+d})")

    def _calculate_flow_score(
        self,
        from_analysis: TurnIntentAnalysis,
        to_analysis: TurnIntentAnalysis
    ) -> float:
        """计算转换流畅度分数"""
        # 基于置信度稳定性和复杂度合理性计算
        confidence_stability = 1.0 - abs(to_analysis.intent_confidence - from_analysis.intent_confidence)
        complexity_reasonable = 1.0 - min(abs(to_analysis.complexity_score - from_analysis.complexity_score), 0.5) * 2
        
        # 意图类型转换合理性（简单规则）
        intent_continuity = 1.0 if from_analysis.primary_intent == to_analysis.primary_intent else 0.7
        
        # 综合分数
        flow_score = (confidence_stability + complexity_reasonable + intent_continuity) / 3.0
        return min(max(flow_score, 0.0), 1.0)

    def render_all_diffs(
        self,
        session: LLMSession,
        show_unchanged: bool = False,
        show_intent_diffs: bool = False
    ):
        """渲染所有轮次的差异"""
        if not session.turns or len(session.turns) < 2:
            self.console.print("[red]需要至少两个轮次来显示差异[/red]")
            return

        self.console.print(f"\n[bold blue]会话差异分析[/bold blue]")
        self.console.print(f"会话ID: {session.session_id}")
        self.console.print(f"总轮次: {len(session.turns)}")
        self.console.print(f"总令牌数: {session.total_tokens}")
        self.console.print(f"时间范围: {session.start_time} - {session.end_time}")

        # 显示轮次间的差异
        for i in range(len(session.turns) - 1):
            current_turn = session.turns[i]
            next_turn = session.turns[i + 1]

            self.console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
            self.console.print(f"[bold cyan]轮次 {i + 1} → 轮次 {i + 2}[/bold cyan]")
            self.console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")

            self.render(
                current_turn,
                next_turn,
                i + 1,
                i + 2,
                show_unchanged=show_unchanged
            )

            # 显示意图差异分析
            if show_intent_diffs and hasattr(current_turn, 'intent_analysis') and hasattr(next_turn, 'intent_analysis'):
                self.render_intent_diff(
                    current_turn.intent_analysis,
                    next_turn.intent_analysis,
                    i + 1,
                    i + 2
                )
                self.render_intent_transition(
                    current_turn.intent_analysis,
                    next_turn.intent_analysis,
                    i + 1,
                    i + 2
                )
