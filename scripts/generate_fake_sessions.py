#!/usr/bin/env python3
"""
Generate synthetic Gemini CLI session captures for importer benchmarking.

Example:
    python scripts/generate_fake_sessions.py --count 1000 --output /tmp/captures
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from backend.testing.factories import build_session_payload, PROVIDER_CONFIG


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate fake session JSON captures.")
    parser.add_argument("--count", type=int, default=100, help="Number of sessions to generate.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory where JSON files will be written.",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=list(PROVIDER_CONFIG.keys()),
        help="Providers to cycle through when generating sessions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    providers: List[str] = args.providers or list(PROVIDER_CONFIG.keys())

    for idx in range(args.count):
        provider = providers[idx % len(providers)]
        payload = build_session_payload(provider=provider)
        target = args.output / f"{payload['session_id']}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {args.count} sessions in {args.output}")


if __name__ == "__main__":
    main()
