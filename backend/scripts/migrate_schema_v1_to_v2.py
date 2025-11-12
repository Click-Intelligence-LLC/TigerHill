#!/usr/bin/env python3
"""
Migration helper to move data from the legacy dashboard schema (v1)
to the new deep-decomposition schema (v2).

Usage:
    python backend/scripts/migrate_schema_v1_to_v2.py
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
OLD_DB = BASE_DIR / "gemini_cli_dashboard.db"
NEW_DB = BASE_DIR / "gemini_cli_dashboard_v2.db"
SCHEMA_FILE = BASE_DIR / "database" / "schema_v2.sql"
BACKUP_FILE = OLD_DB.with_suffix(".db.backup")

try:
    from backend.services.parsers import ProviderDetector
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(BASE_DIR.parent))
    from backend.services.parsers import ProviderDetector  # type: ignore


def ensure_schema(conn: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    conn.executescript(schema_sql)


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def closest_turn(turns: List[sqlite3.Row], timestamp: Optional[str]) -> Optional[str]:
    if not turns:
        return None
    if not timestamp:
        return turns[0]["id"]

    ts = parse_timestamp(timestamp)
    if not ts:
        return turns[0]["id"]

    best_turn = min(
        turns,
        key=lambda turn: abs((parse_timestamp(turn["timestamp"]) or ts) - ts),
    )
    return best_turn["id"]


def migrate():
    if not OLD_DB.exists():
        raise SystemExit(f"Legacy database not found at {OLD_DB}")

    if not BACKUP_FILE.exists():
        shutil.copy2(OLD_DB, BACKUP_FILE)
        print(f"Created backup at {BACKUP_FILE}")

    if NEW_DB.exists():
        NEW_DB.unlink()

    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row

    new_conn = sqlite3.connect(NEW_DB)
    new_conn.row_factory = sqlite3.Row
    ensure_schema(new_conn)

    provider_detector = ProviderDetector()

    sessions_cursor = old_conn.execute("SELECT * FROM sessions")
    sessions = sessions_cursor.fetchall()
    print(f"Migrating {len(sessions)} sessions...")

    for session in sessions:
        session_id = session["id"]
        start_time = session["start_time"]
        end_time = session["end_time"]
        new_conn.execute(
            """
            INSERT INTO sessions (
                id, title, start_time, end_time, duration_seconds,
                status, total_turns, primary_model, primary_provider, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                session["title"],
                start_time,
                end_time,
                session["duration_seconds"],
                session["status"],
                session["total_turns"],
                session["model"],
                None,
                json.dumps({"legacy": True}),
            ),
        )

        turn_rows = old_conn.execute(
            "SELECT * FROM conversation_turns WHERE session_id = ? ORDER BY order_index",
            (session_id,),
        ).fetchall()

        for turn in turn_rows:
            metadata = {
                "legacy_type": turn["type"],
                "legacy_content": turn["content"],
                "legacy_metadata": json.loads(turn["metadata"]) if turn["metadata"] else None,
            }
            new_conn.execute(
                """
                INSERT INTO turns (id, session_id, turn_number, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    turn["id"],
                    session_id,
                    turn["order_index"],
                    turn["timestamp"] or start_time,
                    json.dumps(metadata),
                ),
            )

        request_rows = old_conn.execute(
            "SELECT * FROM request_responses WHERE session_id = ?", (session_id,)
        ).fetchall()

        for request in request_rows:
            turn_id = closest_turn(turn_rows, request["timestamp"]) or str(uuid.uuid4())
            provider, protocol = provider_detector.detect(
                {"url": request["url"], "raw_request": {}}
            )
            request_id = request["id"] or str(uuid.uuid4())
            new_conn.execute(
                """
                INSERT INTO llm_requests (
                    id, turn_id, request_id, timestamp,
                    provider, endpoint_url, protocol,
                    model, temperature, max_tokens, top_p, top_k,
                    frequency_penalty, presence_penalty,
                    stop_sequences, other_params,
                    method, headers, raw_body, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    turn_id,
                    request["id"],
                    request["timestamp"] or start_time,
                    provider,
                    request["url"],
                    protocol,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    request["method"],
                    request["request_headers"],
                    request["request_body"],
                    json.dumps({"legacy": True}),
                ),
            )

            new_conn.execute(
                """
                INSERT INTO llm_responses (
                    id, request_id, timestamp,
                    status_code, headers, response_time_ms,
                    input_tokens, output_tokens, total_tokens, cached_tokens, estimated_cost_usd,
                    is_success, finish_reason,
                    error_type, error_message, error_code, retry_after,
                    raw_body, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    request_id,
                    request["timestamp"] or start_time,
                    request["status_code"],
                    request["response_headers"],
                    request["response_time_ms"],
                    None,
                    None,
                    None,
                    None,
                    None,
                    request["status_code"] == 200 if request["status_code"] is not None else True,
                    "stop",
                    None,
                    None,
                    None,
                    None,
                    request["response_body"],
                    json.dumps({"legacy": True}),
                ),
            )

    new_conn.commit()
    new_conn.close()
    old_conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
