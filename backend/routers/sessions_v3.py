"""
Session and interaction API endpoints for schema v3 (unified interaction model).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import get_db

router = APIRouter(prefix="/v3", tags=["sessions-v3"])


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all sessions with v3 schema (includes total_interactions)."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, title, start_time, end_time, duration_seconds, status,
                   total_turns, total_interactions, primary_model, primary_provider
            FROM sessions
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append({
                "id": row["id"],
                "title": row["title"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "total_turns": row["total_turns"],
                "total_interactions": row["total_interactions"],
                "primary_model": row["primary_model"],
                "primary_provider": row["primary_provider"],
            })

        # Get total count
        cursor = await db.execute("SELECT COUNT(*) FROM sessions")
        total = (await cursor.fetchone())[0]

        return {
            "sessions": sessions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details with interaction counts."""
    async with get_db() as db:
        # Get session
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        session = await cursor.fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get interaction stats
        cursor = await db.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN type = 'request' THEN 1 ELSE 0 END) as requests,
                SUM(CASE WHEN type = 'response' THEN 1 ELSE 0 END) as responses
            FROM llm_interactions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        stats = await cursor.fetchone()

        return {
            "id": session["id"],
            "title": session["title"],
            "start_time": session["start_time"],
            "end_time": session["end_time"],
            "duration_seconds": session["duration_seconds"],
            "status": session["status"],
            "total_turns": session["total_turns"],
            "total_interactions": session["total_interactions"],
            "primary_model": session["primary_model"],
            "primary_provider": session["primary_provider"],
            "metadata": json.loads(session["metadata"]) if session["metadata"] else {},
            "stats": {
                "total_interactions": stats["total"],
                "request_count": stats["requests"],
                "response_count": stats["responses"],
            },
        }


