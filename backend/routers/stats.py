"""
Statistics endpoints backed by the schema v2 database.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..database import get_db

router = APIRouter()


def _format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "0s"
    seconds = float(seconds)
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


async def _response_time_percentiles(db) -> Dict[str, Optional[float]]:
    cursor = await db.execute(
        """
        SELECT duration_ms FROM llm_interactions
        WHERE type = 'response' AND duration_ms IS NOT NULL
        ORDER BY duration_ms
        """
    )
    rows = await cursor.fetchall()
    values = [row[0] for row in rows]
    if not values:
        return {"p50": None, "p90": None, "p99": None}

    def percentile(p: float) -> float:
        index = min(len(values) - 1, max(0, int(round(p * len(values))) - 1))
        return values[index]

    return {
        "p50": percentile(0.5),
        "p90": percentile(0.9),
        "p99": percentile(0.99),
    }


async def _error_breakdown(db) -> Dict[str, int]:
    cursor = await db.execute(
        """
        SELECT error_type, COUNT(*) as count
        FROM llm_interactions
        WHERE type = 'response' AND error_type IS NOT NULL
        GROUP BY error_type
        """
    )
    rows = await cursor.fetchall()
    return {row["error_type"]: row["count"] for row in rows if row["error_type"]}


@router.get("/stats/overview")
async def get_stats_overview():
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as total FROM sessions")
        total_sessions = (await cursor.fetchone())["total"]

        cursor = await db.execute(
            "SELECT AVG(duration_seconds) as avg_duration FROM sessions WHERE duration_seconds IS NOT NULL"
        )
        avg_duration = (await cursor.fetchone())["avg_duration"]

        cursor = await db.execute(
            """
            SELECT primary_model, COUNT(*) as count
            FROM sessions
            WHERE primary_model IS NOT NULL
            GROUP BY primary_model
            ORDER BY count DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        top_model = row["primary_model"] if row else "N/A"

        cursor = await db.execute(
            """
            SELECT
                COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                COUNT(*) as total_count
            FROM sessions
            """
        )
        success_row = await cursor.fetchone()
        success_rate = 0
        if success_row["total_count"] > 0:
            success_rate = round(success_row["success_count"] / success_row["total_count"] * 100, 2)

        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        cursor = await db.execute("SELECT COUNT(*) as count FROM sessions WHERE start_time >= ?", (seven_days_ago,))
        last_7_days = (await cursor.fetchone())["count"]

        fourteen_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()
        cursor = await db.execute(
            """
            SELECT COUNT(*) as count
            FROM sessions
            WHERE start_time >= ? AND start_time < ?
            """,
            (fourteen_days_ago, seven_days_ago),
        )
        prev_week = (await cursor.fetchone())["count"]
        session_volume_change = 0
        if prev_week > 0:
            session_volume_change = round(((last_7_days - prev_week) / prev_week) * 100, 2)

        percentiles = await _response_time_percentiles(db)
        errors = await _error_breakdown(db)

        return {
            "total_sessions": total_sessions,
            "avg_duration": _format_duration(avg_duration),
            "top_model": top_model,
            "success_rate": success_rate,
            "session_volume_last_7_days": last_7_days,
            "session_volume_change": session_volume_change,
            "response_time_ms": percentiles,
            "error_breakdown": errors,
        }


@router.get("/stats/trends")
async def get_stats_trends(
    days: int = Query(7, ge=1, le=30),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.") from exc
        window_days = (end_dt - start_dt).days + 1
    else:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=days - 1)
        window_days = days

    async with get_db() as db:
        trends: List[Dict[str, Any]] = []
        for i in range(window_days):
            day = start_dt + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) as session_count,
                    AVG(duration_seconds) as avg_duration
                FROM sessions
                WHERE DATE(start_time) = DATE(?)
                """,
                (day_str,),
            )
            row = await cursor.fetchone()
            trends.append(
                {
                    "date": day_str,
                    "session_count": row["session_count"] or 0,
                    "avg_duration": round(row["avg_duration"]) if row["avg_duration"] else 0,
                }
            )

        return {"trends": trends}


@router.get("/stats/models")
async def get_model_stats():
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                primary_model,
                COUNT(*) as session_count,
                AVG(duration_seconds) as avg_duration,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count
            FROM sessions
            WHERE primary_model IS NOT NULL
            GROUP BY primary_model
            ORDER BY session_count DESC
            """
        )
        rows = await cursor.fetchall()

        model_stats = []
        for row in rows:
            success_rate = 0
            if row["session_count"] > 0:
                success_rate = round(row["success_count"] / row["session_count"] * 100, 2)
            model_stats.append(
                {
                    "model": row["primary_model"],
                    "session_count": row["session_count"],
                    "avg_duration": round(row["avg_duration"], 2) if row["avg_duration"] else 0,
                    "success_rate": success_rate,
                    "error_count": row["error_count"],
                }
            )

        return {"model_stats": model_stats}
