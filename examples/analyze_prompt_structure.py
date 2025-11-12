"""
Example: Analyzing Prompt Structure from Gemini CLI Capture

This script demonstrates how to use the PromptAnalyzer to analyze
captured Gemini CLI sessions and visualize prompt composition.

Usage:
    python examples/analyze_prompt_structure.py <capture_file.json>

Example:
    python examples/analyze_prompt_structure.py \\
        prompt_captures/gemini_cli/session_abc123.json
"""

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tigerhill.analyzer.prompt_analyzer import PromptAnalyzer
from tigerhill.analyzer.diff_engine import DiffEngine


def main():
    console = Console()

    # Parse arguments
    if len(sys.argv) < 2:
        console.print("[red]Error: No capture file specified[/red]")
        console.print("\nUsage: python analyze_prompt_structure.py <capture_file.json>")
        sys.exit(1)

    capture_file = Path(sys.argv[1])

    if not capture_file.exists():
        console.print(f"[red]Error: File not found: {capture_file}[/red]")
        sys.exit(1)

    # Load capture data
    console.print(f"\n[cyan]Loading capture file:[/cyan] {capture_file}")
    with open(capture_file) as f:
        data = json.load(f)

    session_id = data.get("session_id", "Unknown")
    console.print(f"[cyan]Session ID:[/cyan] {session_id[:20]}...")

    # Initialize analyzer
    analyzer = PromptAnalyzer(model_name="gemini-pro")

    # Analyze all turns
    console.print("\n[yellow]Analyzing prompt structures...[/yellow]")
    structures = analyzer.analyze_session(data)

    if not structures:
        console.print("[red]No turns found in capture file[/red]")
        sys.exit(1)

    console.print(f"[green]✓ Analyzed {len(structures)} turns[/green]\n")

    # Display overall statistics
    display_session_stats(console, structures, data)

    # Display turn-by-turn analysis
    display_turn_details(console, structures)

    # Compute and display diffs
    console.print("\n[bold cyan]═══ Prompt Structure Changes ═══[/bold cyan]\n")
    diff_engine = DiffEngine()
    diffs = diff_engine.compute_all_diffs(structures)

    for diff in diffs:
        display_diff_summary(console, diff, structures)


def display_session_stats(console, structures, session_data):
    """Display overall session statistics"""
    console.print("[bold cyan]═══ Session Statistics ═══[/bold cyan]\n")

    total_tokens = sum(s.total_tokens for s in structures)
    total_unique = sum(s.stats.get("unique_tokens", 0) for s in structures)
    avg_repeated = sum(s.stats.get("repeated_ratio", 0) for s in structures) / len(structures)

    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_row("Total Turns:", str(len(structures)))
    stats_table.add_row("Total Tokens:", f"{total_tokens:,}")
    stats_table.add_row("Unique Tokens:", f"{total_unique:,} ({total_unique/total_tokens*100:.1f}%)")
    stats_table.add_row("Avg Repeated:", f"{avg_repeated*100:.1f}%")

    console.print(stats_table)


def display_turn_details(console, structures):
    """Display detailed turn-by-turn analysis"""
    console.print("\n[bold cyan]═══ Turn-by-Turn Analysis ═══[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Turn", justify="right", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("System", justify="right")
    table.add_column("History", justify="right")
    table.add_column("New", justify="right", style="green")
    table.add_column("Tools", justify="right")
    table.add_column("Repeated %", justify="right")

    for structure in structures:
        stats = structure.stats
        table.add_row(
            str(structure.turn_index),
            f"{structure.total_tokens:,}",
            f"{stats.get('system_tokens', 0):,}",
            f"{stats.get('history_tokens', 0):,}",
            f"{stats.get('new_tokens', 0):,}",
            f"{stats.get('tools_tokens', 0):,}",
            f"{stats.get('repeated_ratio', 0)*100:.1f}%"
        )

    console.print(table)


def display_diff_summary(console, diff, structures):
    """Display diff summary for a turn"""
    from_structure = structures[diff.from_turn - 1]
    to_structure = structures[diff.to_turn - 1]

    console.print(f"[bold]Turn {diff.from_turn} → {diff.to_turn}[/bold]")

    if diff.total_changes == 0:
        console.print("  [dim]No changes[/dim]")
    else:
        if diff.added_components:
            console.print(f"  [green]+ Added: {len(diff.added_components)} components ({diff.added_tokens} tokens)[/green]")
            for comp in diff.added_components:
                preview = comp.content[:50] + "..." if len(comp.content) > 50 else comp.content
                console.print(f"    • {comp.type.value}: {preview}")

        if diff.removed_components:
            console.print(f"  [red]- Removed: {len(diff.removed_components)} components ({diff.removed_tokens} tokens)[/red]")

        if diff.modified_components:
            console.print(f"  [yellow]~ Modified: {len(diff.modified_components)} components[/yellow]")

    # Show summary stats
    new_ratio = diff.added_tokens / to_structure.total_tokens if to_structure.total_tokens > 0 else 0
    console.print(f"  [dim]Delta: {diff.added_tokens} new / {to_structure.total_tokens} total ({new_ratio*100:.1f}%)[/dim]")
    console.print()


if __name__ == "__main__":
    main()