# ---------------------------------------------------------------------------
# Interaction endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}/interactions")
async def get_session_interactions(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all interactions for a session (no JOINs needed!)."""
    async with get_db() as db:
        # Verify session exists
        cursor = await db.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        # Get interactions
        cursor = await db.execute(
            """
            SELECT *
            FROM llm_interactions
            WHERE session_id = ?
            ORDER BY turn_number, sequence
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset),
        )
        rows = await cursor.fetchall()

        interactions = []
        for row in rows:
            interaction = {
                "id": row["id"],
                "session_id": row["session_id"],
                "turn_number": row["turn_number"],
                "sequence": row["sequence"],
                "type": row["type"],
                "timestamp": row["timestamp"],
                "content": row["content"],  # Add content field for both types
            }

            # Add type-specific fields
            if row["type"] == "request":
                # Parse JSON fields
                generation_config = json.loads(row["generation_config"]) if row["generation_config"] else None
                headers = json.loads(row["headers"]) if row["headers"] else None
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}

                interaction.update({
                    "request_id": row["request_id"],
                    "user_input": row["user_input"],
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "top_p": row["top_p"],
                    "top_k": row["top_k"],
                    "url": row["url"],
                    "generation_config": generation_config,
                    "headers": headers,
                    "metadata": metadata,
                })
            else:  # response
                interaction.update({
                    "request_id": row["request_id"],
                    "status_code": row["status_code"],
                    "duration_ms": row["duration_ms"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "total_tokens": row["total_tokens"],
                    "finish_reason": row["finish_reason"],
                    "is_success": row["is_success"],
                })

            interactions.append(interaction)

        # Get total count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM llm_interactions WHERE session_id = ?",
            (session_id,),
        )
        total = (await cursor.fetchone())[0]

        return {
            "interactions": interactions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/sessions/{session_id}/turns/{turn_number}")
async def get_turn_interactions(session_id: str, turn_number: int):
    """Get all interactions for a specific turn."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT *
            FROM llm_interactions
            WHERE session_id = ? AND turn_number = ?
            ORDER BY sequence
            """,
            (session_id, turn_number),
        )
        rows = await cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="Turn not found")

        interactions = []
        for row in rows:
            interaction = {
                "id": row["id"],
                "turn_number": row["turn_number"],
                "sequence": row["sequence"],
                "type": row["type"],
                "timestamp": row["timestamp"],
            }

            if row["type"] == "request":
                interaction.update({
                    "request_id": row["request_id"],
                    "user_input": row["user_input"],
                    "model": row["model"],
                    "contents": json.loads(row["contents"]) if row["contents"] else None,
                })
            else:
                interaction.update({
                    "request_id": row["request_id"],
                    "status_code": row["status_code"],
                    "duration_ms": row["duration_ms"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                })

            interactions.append(interaction)

        return {
            "session_id": session_id,
            "turn_number": turn_number,
            "interactions": interactions,
        }


@router.get("/interactions/{interaction_id}")
async def get_interaction_detail(interaction_id: str):
    """Get detailed interaction with components or spans."""
    async with get_db() as db:
        # Get interaction
        cursor = await db.execute(
            "SELECT * FROM llm_interactions WHERE id = ?",
            (interaction_id,),
        )
        interaction = await cursor.fetchone()

        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")

        result = dict(interaction)

        # Parse JSON fields
        for field in ["contents", "generation_config", "headers", "raw_request", "raw_response", "metadata"]:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except:
                    pass

        # Get components or spans
        if interaction["type"] == "request":
            cursor = await db.execute(
                """
                SELECT *
                FROM prompt_components
                WHERE interaction_id = ?
                ORDER BY order_index
                """,
                (interaction_id,),
            )
            components = await cursor.fetchall()
            result["components"] = [dict(c) for c in components]

        else:  # response
            cursor = await db.execute(
                """
                SELECT *
                FROM response_spans
                WHERE interaction_id = ?
                ORDER BY order_index
                """,
                (interaction_id,),
            )
            spans = await cursor.fetchall()
            result["spans"] = [dict(s) for s in spans]

        return result


# ---------------------------------------------------------------------------
# Statistics endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get aggregated statistics for a session."""
    async with get_db() as db:
        # Per-turn stats
        cursor = await db.execute(
            """
            SELECT
                turn_number,
                COUNT(*) as interaction_count,
                SUM(CASE WHEN type = 'request' THEN 1 ELSE 0 END) as request_count,
                SUM(CASE WHEN type = 'response' THEN 1 ELSE 0 END) as response_count,
                SUM(CASE WHEN type = 'response' THEN COALESCE(input_tokens, 0) ELSE 0 END) as total_input_tokens,
                SUM(CASE WHEN type = 'response' THEN COALESCE(output_tokens, 0) ELSE 0 END) as total_output_tokens
            FROM llm_interactions
            WHERE session_id = ?
            GROUP BY turn_number
            ORDER BY turn_number
            """,
            (session_id,),
        )
        turn_stats = await cursor.fetchall()

        # Overall stats
        cursor = await db.execute(
            """
            SELECT
                COUNT(DISTINCT turn_number) as total_turns,
                COUNT(*) as total_interactions,
                SUM(CASE WHEN type = 'response' THEN COALESCE(input_tokens, 0) ELSE 0 END) as total_input_tokens,
                SUM(CASE WHEN type = 'response' THEN COALESCE(output_tokens, 0) ELSE 0 END) as total_output_tokens
            FROM llm_interactions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        overall = await cursor.fetchone()

        return {
            "session_id": session_id,
            "overall": dict(overall),
            "per_turn": [dict(t) for t in turn_stats],
        }


@router.get("/interactions/{interaction_id}/components")
async def get_interaction_components(interaction_id: str):
    """Get prompt components for a request interaction."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM prompt_components
            WHERE interaction_id = ?
            ORDER BY order_index
            """,
            (interaction_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/interactions/{interaction_id}/spans")
async def get_interaction_spans(interaction_id: str):
    """Get response spans for a response interaction."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM response_spans
            WHERE interaction_id = ?
            ORDER BY order_index
            """,
            (interaction_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Replay endpoint
# ---------------------------------------------------------------------------


class EditedComponent(BaseModel):
    """Edited component data."""
    id: str
    content: Optional[str] = None
    content_json: Optional[Any] = None


class ConfigOverrides(BaseModel):
    """Configuration overrides for replay."""
    endpoint: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


class ReplayRequest(BaseModel):
    """Request body for replay endpoint."""
    request_interaction_id: str
    edited_components: List[EditedComponent]
    config_overrides: Optional[ConfigOverrides] = None


@router.post("/replay")
async def replay_request(request: ReplayRequest):
    """
    Replay a request with edited components.

    This endpoint takes an original request interaction ID and a list of edited components,
    then simulates sending a new request to the LLM with the modified prompt.

    NOTE: This is a mock implementation. In production, you would:
    1. Fetch the original request parameters (model, temperature, etc.)
    2. Construct the modified prompt from edited components
    3. Call the actual LLM API
    4. Store the new response in the database
    5. Return the response interaction

    For now, this returns a mock response for UI demonstration.
    """
    async with get_db() as db:
        # Fetch original request interaction
        cursor = await db.execute(
            "SELECT * FROM llm_interactions WHERE id = ? AND type = 'request'",
            (request.request_interaction_id,),
        )
        original_request = await cursor.fetchone()

        if not original_request:
            raise HTTPException(status_code=404, detail="Original request not found")

        # Get config overrides
        config = request.config_overrides.model_dump(exclude_none=True) if request.config_overrides else {}

        # Mock response - in production, this would be a real LLM API call
        mock_response = {
            "replay_id": str(uuid.uuid4()),
            "original_request_id": request.request_interaction_id,
            "timestamp": time.time(),
            "status": "success",
            "message": "This is a mock replay response. In production, this would contain the actual LLM response.",
            "edited_components_count": len(request.edited_components),
            "config_overrides": config,
            "applied_config": {
                "endpoint": config.get("endpoint", original_request["url"]),
                "model": config.get("model", original_request["model"]),
                "temperature": config.get("temperature", original_request["temperature"]),
                "max_tokens": config.get("max_tokens", original_request["max_tokens"]),
                "top_p": config.get("top_p", original_request["top_p"]),
                "top_k": config.get("top_k", original_request["top_k"]),
            },
            "mock_response_data": {
                "content": "这是一个模拟的重放响应。在实际生产环境中，这里会包含真实的 LLM API 响应内容。",
                "finish_reason": "stop",
                "total_tokens": 150,
                "duration_ms": 1234,
            },
            # For UI to know this is a mock
            "is_mock": True,
        }

        return mock_response
