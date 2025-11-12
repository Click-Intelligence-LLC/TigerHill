"""
Example: Complete LLM Interaction Visualization

This script demonstrates the full visualization capabilities for
analyzing Gemini CLI captures, including:
- Prompt structure analysis
- Diff view (incremental changes)
- Statistics view (token/cost analysis)
- Optimization suggestions

Usage:
    python examples/visualize_llm_interaction.py <capture_file.json> [options]

Options:
    --mode {diff,stats,both}   Visualization mode (default: both)
    --show-unchanged           Show unchanged components in diff view
    --turn N                   Focus on specific turn

Examples:
    # Full analysis
    python examples/visualize_llm_interaction.py session_abc123.json

    # Only diff view
    python examples/visualize_llm_interaction.py session_abc123.json --mode diff

    # Only statistics
    python examples/visualize_llm_interaction.py session_abc123.json --mode stats

    # Show specific turn with unchanged components
    python examples/visualize_llm_interaction.py session_abc123.json --turn 5 --show-unchanged

    # Intent analysis
    python examples/visualize_llm_interaction.py session_abc123.json --intent-analysis

    # Intent flow analysis
    python examples/visualize_llm_interaction.py session_abc123.json --intent-flow

    # Combined analysis with intent
    python examples/visualize_llm_interaction.py session_abc123.json --mode both --intent-analysis --intent-flow
"""

import sys
import json
import argparse
from pathlib import Path
from rich.console import Console

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tigerhill.analyzer.prompt_analyzer import PromptAnalyzer
from tigerhill.analyzer.diff_engine import DiffEngine
from tigerhill.visualization.diff_view import DiffView
from tigerhill.visualization.stats_view import StatsView


def main():
    parser = argparse.ArgumentParser(
        description="Visualize LLM interaction from Gemini CLI capture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "capture_file",
        type=str,
        help="Path to capture file (JSON)"
    )

    parser.add_argument(
        "--mode",
        choices=["diff", "stats", "both"],
        default="both",
        help="Visualization mode (default: both)"
    )

    parser.add_argument(
        "--show-unchanged",
        action="store_true",
        help="Show unchanged components in diff view"
    )

    parser.add_argument(
        "--turn",
        type=int,
        help="Focus on specific turn"
    )

    parser.add_argument(
        "--no-content",
        action="store_true",
        help="Hide component content (show only summaries)"
    )

    parser.add_argument(
        "--intent-analysis",
        action="store_true",
        help="Enable intent analysis visualization"
    )

    parser.add_argument(
        "--intent-flow",
        action="store_true",
        help="Show intent flow analysis"
    )

    parser.add_argument(
        "--intent-patterns",
        action="store_true",
        help="Show intent pattern analysis"
    )

    args = parser.parse_args()

    # Initialize console
    console = Console()

    # Load capture file
    capture_file = Path(args.capture_file)

    if not capture_file.exists():
        console.print(f"[red]Error: File not found: {capture_file}[/red]")
        sys.exit(1)

    console.print(f"\n[cyan]Loading capture file:[/cyan] {capture_file}")
    with open(capture_file) as f:
        data = json.load(f)

    session_id = data.get("session_id", "Unknown")
    console.print(f"[cyan]Session ID:[/cyan] {session_id[:20]}...\n")

    # Initialize tools
    analyzer = PromptAnalyzer(model_name="gemini-pro")
    diff_engine = DiffEngine()
    diff_view = DiffView(console=console)
    stats_view = StatsView(console=console)

    # Analyze all turns
    console.print("[yellow]Analyzing prompt structures...[/yellow]")
    structures = analyzer.analyze_session(data)

    if not structures:
        console.print("[red]No turns found in capture file[/red]")
        sys.exit(1)

    console.print(f"[green]✓ Analyzed {len(structures)} turns[/green]")

    # Check if we have any actual data
    total_tokens = sum(s.total_tokens for s in structures)
    if total_tokens == 0:
        console.print("\n[yellow]⚠ Warning: This capture has 0 tokens[/yellow]")
        console.print("[dim]This usually means:[/dim]")
        console.print("[dim]  1. The session was interrupted or failed[/dim]")
        console.print("[dim]  2. The interceptor didn't capture the request body[/dim]")
        console.print("[dim]  3. The capture file is incomplete/malformed[/dim]")
        console.print("\n[yellow]Statistics will show limited information.[/yellow]\n")

    # Process based on mode
    if args.mode in ["stats", "both"]:
        render_statistics(
            console,
            stats_view,
            structures,
            data,
            specific_turn=args.turn
        )

    if args.mode in ["diff", "both"]:
        render_diff_analysis(
            console,
            diff_view,
            diff_engine,
            structures,
            session_data=data,
            show_unchanged=args.show_unchanged,
            show_content=not args.no_content,
            specific_turn=args.turn
        )
    
    # 意图分析模式
    if args.intent_analysis:
        render_intent_analysis(
            console,
            structures,
            specific_turn=args.turn
        )
    
    if args.intent_flow:
        render_intent_flow(
            console,
            diff_engine,
            structures
        )
    
    if args.intent_patterns:
        render_intent_patterns(
            console,
            stats_view,
            structures
        )


