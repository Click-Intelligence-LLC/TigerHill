#!/usr/bin/env python3
"""
Verification helper for schema v2.
"""

from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "gemini_cli_dashboard_v2.db"


def verify():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    required_tables = [
        "sessions",
        "turns",
        "llm_requests",
        "prompt_components",
        "llm_responses",
        "response_spans",
    ]

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ({})".format(
            ",".join("?" for _ in required_tables)
        ),
        required_tables,
    )
    tables = {row["name"] for row in cursor.fetchall()}
    missing = set(required_tables) - tables
    if missing:
        raise SystemExit(f"Missing tables: {', '.join(sorted(missing))}")

    cursor = conn.execute("SELECT COUNT(*) as count FROM sessions")
    session_count = cursor.fetchone()["count"]

    print("✅ Schema verification complete.")
    print(f"Sessions stored: {session_count}")

    conn.close()


if __name__ == "__main__":
    verify()
