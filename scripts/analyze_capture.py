#!/usr/bin/env python3
"""
Analyze a TigerHill capture JSON and print the PromptAnalyzer report.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tigerhill.observer import PromptAnalyzer


def find_latest_capture(search_root: str) -> Optional[str]:
    pattern = os.path.join(search_root, "**", "capture_*.json")
    candidates = glob.glob(pattern, recursive=True)
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def resolve_capture_path(target: Optional[str]) -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if not target:
        default_root = os.path.join(repo_root, "prompt_captures")
        latest = find_latest_capture(default_root)
        if not latest:
            raise FileNotFoundError(
                f"No capture_*.json found under {default_root}. Provide a path explicitly."
            )
        return latest

    candidate = os.path.abspath(target)
    if os.path.isdir(candidate):
        latest = find_latest_capture(candidate)
        if not latest:
            raise FileNotFoundError(f"No capture_*.json found in directory: {candidate}")
        return latest

    if not os.path.isfile(candidate):
        raise FileNotFoundError(f"Capture file not found: {candidate}")

    return candidate


def load_capture(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run PromptAnalyzer on a TigerHill capture JSON file."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Capture file or directory. If omitted, uses the latest capture under prompt_captures/.",
    )
    args = parser.parse_args()

    try:
        capture_path = resolve_capture_path(args.path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    data = load_capture(capture_path)
    analyzer = PromptAnalyzer(data)
    report = analyzer.analyze_all()

    print(f"=== PromptAnalyzer Report ===")
    print(f"Capture file: {capture_path}")
    print(f"Agent: {data.get('agent_name', 'unknown')}")
    print(f"Requests: {len(data.get('requests', []))}")
    print(f"Responses: {len(data.get('responses', []))}")
    print()

    analyzer.print_report(report)


if __name__ == "__main__":
    main()