def render_statistics(
    console,
    stats_view,
    structures,
    session_data,
    specific_turn=None
):
    """Render statistics views"""
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]STATISTICS VIEW[/bold cyan]")
    console.print("=" * 70)

    # Session-level statistics
    stats_view.render_session_stats(structures, session_data)

    # Turn-by-turn table
    stats_view.render_turn_table(structures)

    # Token distribution for specific turn or last turn
    if specific_turn:
        if specific_turn <= len(structures):
            stats_view.render_token_distribution(structures[specific_turn - 1])
        else:
            console.print(f"[red]Turn {specific_turn} does not exist[/red]")
    else:
        # Show last turn distribution
        stats_view.render_token_distribution(structures[-1])

    # Redundancy analysis
    stats_view.render_redundancy_analysis(structures)

    # Cost analysis
    stats_view.render_cost_analysis(structures)


def render_intent_analysis(
    console,
    structures,
    specific_turn=None
):
    """Render intent analysis results"""
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]INTENT ANALYSIS[/bold cyan]")
    console.print("=" * 70)
    
    # 过滤需要显示的轮次
    if specific_turn:
        if specific_turn <= len(structures):
            structures = [structures[specific_turn - 1]]
        else:
            console.print(f"[red]Turn {specific_turn} does not exist[/red]")
            return
    
    # 显示每个轮次的意图分析
    for i, structure in enumerate(structures):
        if not structure.intent_analysis:
            console.print(f"[yellow]Turn {i+1}: No intent analysis available[/yellow]")
            continue
            
        intent_analysis = structure.intent_analysis
        
        console.print(f"\n[bold]Turn {intent_analysis.turn_index + 1}:[/bold]")
        
        # 主要意图信息
        console.print(f"  [cyan]Primary Intent:[/cyan] {intent_analysis.primary_intent.value}")
        console.print(f"  [cyan]Confidence:[/cyan] {intent_analysis.intent_confidence:.2f}")
        console.print(f"  [cyan]Complexity Score:[/cyan] {intent_analysis.complexity_score:.2f}")
        console.print(f"  [cyan]Total Tokens:[/cyan] {intent_analysis.total_tokens}")
        console.print(f"  [cyan]Intent Diversity:[/cyan] {intent_analysis.intent_diversity:.2f}")
        
        # 意图单元详情
        if intent_analysis.intent_units:
            console.print(f"  [cyan]Intent Units:[/cyan] {len(intent_analysis.intent_units)}")
            for j, unit in enumerate(intent_analysis.intent_units):
                console.print(f"    [dim]{j+1}.[/dim] [yellow]{unit.intent_type.value}[/yellow] "
                            f"(confidence: {unit.confidence:.2f}, tokens: {unit.tokens})")
                console.print(f"       [dim]Content:[/dim] {unit.content[:60]}...")
                if unit.keywords:
                    console.print(f"       [dim]Keywords:[/dim] {', '.join(unit.keywords)}")
                if unit.context_dependencies:
                    console.print(f"       [dim]Dependencies:[/dim] {', '.join(unit.context_dependencies)}")
        
        # 上下文引用
        if intent_analysis.context_references:
            console.print(f"  [cyan]Context References:[/cyan] {intent_analysis.context_references}")


