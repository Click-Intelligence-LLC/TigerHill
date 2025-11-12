"""
Session-related API endpoints backed by the schema v2 database.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from ..database import get_db, get_session_with_components
from ..services.intent_analyzer import IntentAnalyzer

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _encode_cursor(start_time: str, session_id: str) -> str:
    raw = f"{start_time}|{session_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str) -> Tuple[str, str]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        parts = decoded.split("|", 1)
        return parts[0], parts[1]
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


def _component_to_flow_entry(component: Dict[str, Any], timestamp: str, provider: Optional[str]) -> Dict[str, Any]:
    content = component.get("content")
    if not content and component.get("content_json") is not None:
        content = json.dumps(component["content_json"], ensure_ascii=False, indent=2)
    return {
        "type": component.get("component_type"),
        "timestamp": timestamp,
        "content": content,
        "metadata": {
            "role": component.get("role"),
            "source": component.get("source"),
            "provider": provider,
        },
    }


def _span_to_flow_entry(span: Dict[str, Any], timestamp: str, provider: Optional[str]) -> Dict[str, Any]:
    content = span.get("content")
    if not content and span.get("content_json") is not None:
        content = json.dumps(span["content_json"], ensure_ascii=False, indent=2)
    return {
        "type": span.get("span_type"),
        "timestamp": timestamp,
        "content": content,
        "metadata": {
            "tool_name": span.get("tool_name"),
            "provider": provider,
            "language": span.get("language"),
        },
    }


def _build_conversation_flow(turns: List[Dict[str, Any]], exclude_history: bool = True) -> List[Dict[str, Any]]:
    """
    Build conversation flow from turns.

    Args:
        turns: List of turn objects with requests
        exclude_history: If True, skip conversation_history components to avoid duplicates (default: True)

    Returns:
        List of conversation flow entries (components + spans)
    """
    flow: List[Dict[str, Any]] = []
    for turn in turns:
        for request in turn.get("requests", []):
            request_timestamp = request.get("timestamp")
            provider = request.get("provider")
            for component in request.get("components", []):
                # Filter conversation_history to avoid showing duplicates in timeline
                # Gemini API includes full conversation history in each request, so we skip
                # history entries to show a clean deduplicated timeline
                if exclude_history and component.get("component_type") == "conversation_history":
                    continue
                flow.append(_component_to_flow_entry(component, request_timestamp, provider))
            response = request.get("response")
            if response:
                response_timestamp = response.get("timestamp") or request_timestamp
                for span in response.get("spans", []):
                    flow.append(_span_to_flow_entry(span, response_timestamp, provider))
    return flow


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def get_sessions(
    cursor: Optional[str] = Query(None),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    model: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("newest", regex="^(newest|oldest|longest|shortest)$"),
):
    async with get_db() as db:
        where_clauses = []
        params: List[Any] = []

        if model:
            where_clauses.append("primary_model = ?")
            params.append(model)
        if provider:
            where_clauses.append("primary_provider = ?")
            params.append(provider)
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if start_date:
            where_clauses.append("start_time >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("start_time <= ?")
            params.append(end_date)
        if search:
            like_query = f"%{search}%"
            where_clauses.append(
                """(
                    title LIKE ?
                    OR id LIKE ?
                    OR EXISTS (
                        SELECT 1 FROM turns tt
                        JOIN llm_requests lr ON lr.turn_id = tt.id
                        JOIN prompt_components pc ON pc.request_id = lr.id
                        WHERE tt.session_id = sessions.id AND pc.content LIKE ?
                    )
                    OR EXISTS (
                        SELECT 1 FROM turns tt2
                        JOIN llm_requests lr2 ON lr2.turn_id = tt2.id
                        JOIN llm_responses resp ON resp.request_id = lr2.id
                        JOIN response_spans rs ON rs.response_id = resp.id
                        WHERE tt2.session_id = sessions.id AND rs.content LIKE ?
                    )
                )"""
            )
            params.extend([like_query, like_query, like_query, like_query])

        if cursor:
            cursor_value, cursor_id = _decode_cursor(cursor)
            if sort == "newest":
                where_clauses.append("(start_time < ? OR (start_time = ? AND id < ?))")
                params.extend([cursor_value, cursor_value, cursor_id])
            elif sort == "oldest":
                where_clauses.append("(start_time > ? OR (start_time = ? AND id > ?))")
                params.extend([cursor_value, cursor_value, cursor_id])
            elif sort == "longest":
                numeric_value = float(cursor_value)
                where_clauses.append("(duration_seconds < ? OR (duration_seconds = ? AND id < ?))")
                params.extend([numeric_value, numeric_value, cursor_id])
            else:  # shortest
                numeric_value = float(cursor_value)
                where_clauses.append("(duration_seconds > ? OR (duration_seconds = ? AND id > ?))")
                params.extend([numeric_value, numeric_value, cursor_id])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if sort == "newest":
            order_clause = "ORDER BY start_time DESC, id DESC"
        elif sort == "oldest":
            order_clause = "ORDER BY start_time ASC, id ASC"
        elif sort == "longest":
            order_clause = "ORDER BY duration_seconds DESC, start_time DESC"
        else:
            order_clause = "ORDER BY duration_seconds ASC, start_time DESC"

        query = f"""
            SELECT id, title, start_time, end_time, duration_seconds,
                   status, total_turns, primary_model, primary_provider
            FROM sessions
            {where_sql}
            {order_clause}
            LIMIT ?
        """
        query_params = list(params)
        query_params.append(limit + 1)
        cursor_obj = await db.execute(query, query_params)
        rows = await cursor_obj.fetchall()

        has_more = len(rows) > limit
        rows = rows[:limit]

        sessions = [
            {
                "id": row["id"],
                "title": row["title"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "total_turns": row["total_turns"],
                "primary_model": row["primary_model"],
                "primary_provider": row["primary_provider"],
            }
            for row in rows
        ]

        next_cursor = None
        if has_more and rows:
            last_row = rows[-1]
            if sort in {"longest", "shortest"}:
                cursor_value = last_row["duration_seconds"] or 0
            else:
                cursor_value = last_row["start_time"]
            next_cursor = _encode_cursor(str(cursor_value), last_row["id"])

        count_query = f"SELECT COUNT(*) as total FROM sessions {where_sql}"
        count_cursor = await db.execute(count_query, params)
        total = (await count_cursor.fetchone())["total"]

        return {
            "sessions": sessions,
            "total": total,
            "next_cursor": next_cursor,
            "limit": limit,
            "sort": sort,
        }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    exclude_history: bool = Query(True, description="Filter conversation_history from timeline for clean view")
):
    """
    Get session details with conversation flow.

    Args:
        session_id: Session ID
        exclude_history: If True, filter conversation_history components from timeline (default: True).
                        Set to False to see raw request data including history duplicates.

    Returns:
        Session data with conversation flow and turns
    """
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_flow = _build_conversation_flow(result["turns"], exclude_history=exclude_history)

    return {
        "session": result["session"],
        "conversation_flow": conversation_flow,
        "turns": result["turns"],
    }


@router.get("/sessions/{session_id}/turns")
async def get_session_turns(
    session_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    start_index = (page - 1) * limit
    end_index = start_index + limit
    turns = result["turns"][start_index:end_index]

    return {
        "session": result["session"],
        "turns": turns,
        "page": page,
        "limit": limit,
        "total_turns": len(result["turns"]),
    }


@router.get("/sessions/{session_id}/turns/{turn_number}")
async def get_single_turn(session_id: str, turn_number: int):
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    for turn in result["turns"]:
        if turn["turn_number"] == turn_number:
            return {"session": result["session"], "turn": turn}
    raise HTTPException(status_code=404, detail="Turn not found")


@router.get("/sessions/{session_id}/details")
async def get_session_details(session_id: str):
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    requests: List[Dict[str, Any]] = []
    for turn in result["turns"]:
        for request in turn.get("requests", []):
            requests.append(request)

    return {"session": result["session"], "requests": requests}


@router.get("/sessions/{session_id}/intent")
async def get_session_with_intent(
    session_id: str,
    exclude_history: bool = Query(True, description="Filter conversation_history from timeline for clean view")
):
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_flow = _build_conversation_flow(result["turns"], exclude_history=exclude_history)
    analyzer = IntentAnalyzer()
    enriched_flow: List[Dict[str, Any]] = []
    for entry in conversation_flow:
        enriched_entry = dict(entry)
        if entry["type"] in {"user", "user_input"}:
            try:
                enriched_entry["intent_analysis"] = analyzer.analyze_intent(entry["content"])
            except Exception:
                enriched_entry["intent_analysis"] = None
        enriched_flow.append(enriched_entry)

    intent_flow_analysis = analyzer.analyze_intent_flow(enriched_flow)
    return {
        "session": result["session"],
        "conversation_flow": enriched_flow,
        "intent_flow_analysis": intent_flow_analysis,
    }
