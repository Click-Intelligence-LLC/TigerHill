"""
Statistics View - Token & Cost Analysis

Displays token distribution, cost analysis, and optimization suggestions.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from typing import List, Optional, Dict, Any
from tigerhill.analyzer.models import PromptStructure, TurnIntentAnalysis, IntentUnit, IntentType


class StatsView:
    """统计视图生成器"""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize StatsView.

        Args:
            console: Rich Console instance (creates new one if not provided)
        """
        self.console = console or Console()

    def render_session_stats(
        self,
        structures: List[PromptStructure],
        session_data: Optional[Dict[str, Any]] = None
    ):
        """
        渲染整个会话的统计信息

        Args:
            structures: List of PromptStructure objects
            session_data: Optional session metadata
        """
        self.console.print("\n[bold cyan]═══ Session Statistics ═══[/bold cyan]\n")

        if session_data:
            session_id = session_data.get("session_id", "Unknown")
            self.console.print(f"Session ID: [cyan]{session_id[:20]}...[/cyan]")
            self.console.print()

        # Overall stats
        total_turns = len(structures)
        total_tokens = sum(s.total_tokens for s in structures)
        total_unique = sum(s.stats.get("unique_tokens", 0) for s in structures)
        avg_repeated = sum(s.stats.get("repeated_ratio", 0) for s in structures) / total_turns if total_turns > 0 else 0

        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_row("Total Turns:", f"[cyan]{total_turns}[/cyan]")
        stats_table.add_row("Total Tokens:", f"[yellow]{total_tokens:,}[/yellow]")

        # Avoid division by zero
        if total_tokens > 0:
            unique_pct = total_unique / total_tokens * 100
            stats_table.add_row("Unique Tokens:", f"[green]{total_unique:,}[/green] ({unique_pct:.1f}%)")
        else:
            stats_table.add_row("Unique Tokens:", f"[green]{total_unique:,}[/green] (0.0%)")

        stats_table.add_row("Avg Repeated:", self._format_repeated_ratio(avg_repeated))

        # 添加意图分析统计
        structures_with_intent = [
            s for s in structures 
            if hasattr(s, 'intent_analysis') and s.intent_analysis is not None
        ]
        
        if structures_with_intent:
            intent_turns = len(structures_with_intent)
            intent_coverage = (intent_turns / total_turns * 100) if total_turns > 0 else 0
            
            # 计算平均置信度
            avg_confidence = sum(
                s.intent_analysis.intent_confidence for s in structures_with_intent
            ) / len(structures_with_intent)
            
            # 计算平均复杂度
            avg_complexity = sum(
                s.intent_analysis.complexity_score for s in structures_with_intent
            ) / len(structures_with_intent)
            
            stats_table.add_row("Intent Analysis Turns:", f"[magenta]{intent_turns}[/magenta]")
            stats_table.add_row("Intent Coverage:", f"[blue]{intent_coverage:.1f}%[/blue]")
            stats_table.add_row("Avg Intent Confidence:", f"[green]{avg_confidence:.2f}[/green]")
            stats_table.add_row("Avg Intent Complexity:", f"[yellow]{avg_complexity:.2f}[/yellow]")

        self.console.print(stats_table)

    def render_token_distribution(
        self,
        structure: PromptStructure,
        show_bar: bool = True
    ):
        """
        渲染 token 分布图

        Args:
            structure: PromptStructure for a specific turn
            show_bar: Whether to show bar chart
        """
        self.console.print(f"\n[bold cyan]═══ Token Distribution (Turn {structure.turn_index}) ═══[/bold cyan]\n")

        stats = structure.stats
        total = structure.total_tokens

        if total == 0:
            self.console.print("[dim]No tokens in this turn[/dim]")
            return

        # Component breakdown
        components = [
            ("System Prompt", stats.get("system_tokens", 0), "cyan"),
            ("History", stats.get("history_tokens", 0), "yellow"),
            ("New User Input", stats.get("new_tokens", 0), "green"),
            ("Tools", stats.get("tools_tokens", 0), "magenta"),
        ]

        if show_bar:
            for name, tokens, color in components:
                if tokens > 0:
                    bar_length = int((tokens / total) * 40)
                    bar = "█" * bar_length + "░" * (40 - bar_length)
                    percentage = tokens / total * 100
                    self.console.print(
                        f"[{color}]{name:<20} {bar}  {tokens:>6,} tok ({percentage:>5.1f}%)[/{color}]"
                    )
        else:
            table = Table(show_header=True)
            table.add_column("Component", style="bold")
            table.add_column("Tokens", justify="right")
            table.add_column("Percentage", justify="right")

            for name, tokens, color in components:
                if tokens > 0:
                    percentage = tokens / total * 100
                    table.add_row(
                        name,
                        f"[{color}]{tokens:,}[/{color}]",
                        f"{percentage:.1f}%"
                    )

            self.console.print(table)

        # Summary line
        self.console.print(f"\n[bold]Total: {total:,} tokens[/bold]")

    def render_redundancy_analysis(
        self,
        structures: List[PromptStructure]
    ):
        """
        渲染冗余分析

        Args:
            structures: List of all PromptStructure objects
        """
        self.console.print("\n[bold cyan]═══ Redundancy Analysis ═══[/bold cyan]\n")

        if not structures:
            return

        # Calculate metrics
        avg_repeated = sum(s.stats.get("repeated_ratio", 0) for s in structures) / len(structures)
        avg_unique = sum(s.stats.get("unique_tokens", 0) for s in structures) / len(structures)

        # History growth rate
        history_growth = self._calculate_history_growth(structures)

        # Display metrics
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row(
            "Average repeated ratio:",
            self._format_repeated_ratio(avg_repeated, show_warning=True)
        )
        table.add_row(
            "Unique tokens per turn:",
            f"[green]~{avg_unique:.0f} tokens[/green]"
        )
        table.add_row(
            "History growth rate:",
            f"[yellow]+{history_growth:.0f} tokens/turn[/yellow]"
        )

        self.console.print(table)

        # Optimization suggestions
        suggestions = self._generate_suggestions(structures, avg_repeated, history_growth)
        if suggestions:
            self.console.print("\n[bold]💡 Optimization Suggestions:[/bold]")
            for i, suggestion in enumerate(suggestions, 1):
                self.console.print(f"  {i}. {suggestion}")

    def render_cost_analysis(
        self,
        structures: List[PromptStructure],
        pricing: Optional[Dict[str, float]] = None
    ):
        """
        渲染成本分析

        Args:
            structures: List of PromptStructure objects
            pricing: Pricing dict {"input_per_1k": 0.001, "output_per_1k": 0.002}
        """
        self.console.print("\n[bold cyan]═══ Cost Analysis ═══[/bold cyan]\n")

        # Use default Gemini pricing if not provided
        if pricing is None:
            pricing = {
                "input_per_1k": 0.00025,   # Gemini Pro pricing (example)
                "output_per_1k": 0.0005     # Gemini Pro pricing (example)
            }

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Turn", justify="right", style="cyan")
        table.add_column("Input Tok", justify="right")
        table.add_column("Output Tok", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("Cumulative", justify="right", style="yellow")

        cumulative_cost = 0

        for structure in structures:
            input_tokens = structure.total_tokens
            # Estimate output tokens (would need actual response data)
            output_tokens = structure.stats.get("output_tokens", input_tokens // 10)

            cost = (
                (input_tokens / 1000) * pricing["input_per_1k"] +
                (output_tokens / 1000) * pricing["output_per_1k"]
            )
            cumulative_cost += cost

            table.add_row(
                str(structure.turn_index),
                f"{input_tokens:,}",
                f"{output_tokens:,}",
                f"${cost:.4f}",
                f"${cumulative_cost:.4f}"
            )

        self.console.print(table)

        # Cost trend analysis
        if len(structures) > 1:
            first_cost = (
                (structures[0].total_tokens / 1000) * pricing["input_per_1k"]
            )
            last_cost = (
                (structures[-1].total_tokens / 1000) * pricing["input_per_1k"]
            )
            increase = (last_cost / first_cost - 1) * 100 if first_cost > 0 else 0

            self.console.print()
            if increase > 50:
                self.console.print(
                    f"[red]⚠ Cost per turn increasing by ~{increase:.0f}% (due to history growth)[/red]"
                )
            elif increase > 20:
                self.console.print(
                    f"[yellow]⚠ Cost per turn increasing by ~{increase:.0f}%[/yellow]"
                )

    def render_turn_table(
        self,
        structures: List[PromptStructure]
    ):
        """
        渲染 turn-by-turn 表格

        Args:
            structures: List of PromptStructure objects
        """
        self.console.print("\n[bold cyan]═══ Turn-by-Turn Statistics ═══[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Turn", justify="right", style="cyan")
        table.add_column("Total Tokens", justify="right")
        table.add_column("New Tokens", justify="right", style="green")
        table.add_column("Repeated %", justify="right")
        table.add_column("Components", justify="right", width=10)
        
        # 如果有意图分析，添加意图列
        has_intent_analysis = any(
            hasattr(s, 'intent_analysis') and s.intent_analysis is not None 
            for s in structures
        )
        
        if has_intent_analysis:
            table.add_column("Primary Intent", width=15)
            table.add_column("Confidence", justify="right", width=10)
            table.add_column("Complexity", justify="right", width=10)

        for structure in structures:
            stats = structure.stats
            repeated_ratio = stats.get("repeated_ratio", 0) * 100

            # Color code repeated ratio
            if repeated_ratio > 90:
                repeated_str = f"[red]{repeated_ratio:.1f}%[/red]"
            elif repeated_ratio > 70:
                repeated_str = f"[yellow]{repeated_ratio:.1f}%[/yellow]"
            else:
                repeated_str = f"[green]{repeated_ratio:.1f}%[/green]"
            
            row_data = [
                str(structure.turn_index),
                f"{structure.total_tokens:,}",
                f"{stats.get('unique_tokens', 0):,}",
                repeated_str,
                f"{len(structure.components)}"
            ]
            
            # 添加意图分析信息
            if has_intent_analysis and hasattr(structure, 'intent_analysis') and structure.intent_analysis:
                intent_type = structure.intent_analysis.primary_intent.value.replace('_', ' ').title()
                confidence = f"{structure.intent_analysis.intent_confidence:.2f}"
                complexity = f"{structure.intent_analysis.complexity_score:.2f}"
                
                # 根据置信度设置颜色
                confidence_color = "green" if structure.intent_analysis.intent_confidence > 0.8 else "yellow" if structure.intent_analysis.intent_confidence > 0.6 else "red"
                
                row_data.extend([
                    f"[cyan]{intent_type}[/cyan]",
                    f"[{confidence_color}]{confidence}[/{confidence_color}]",
                    f"[yellow]{complexity}[/yellow]"
                ])
            elif has_intent_analysis:
                row_data.extend(["[dim]N/A[/dim]", "[dim]N/A[/dim]", "[dim]N/A[/dim]"])
            
            table.add_row(*row_data)

        self.console.print(table)

    def _format_repeated_ratio(
        self,
        ratio: float,
        show_warning: bool = False
    ) -> str:
        """格式化重复率"""
        percentage = ratio * 100

        if show_warning:
            if percentage > 90:
                return f"[red]{percentage:.1f}% (❗ High)[/red]"
            elif percentage > 70:
                return f"[yellow]{percentage:.1f}% (⚠ Moderate)[/yellow]"
            else:
                return f"[green]{percentage:.1f}% (✓ Good)[/green]"
        else:
            return f"{percentage:.1f}%"

    def _calculate_history_growth(
        self,
        structures: List[PromptStructure]
    ) -> float:
        """计算历史对话增长速率"""
        if len(structures) < 2:
            return 0

        history_tokens = [
            s.stats.get("history_tokens", 0)
            for s in structures
        ]

        # Calculate average growth
        growth_rates = []
        for i in range(1, len(history_tokens)):
            growth = history_tokens[i] - history_tokens[i - 1]
            growth_rates.append(growth)

        return sum(growth_rates) / len(growth_rates) if growth_rates else 0

    def _generate_suggestions(
        self,
        structures: List[PromptStructure],
        avg_repeated: float,
        history_growth: float
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []

        # High redundancy
        if avg_repeated > 0.90:
            savings = self._estimate_savings(structures, 5)
            suggestions.append(
                f"Consider using conversation summarization (avg {avg_repeated*100:.1f}% redundancy)"
            )
            suggestions.append(
                f"Limit history to last 5 turns to save ~{savings:.0f}% tokens"
            )

        # Fast history growth
        if history_growth > 200:
            suggestions.append(
                f"History growing at {history_growth:.0f} tokens/turn - implement sliding window"
            )

        # System prompt repetition
        if len(structures) > 0:
            system_tokens = structures[0].stats.get("system_tokens", 0)
            if system_tokens > 100:
                total_system = system_tokens * len(structures)
                suggestions.append(
                    f"System prompt ({system_tokens} tokens) repeated every turn - "
                    f"use API caching to save {total_system:,} tokens"
                )

        return suggestions

    def _estimate_savings(
        self,
        structures: List[PromptStructure],
        history_limit: int
    ) -> float:
        """估算限制历史长度后的节省比例"""
        if len(structures) < history_limit:
            return 0

        # Calculate total tokens in all history
        total_history = sum(s.stats.get("history_tokens", 0) for s in structures)

        # Estimate tokens if we only keep last N turns
        # This is a rough estimate
        avg_turn_size = total_history / len(structures) if len(structures) > 0 else 0
        estimated_limited = avg_turn_size * history_limit * len(structures)

        savings = (total_history - estimated_limited) / total_history * 100 if total_history > 0 else 0
        return max(0, savings)

    def render_intent_analysis(
        self,
        structures: List[PromptStructure],
        show_details: bool = True
    ):
        """
        渲染意图分析统计

        Args:
            structures: List of PromptStructure objects with intent_analysis
            show_details: Whether to show detailed intent unit breakdown
        """
        self.console.print("\n[bold cyan]═══ Intent Analysis Statistics ═══[/bold cyan]\n")

        # 筛选出包含意图分析的结构
        structures_with_intent = [
            s for s in structures 
            if hasattr(s, 'intent_analysis') and s.intent_analysis is not None
        ]

        if not structures_with_intent:
            self.console.print("[dim]No intent analysis data available[/dim]")
            return

        # 统计意图分布
        intent_counts = {}
        total_confidence = 0
        total_complexity = 0
        total_intent_units = 0

        for structure in structures_with_intent:
            intent_analysis = structure.intent_analysis
            primary_intent = intent_analysis.primary_intent.value
            
            intent_counts[primary_intent] = intent_counts.get(primary_intent, 0) + 1
            total_confidence += intent_analysis.intent_confidence
            total_complexity += intent_analysis.complexity_score
            total_intent_units += len(intent_analysis.intent_units)

        # 显示意图分布
        self.console.print("[bold]Intent Distribution:[/bold]")
        intent_table = Table(show_header=True, header_style="bold magenta")
        intent_table.add_column("Intent Type", style="cyan")
        intent_table.add_column("Count", justify="right")
        intent_table.add_column("Percentage", justify="right")

        total_turns = len(structures_with_intent)
        for intent_type, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_turns * 100
            intent_table.add_row(
                intent_type.replace("_", " ").title(),
                f"{count}",
                f"{percentage:.1f}%"
            )

        self.console.print(intent_table)

        # 显示总体统计
        self.console.print("\n[bold]Overall Statistics:[/bold]")
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_row("Total Turns with Intent:", f"[cyan]{total_turns}[/cyan]")
        stats_table.add_row("Average Confidence:", f"[green]{total_confidence/total_turns:.2f}[/green]")
        stats_table.add_row("Average Complexity:", f"[yellow]{total_complexity/total_turns:.2f}[/yellow]")
        stats_table.add_row("Total Intent Units:", f"[magenta]{total_intent_units}[/magenta]")
        stats_table.add_row("Avg Units per Turn:", f"[blue]{total_intent_units/total_turns:.1f}[/blue]")
        
        self.console.print(stats_table)

        # 显示详细信息
        if show_details and structures_with_intent:
            self.console.print("\n[bold]Recent Intent Details:[/bold]")
            recent_structures = structures_with_intent[-3:]  # 显示最近3轮
            
            for structure in recent_structures:
                intent_analysis = structure.intent_analysis
                turn_index = structure.turn_index
                
                self.console.print(f"\n[dim]Turn {turn_index}:[/dim]")
                self.console.print(
                    f"  Primary: [cyan]{intent_analysis.primary_intent.value.replace('_', ' ').title()}[/cyan] "
                    f"(confidence: [green]{intent_analysis.intent_confidence:.2f}[/green])"
                )
                self.console.print(
                    f"  Complexity: [yellow]{intent_analysis.complexity_score:.2f}[/yellow], "
                    f"Units: [magenta]{len(intent_analysis.intent_units)}[/magenta]"
                )
                
                # 显示意图单元详情
                if intent_analysis.intent_units:
                    for i, unit in enumerate(intent_analysis.intent_units[:2], 1):  # 显示前2个单元
                        self.console.print(
                             f"    {i}. [dim]{unit.intent_type.value.replace('_', ' ').title()}[/dim] "
                             f"- {unit.content[:50]}{'...' if len(unit.content) > 50 else ''}"
                         )

    def render_intent_flow_stats(
        self,
        structures: List[PromptStructure],
        diff_engine=None
    ):
        """
        渲染意图流统计

        Args:
            structures: List of PromptStructure objects with intent_analysis
            diff_engine: Optional DiffEngine instance for computing intent flow
        """
        self.console.print("\n[bold cyan]═══ Intent Flow Statistics ═══[/bold cyan]\n")

        # 筛选出包含意图分析的结构
        structures_with_intent = [
            s for s in structures 
            if hasattr(s, 'intent_analysis') and s.intent_analysis is not None
        ]

        if len(structures_with_intent) < 2:
            self.console.print("[dim]Need at least 2 turns with intent analysis for flow statistics[/dim]")
            return

        # 如果没有提供diff_engine，创建一个简单的流分析
        if diff_engine is None:
            self._render_simple_intent_flow(structures_with_intent)
        else:
            self._render_enhanced_intent_flow(structures_with_intent, diff_engine)

    def _render_simple_intent_flow(self, structures_with_intent: List):
        """渲染简单的意图流统计"""
        # 构建意图序列
        intent_sequence = [
            s.intent_analysis.primary_intent.value 
            for s in structures_with_intent
        ]

        # 计算转换统计
        transitions = {}
        for i in range(len(intent_sequence) - 1):
            from_intent = intent_sequence[i]
            to_intent = intent_sequence[i + 1]
            key = f"{from_intent} → {to_intent}"
            transitions[key] = transitions.get(key, 0) + 1

        # 显示转换矩阵
        self.console.print("[bold]Intent Transitions:[/bold]")
        if transitions:
            trans_table = Table(show_header=True, header_style="bold magenta")
            trans_table.add_column("Transition", style="cyan")
            trans_table.add_column("Count", justify="right")
            trans_table.add_column("Frequency", justify="right")

            total_transitions = sum(transitions.values())
            for trans, count in sorted(transitions.items(), key=lambda x: x[1], reverse=True):
                frequency = count / total_transitions * 100
                trans_table.add_row(
                    trans.replace("_", " ").title(),
                    f"{count}",
                    f"{frequency:.1f}%"
                )

            self.console.print(trans_table)
        else:
            self.console.print("[dim]No transitions found[/dim]")

        # 显示意图稳定性分析
        self.console.print("\n[bold]Intent Stability Analysis:[/bold]")
        
        # 计算意图变化次数
        intent_changes = sum(
            1 for i in range(len(intent_sequence) - 1)
            if intent_sequence[i] != intent_sequence[i + 1]
        )
        
        stability = (len(intent_sequence) - 1 - intent_changes) / (len(intent_sequence) - 1) * 100 if len(intent_sequence) > 1 else 100
        
        stability_color = "green" if stability > 70 else "yellow" if stability > 40 else "red"
        self.console.print(f"  Intent Stability: [{stability_color}]{stability:.1f}%[/{stability_color}]")
        self.console.print(f"  Total Changes: [cyan]{intent_changes}[/cyan]")
        self.console.print(f"  Sequence Length: [blue]{len(intent_sequence)}[/blue]")

        # 显示最常见的意图
        from collections import Counter
        intent_counter = Counter(intent_sequence)
        most_common = intent_counter.most_common(3)
        
        self.console.print("\n[bold]Top Intents:[/bold]")
        for intent, count in most_common:
            percentage = count / len(intent_sequence) * 100
            self.console.print(f"  {intent.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")

    def _render_enhanced_intent_flow(self, structures_with_intent: List, diff_engine):
        """使用DiffEngine渲染增强的意图流统计"""
        try:
            # 使用diff_engine计算意图流
            intent_flow = diff_engine.compute_intent_flow(structures_with_intent)
            
            if intent_flow and intent_flow.get("transitions"):
                self.console.print("[bold]Enhanced Intent Flow Analysis:[/bold]")
                
                # 显示转换矩阵
                transitions = intent_flow["transitions"]
                if transitions:
                    trans_table = Table(show_header=True, header_style="bold magenta")
                    trans_table.add_column("From Intent", style="cyan")
                    trans_table.add_column("To Intent", style="green")
                    trans_table.add_column("Count", justify="right")
                    
                    for from_intent, to_dict in transitions.items():
                        for to_intent, count in to_dict.items():
                            trans_table.add_row(
                                from_intent.value.replace("_", " ").title(),
                                to_intent.value.replace("_", " ").title(),
                                f"{count}"
                            )
                    
                    self.console.print(trans_table)
                
                # 显示流统计
                flow_stats = intent_flow.get("flow_statistics", {})
                if flow_stats:
                    self.console.print("\n[bold]Flow Statistics:[/bold]")
                    stats_table = Table(show_header=False, box=None, padding=(0, 2))
                    
                    if "total_transitions" in flow_stats:
                        stats_table.add_row("Total Transitions:", f"[cyan]{flow_stats['total_transitions']}[/cyan]")
                    
                    if "unique_patterns" in flow_stats:
                        stats_table.add_row("Unique Patterns:", f"[magenta]{flow_stats['unique_patterns']}[/magenta]")
                    
                    if "avg_confidence_stability" in flow_stats:
                        stability = flow_stats['avg_confidence_stability']
                        stability_color = "green" if stability > 0.8 else "yellow" if stability > 0.5 else "red"
                        stats_table.add_row("Confidence Stability:", f"[{stability_color}]{stability:.2f}[/{stability_color}]")
                    
                    if "complexity_trend" in flow_stats:
                        trend = flow_stats['complexity_trend']
                        trend_symbol = "↗" if trend > 0.1 else "↘" if trend < -0.1 else "→"
                        trend_color = "green" if trend > 0.1 else "red" if trend < -0.1 else "yellow"
                        stats_table.add_row("Complexity Trend:", f"[{trend_color}]{trend_symbol} {trend:.3f}[/{trend_color}]")
                    
                    self.console.print(stats_table)
                
                # 显示检测到的模式
                patterns = intent_flow.get("patterns", {})
                if patterns:
                    self.console.print("\n[bold]Detected Patterns:[/bold]")
                    pattern_list = list(patterns.items())[:5]  # 显示前5个模式
                    
                    for pattern_name, pattern_data in pattern_list:
                        if isinstance(pattern_data, dict) and "count" in pattern_data:
                            self.console.print(f"  {pattern_name}: {pattern_data['count']} occurrences")
                        else:
                            self.console.print(f"  {pattern_name}: {pattern_data}")
        
        except Exception as e:
            self.console.print(f"[dim]Enhanced intent flow analysis failed: {e}[/dim]")
            self._render_simple_intent_flow(structures_with_intent)

    def render_intent_patterns(
        self,
        structures: List[PromptStructure],
        min_pattern_length: int = 2
    ):
        """
        渲染意图模式分析

        Args:
            structures: List of PromptStructure objects with intent_analysis
            min_pattern_length: Minimum length of patterns to detect
        """
        self.console.print("\n[bold cyan]═══ Intent Pattern Analysis ═══[/bold cyan]\n")

        # 筛选出包含意图分析的结构
        structures_with_intent = [
            s for s in structures 
            if hasattr(s, 'intent_analysis') and s.intent_analysis is not None
        ]

        if len(structures_with_intent) < min_pattern_length:
            self.console.print(f"[dim]Need at least {min_pattern_length} turns with intent analysis for pattern detection[/dim]")
            return

        # 构建意图序列
        intent_sequence = [
            s.intent_analysis.primary_intent.value 
            for s in structures_with_intent
        ]

        # 分析意图模式
        patterns = self._detect_intent_patterns(intent_sequence, min_pattern_length)
        
        if patterns:
            self.console.print("[bold]Detected Intent Patterns:[/bold]")
            pattern_table = Table(show_header=True, header_style="bold magenta")
            pattern_table.add_column("Pattern", style="cyan")
            pattern_table.add_column("Count", justify="right")
            pattern_table.add_column("Frequency", justify="right")
            pattern_table.add_column("Coverage", justify="right")

            total_patterns = sum(patterns.values())
            sequence_length = len(intent_sequence)
            
            for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                frequency = count / total_patterns * 100
                coverage = (len(pattern.split(" → ")) * count) / sequence_length * 100
                
                pattern_table.add_row(
                    pattern.replace("_", " ").title(),
                    f"{count}",
                    f"{frequency:.1f}%",
                    f"{coverage:.1f}%"
                )

            self.console.print(pattern_table)
        else:
            self.console.print("[dim]No significant patterns detected[/dim]")

        # 显示会话特征
        self.console.print("\n[bold]Session Characteristics:[/bold]")
        
        # 计算意图多样性
        unique_intents = len(set(intent_sequence))
        diversity = unique_intents / len(intent_sequence)
        
        # 计算平均复杂度
        avg_complexity = sum(s.intent_analysis.complexity_score for s in structures_with_intent) / len(structures_with_intent)
        
        # 计算平均置信度
        avg_confidence = sum(s.intent_analysis.intent_confidence for s in structures_with_intent) / len(structures_with_intent)
        
        # 计算意图变化频率
        intent_changes = sum(
            1 for i in range(len(intent_sequence) - 1)
            if intent_sequence[i] != intent_sequence[i + 1]
        )
        change_rate = intent_changes / (len(intent_sequence) - 1) if len(intent_sequence) > 1 else 0

        # 显示特征表格
        char_table = Table(show_header=False, box=None, padding=(0, 2))
        
        diversity_color = "green" if diversity > 0.7 else "yellow" if diversity > 0.4 else "red"
        char_table.add_row("Intent Diversity:", f"[{diversity_color}]{diversity:.2f}[/{diversity_color}]")
        
        complexity_color = "green" if avg_complexity < 0.3 else "yellow" if avg_complexity < 0.7 else "red"
        char_table.add_row("Average Complexity:", f"[{complexity_color}]{avg_complexity:.2f}[/{complexity_color}]")
        
        confidence_color = "green" if avg_confidence > 0.8 else "yellow" if avg_confidence > 0.6 else "red"
        char_table.add_row("Average Confidence:", f"[{confidence_color}]{avg_confidence:.2f}[/{confidence_color}]")
        
        change_color = "green" if change_rate < 0.3 else "yellow" if change_rate < 0.6 else "red"
        char_table.add_row("Intent Change Rate:", f"[{change_color}]{change_rate:.2f}[/{change_color}]")
        
        char_table.add_row("Unique Intent Types:", f"[cyan]{unique_intents}[/cyan]")
        char_table.add_row("Total Turns:", f"[blue]{len(intent_sequence)}[/blue]")
        
        self.console.print(char_table)

        # 显示主导意图链
        self._render_dominant_intent_chain(intent_sequence)

    def _detect_intent_patterns(self, sequence: List[str], min_length: int) -> Dict[str, int]:
        """检测意图序列中的模式"""
        patterns = {}
        
        # 检测不同长度的模式
        for length in range(min_length, min(len(sequence) + 1, 6)):
            for i in range(len(sequence) - length + 1):
                pattern = " → ".join(sequence[i:i + length])
                patterns[pattern] = patterns.get(pattern, 0) + 1
        
        # 过滤掉只出现一次的模式
        return {pattern: count for pattern, count in patterns.items() if count > 1}

    def _render_dominant_intent_chain(self, intent_sequence: List[str]):
        """渲染主导意图链"""
        from collections import Counter
        
        intent_counter = Counter(intent_sequence)
        most_common_intents = intent_counter.most_common(3)
        
        if most_common_intents:
            self.console.print("\n[bold]Dominant Intent Chain:[/bold]")
            
            # 构建主导意图序列
            dominant_sequence = []
            for intent in intent_sequence:
                # 只保留最常见的意图
                if intent in [item[0] for item in most_common_intents[:2]]:
                    dominant_sequence.append(intent)
            
            # 简化序列，合并连续的相同意图
            simplified_chain = []
            current_intent = None
            count = 0
            
            for intent in dominant_sequence:
                if intent == current_intent:
                    count += 1
                else:
                    if current_intent is not None:
                        simplified_chain.append(f"{current_intent.replace('_', ' ').title()} ×{count}")
                    current_intent = intent
                    count = 1
            
            if current_intent is not None:
                simplified_chain.append(f"{current_intent.replace('_', ' ').title()} ×{count}")
            
            if simplified_chain:
                chain_str = " → ".join(simplified_chain)
                self.console.print(f"  {chain_str}")
            
            # 显示每个主导意图的详细信息
            self.console.print("\n[dim]Dominant Intent Details:[/dim]")
            for intent, count in most_common_intents:
                percentage = count / len(intent_sequence) * 100
                self.console.print(
                    f"  [cyan]{intent.replace('_', ' ').title()}[/cyan]: "
                    f"{count} occurrences ({percentage:.1f}%)"
                )

    def _format_intent_type(self, intent_type: IntentType) -> str:
        """格式化意图类型显示"""
        return intent_type.value.replace('_', ' ').title()

    def _get_confidence_color(self, confidence: float) -> str:
        """根据置信度返回颜色"""
        if confidence > 0.8:
            return "green"
        elif confidence > 0.6:
            return "yellow"
        else:
            return "red"

    def _get_complexity_color(self, complexity: float) -> str:
        """根据复杂度返回颜色"""
        if complexity < 0.3:
            return "green"
        elif complexity < 0.7:
            return "yellow"
        else:
            return "red"

    def _format_intent_summary(self, intent_analysis: TurnIntentAnalysis) -> str:
        """格式化意图分析摘要"""
        intent_type = self._format_intent_type(intent_analysis.primary_intent)
        confidence_color = self._get_confidence_color(intent_analysis.intent_confidence)
        complexity_color = self._get_complexity_color(intent_analysis.complexity_score)
        
        return (
            f"[cyan]{intent_type}[/cyan] | "
            f"[{confidence_color}]conf: {intent_analysis.intent_confidence:.2f}[/{confidence_color}] | "
            f"[{complexity_color}]comp: {intent_analysis.complexity_score:.2f}[/{complexity_color}]"
        )