def render_intent_flow(
    console,
    diff_engine,
    structures
):
    """Render intent flow analysis"""
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]INTENT FLOW ANALYSIS[/bold cyan]")
    console.print("=" * 70)
    
    # 计算意图流
    if len(structures) < 2:
        console.print("[yellow]Need at least 2 turns for intent flow analysis[/yellow]")
        return
    
    # 提取意图分析数据
    intent_analyses = [s.intent_analysis for s in structures if s.intent_analysis]
    
    if len(intent_analyses) < 2:
        console.print("[yellow]Not enough intent analysis data for flow analysis[/yellow]")
        return
    
    # 使用diff_engine计算意图流
    flow_result = diff_engine.compute_intent_flow(structures)
    
    if not flow_result:
        console.print("[yellow]No intent flow data available[/yellow]")
        return
    
    # 显示转换矩阵
    if flow_result.get("transition_matrix"):
        console.print("\n[bold]Intent Transition Matrix:[/bold]")
        matrix = flow_result["transition_matrix"]
        for from_intent, transitions in matrix.items():
            console.print(f"\n[yellow]{from_intent}:[/yellow]")
            for to_intent, count in transitions.items():
                if count > 0:
                    console.print(f"  → {to_intent}: {count}")
    
    # 显示转换模式
    if flow_result.get("transition_patterns"):
        console.print("\n[bold]Transition Patterns:[/bold]")
        patterns = flow_result["transition_patterns"]
        pattern_list = []
        for pattern_type, pattern_data in patterns.items():
            if pattern_data.get("transitions"):
                pattern_list.append({
                    'type': pattern_type,
                    'count': pattern_data['count'],
                    'avg_confidence_change': pattern_data.get('average_confidence_change', 0)
                })
        
        # 按count排序并显示前5个
        pattern_list.sort(key=lambda x: x['count'], reverse=True)
        for pattern in pattern_list[:5]:
            console.print(f"  [cyan]{pattern['type']}:[/cyan] "
                        f"{pattern['count']} times, "
                        f"avg confidence change: {pattern['avg_confidence_change']:+.3f}")
    
    # 显示统计信息
    if flow_result.get("statistics"):
        stats = flow_result["statistics"]
        console.print("\n[bold]Flow Statistics:[/bold]")
        console.print(f"  Total Transitions: {stats.get('total_transitions', 0)}")
        console.print(f"  Unique Patterns: {stats.get('unique_patterns', 0)}")
        console.print(f"  Avg Confidence Stability: {stats.get('avg_confidence_stability', 0):.3f}")
        console.print(f"  Complexity Trend: {stats.get('complexity_trend', 'unknown')}")
    
    # 显示详细流分析
    if flow_result.get("detailed_analysis"):
        analysis = flow_result["detailed_analysis"]
        console.print("\n[bold]Detailed Flow Analysis:[/bold]")
        
        if analysis.get("confidence_stability"):
            conf_stability = analysis["confidence_stability"]
            console.print(f"  Confidence Stability: {conf_stability.get('stability_score', 0):.3f}")
            console.print(f"  Stability Trend: {conf_stability.get('trend', 'unknown')}")
        
        if analysis.get("complexity_trend"):
            complexity = analysis["complexity_trend"]
            console.print(f"  Complexity Trend: {complexity.get('trend', 'unknown')}")
            console.print(f"  Avg Complexity Change: {complexity.get('avg_change', 0):+.3f}")
        
        if analysis.get("flow_quality_score"):
            console.print(f"  Flow Quality Score: {analysis['flow_quality_score']:.3f}")


def render_intent_patterns(
    console,
    stats_view,
    structures
):
    """Render intent pattern analysis"""
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]INTENT PATTERN ANALYSIS[/bold cyan]")
    console.print("=" * 70)
    
    # 使用stats_view的render_intent_patterns方法
    stats_view.render_intent_patterns(structures)


def render_diff_analysis(
    console,
    diff_view,
    diff_engine,
    structures,
    session_data=None,
    show_unchanged=False,
    show_content=True,
    specific_turn=None
):
    """Render diff views"""
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]DIFF VIEW[/bold cyan]")
    console.print("=" * 70)

    # Compute diffs
    diffs = diff_engine.compute_all_diffs(structures)

    if specific_turn:
        # Show diff for specific turn
        if specific_turn > 1 and specific_turn <= len(structures):
            diff = diffs[specific_turn - 2]  # diffs are 0-indexed, turns are 1-indexed
            from_structure = structures[specific_turn - 2]
            to_structure = structures[specific_turn - 1]

            diff_view.render(
                diff,
                from_structure,
                to_structure,
                show_unchanged=show_unchanged,
                show_content=show_content
            )
        else:
            console.print(f"[red]Cannot show diff for turn {specific_turn}[/red]")
            console.print("[yellow]Diff is only available for turns 2 and above[/yellow]")
    else:
        # Show all diffs
        # 创建LLMSession对象用于render_all_diffs
        session_data_dict = {
            "session_id": session_data.get("session_id", "unknown") if session_data else "unknown",
            "turns": structures,
            "total_tokens": sum(s.total_tokens for s in structures),
            "start_time": session_data.get("start_time", "") if session_data else "",
            "end_time": session_data.get("end_time", "") if session_data else ""
        }
        
        # 创建LLMSession实例
        from tigerhill.visualization.diff_view import LLMSession
        session = LLMSession(
            session_id=session_data_dict["session_id"],
            turns=session_data_dict["turns"],
            total_tokens=session_data_dict["total_tokens"],
            start_time=session_data_dict["start_time"],
            end_time=session_data_dict["end_time"]
        )
        
        diff_view.render_all_diffs(
            session,
            show_unchanged=show_unchanged,
            show_intent_diffs=False
        )


if __name__ == "__main__":
    main()
