"""
Database models, schema management, and query helpers for the Gemini CLI Dashboard.

This module implements the v2 deep-decomposition schema with prompt components
and response spans. It supersedes the original flat schema and should be used
by all backend services moving forward.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import os

import aiosqlite
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent
DB_FILE_PATH = os.getenv(
    "TIGERHILL_DB_PATH",
    str((BASE_DIR / "gemini_cli_dashboard_v3.db").resolve()),
)
SCHEMA_FILE_PATH = str((BASE_DIR / "database" / "schema_v3.sql").resolve())


def set_db_path(path: str) -> None:
    global DB_FILE_PATH
    DB_FILE_PATH = path


# ---------------------------------------------------------------------------
# Pydantic models mirroring the schema
# ---------------------------------------------------------------------------


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    total_turns: int = 0
    total_interactions: int = 0  # NEW: track total request/response count
    primary_model: Optional[str] = None
    primary_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Interaction(BaseModel):
    """Unified model for both requests and responses (Schema V3)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    turn_number: float  # Can be integer (1, 2) or fractional (6.1, 6.2) after split
    sequence: int
    type: str  # 'request' or 'response'

    # Request-specific fields (NULL for responses)
    request_id: Optional[str] = None  # Original request ID from JSON
    user_input: Optional[str] = None
    system_instruction: Optional[str] = None
    contents: Optional[List[Dict[str, Any]]] = None  # Full contents array
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    generation_config: Optional[Dict[str, Any]] = None

    # Response-specific fields (NULL for requests)
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    finish_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    is_success: Optional[bool] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_after: Optional[int] = None

    # Common fields
    content: Optional[str] = None  # Extracted content for easy access
    timestamp: float
    method: Optional[str] = None
    url: Optional[str] = None
    endpoint_url: Optional[str] = None
    protocol: Optional[str] = None
    provider: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    raw_request: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptComponent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    interaction_id: str  # Updated from request_id
    component_type: str
    role: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[Any] = None  # Can be dict or list (e.g., conversation_history)
    order_index: int = 0
    token_count: Optional[int] = None
    source: Optional[str] = None
    template_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResponseSpan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    interaction_id: str  # Updated from response_id
    span_type: str
    order_index: int = 0
    content: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    stream_index: Optional[int] = None
    timestamp: Optional[float] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    token_count: Optional[int] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    language: Optional[str] = None
    is_executable: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


# Legacy models (kept for backward compatibility with v2)
class Turn(BaseModel):
    """DEPRECATED: Use Interaction with turn_number instead."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    turn_number: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class LLMRequest(BaseModel):
    """DEPRECATED: Use Interaction with type='request' instead."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    turn_id: str
    request_id: Optional[str] = None
    timestamp: datetime
    provider: Optional[str] = None
    endpoint_url: Optional[str] = None
    protocol: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    other_params: Optional[Dict[str, Any]] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    raw_body: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """DEPRECATED: Use Interaction with type='response' instead."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    timestamp: datetime
    status_code: Optional[int] = None
    headers: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    is_success: bool = True
    finish_reason: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_after: Optional[int] = None
    raw_body: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Core database helpers
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create the schema if it doesn't exist."""
    schema_sql = Path(SCHEMA_FILE_PATH).read_text(encoding="utf-8")
    async with aiosqlite.connect(DB_FILE_PATH) as db:
        await db.executescript(schema_sql)
        await db.commit()


# Backwards compatible alias used by legacy scripts/tests
init_db_v2 = init_db


@asynccontextmanager
async def get_db():
    """Return an aiosqlite connection with row factory configured."""
    async with aiosqlite.connect(DB_FILE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # CRITICAL: Enable foreign key constraints to ensure CASCADE DELETE works
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


def _json_dumps(payload: Optional[Any]) -> Optional[str]:
    if payload is None:
        return None
    return json.dumps(payload)


def _json_loads(payload: Optional[Any]) -> Optional[Any]:
    if payload is None:
        return None
    if isinstance(payload, (dict, list)):
        return payload
    try:
        return json.loads(payload)
    except Exception:
        return None


async def _execute_with_optional_connection(
    query: str,
    params: Tuple[Any, ...],
    db: Optional[aiosqlite.Connection],
) -> None:
    if db is not None:
        await db.execute(query, params)
        return
    async with get_db() as owned_db:
        await owned_db.execute(query, params)
        await owned_db.commit()


async def insert_session(session: Session, db: Optional[aiosqlite.Connection] = None) -> str:
    await _execute_with_optional_connection(
        """
        INSERT OR REPLACE INTO sessions (
            id, title, start_time, end_time, duration_seconds,
            status, total_turns, primary_model, primary_provider, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session.id,
            session.title,
            session.start_time.isoformat(),
            session.end_time.isoformat() if session.end_time else None,
            session.duration_seconds,
            session.status,
            session.total_turns,
            session.primary_model,
            session.primary_provider,
            _json_dumps(session.metadata),
        ),
        db,
    )
    return session.id


async def insert_turn(turn: Turn, db: Optional[aiosqlite.Connection] = None) -> str:
    await _execute_with_optional_connection(
        """
        INSERT INTO turns (id, session_id, turn_number, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            turn.id,
            turn.session_id,
            turn.turn_number,
            turn.timestamp.isoformat(),
            _json_dumps(turn.metadata),
        ),
        db,
    )
    return turn.id


async def insert_llm_request(
    request: LLMRequest, db: Optional[aiosqlite.Connection] = None
) -> str:
    await _execute_with_optional_connection(
        """
        INSERT INTO llm_requests (
            id, turn_id, request_id, timestamp,
            provider, endpoint_url, protocol,
            model, temperature, max_tokens, top_p, top_k,
            frequency_penalty, presence_penalty,
            stop_sequences, other_params,
            method, headers, raw_body, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.id,
            request.turn_id,
            request.request_id,
            request.timestamp.isoformat(),
            request.provider,
            request.endpoint_url,
            request.protocol,
            request.model,
            request.temperature,
            request.max_tokens,
            request.top_p,
            request.top_k,
            request.frequency_penalty,
            request.presence_penalty,
            _json_dumps(request.stop_sequences),
            _json_dumps(request.other_params),
            request.method,
            _json_dumps(request.headers),
            _json_dumps(request.raw_body),
            _json_dumps(request.metadata),
        ),
        db,
    )
    return request.id


async def insert_prompt_component(
    component: PromptComponent, db: Optional[aiosqlite.Connection] = None
) -> str:
    await _execute_with_optional_connection(
        """
        INSERT INTO prompt_components (
            id, request_id, component_type, role, content, content_json,
            order_index, token_count, source, template_id, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            component.id,
            component.request_id,
            component.component_type,
            component.role,
            component.content,
            _json_dumps(component.content_json),
            component.order_index,
            component.token_count,
            component.source,
            component.template_id,
            _json_dumps(component.metadata),
        ),
        db,
    )
    return component.id


async def insert_llm_response(
    response: LLMResponse, db: Optional[aiosqlite.Connection] = None
) -> str:
    await _execute_with_optional_connection(
        """
        INSERT INTO llm_responses (
            id, request_id, timestamp,
            status_code, headers, response_time_ms,
            input_tokens, output_tokens, total_tokens, cached_tokens, estimated_cost_usd,
            is_success, finish_reason,
            error_type, error_message, error_code, retry_after,
            raw_body, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            response.id,
            response.request_id,
            response.timestamp.isoformat(),
            response.status_code,
            _json_dumps(response.headers),
            response.response_time_ms,
            response.input_tokens,
            response.output_tokens,
            response.total_tokens,
            response.cached_tokens,
            response.estimated_cost_usd,
            response.is_success,
            response.finish_reason,
            response.error_type,
            response.error_message,
            response.error_code,
            response.retry_after,
            _json_dumps(response.raw_body),
            _json_dumps(response.metadata),
        ),
        db,
    )
    return response.id


async def insert_response_span(
    span: ResponseSpan, db: Optional[aiosqlite.Connection] = None
) -> str:
    await _execute_with_optional_connection(
        """
        INSERT INTO response_spans (
            id, response_id, span_type, order_index,
            content, content_json,
            stream_index, timestamp, start_char, end_char,
            token_count,
            tool_name, tool_input, tool_output, tool_call_id,
            language, is_executable,
            metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            span.id,
            span.response_id,
            span.span_type,
            span.order_index,
            span.content,
            _json_dumps(span.content_json),
            span.stream_index,
            span.timestamp,
            span.start_char,
            span.end_char,
            span.token_count,
            span.tool_name,
            _json_dumps(span.tool_input),
            _json_dumps(span.tool_output),
            span.tool_call_id,
            span.language,
            span.is_executable,
            _json_dumps(span.metadata),
        ),
        db,
    )
    return span.id


# ---------------------------------------------------------------------------
# Query helpers used by routers and services
# ---------------------------------------------------------------------------


async def session_exists(session_id: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("SELECT 1 FROM sessions WHERE id = ? LIMIT 1", (session_id,))
        row = await cursor.fetchone()
    return row is not None


async def get_session_with_components(session_id: str) -> Optional[Dict[str, Any]]:
    """Return session data with nested turns/requests/components/spans."""
    async with get_db() as db:
        session_cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = await session_cursor.fetchone()
        if not session_row:
            return None
        session = _row_to_session(session_row)

        turn_cursor = await db.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_number", (session_id,)
        )
        turn_rows = await turn_cursor.fetchall()
        if not turn_rows:
            return {"session": session, "turns": []}

        turn_ids = [row["id"] for row in turn_rows]
        turns = [{**dict(row), "metadata": _json_loads(row["metadata"])} for row in turn_rows]

        requests = await _fetch_requests(db, turn_ids)
        components = await _fetch_prompt_components(db, [r["id"] for r in requests])
        responses = await _fetch_responses(db, [r["id"] for r in requests])
        spans = await _fetch_response_spans(db, [resp["id"] for resp in responses.values()])

        requests_by_turn: Dict[str, List[Dict[str, Any]]] = {tid: [] for tid in turn_ids}
        for request in requests:
            request_id = request["id"]
            request["stop_sequences"] = _json_loads(request["stop_sequences"])
            request["other_params"] = _json_loads(request["other_params"])
            request["headers"] = _json_loads(request["headers"])
            request["raw_body"] = _json_loads(request["raw_body"])
            request["metadata"] = _json_loads(request["metadata"])
            request["components"] = components.get(request_id, [])
            response = responses.get(request_id)
            if response:
                resp_id = response["id"]
                response["headers"] = _json_loads(response["headers"])
                response["raw_body"] = _json_loads(response["raw_body"])
                response["metadata"] = _json_loads(response["metadata"])
                response["spans"] = spans.get(resp_id, [])
            request["response"] = response
            requests_by_turn.setdefault(request["turn_id"], []).append(request)

        for turn in turns:
            turn["requests"] = sorted(
                requests_by_turn.get(turn["id"], []),
                key=lambda req: req["timestamp"] or "",
            )

        return {"session": session, "turns": turns}


async def get_request_with_spans(request_id: str) -> Optional[Dict[str, Any]]:
    """Return a single request with its response and spans."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM llm_requests WHERE id = ?", (request_id,))
        request_row = await cursor.fetchone()
        if not request_row:
            return None

        request = dict(request_row)
        request["headers"] = _json_loads(request["headers"])
        request["raw_body"] = _json_loads(request["raw_body"])
        request["stop_sequences"] = _json_loads(request["stop_sequences"])
        request["other_params"] = _json_loads(request["other_params"])
        request["metadata"] = _json_loads(request["metadata"])

        comp_map = await _fetch_prompt_components(db, [request_id])
        request["components"] = comp_map.get(request_id, [])

        responses = await _fetch_responses(db, [request_id])
        response = responses.get(request_id)
        if response:
            resp_id = response["id"]
            response["headers"] = _json_loads(response["headers"])
            response["raw_body"] = _json_loads(response["raw_body"])
            response["metadata"] = _json_loads(response["metadata"])
            span_map = await _fetch_response_spans(db, [resp_id])
            response["spans"] = span_map.get(resp_id, [])
        request["response"] = response

        return request


# ---------------------------------------------------------------------------
# Internal fetch helpers
# ---------------------------------------------------------------------------


def _row_to_session(row: aiosqlite.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "duration_seconds": row["duration_seconds"],
        "status": row["status"],
        "total_turns": row["total_turns"],
        "primary_model": row["primary_model"],
        "primary_provider": row["primary_provider"],
        "metadata": _json_loads(row["metadata"]),
        "created_at": row["created_at"],
    }


async def _fetch_requests(
    db: aiosqlite.Connection, turn_ids: Iterable[str]
) -> List[Dict[str, Any]]:
    if not turn_ids:
        return []
    placeholders = ",".join("?" for _ in turn_ids)
    cursor = await db.execute(
        f"""
        SELECT * FROM llm_requests
        WHERE turn_id IN ({placeholders})
        ORDER BY timestamp
        """,
        tuple(turn_ids),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def _fetch_prompt_components(
    db: aiosqlite.Connection, request_ids: Iterable[str]
) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    request_ids = list(request_ids)
    if not request_ids:
        return result
    placeholders = ",".join("?" for _ in request_ids)
    cursor = await db.execute(
        f"""
        SELECT * FROM prompt_components
        WHERE request_id IN ({placeholders})
        ORDER BY order_index
        """,
        tuple(request_ids),
    )
    rows = await cursor.fetchall()
    for row in rows:
        component = dict(row)
        component["content_json"] = _json_loads(row["content_json"])
        component["metadata"] = _json_loads(row["metadata"])
        component["token_count"] = row["token_count"]
        result.setdefault(row["request_id"], []).append(component)
    return result


async def _fetch_responses(
    db: aiosqlite.Connection, request_ids: Iterable[str]
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    request_ids = list(request_ids)
    if not request_ids:
        return result
    placeholders = ",".join("?" for _ in request_ids)
    cursor = await db.execute(
        f"""
        SELECT * FROM llm_responses
        WHERE request_id IN ({placeholders})
        """,
        tuple(request_ids),
    )
    rows = await cursor.fetchall()
    for row in rows:
        result[row["request_id"]] = dict(row)
    return result


async def _fetch_response_spans(
    db: aiosqlite.Connection, response_ids: Iterable[str]
) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {}
    response_ids = list(response_ids)
    if not response_ids:
        return result
    placeholders = ",".join("?" for _ in response_ids)
    cursor = await db.execute(
        f"""
        SELECT * FROM response_spans
        WHERE response_id IN ({placeholders})
        ORDER BY order_index
        """,
        tuple(response_ids),
    )
    rows = await cursor.fetchall()
    for row in rows:
        span = dict(row)
        span["content_json"] = _json_loads(row["content_json"])
        span["tool_input"] = _json_loads(row["tool_input"])
        span["tool_output"] = _json_loads(row["tool_output"])
        span["metadata"] = _json_loads(row["metadata"])
        result.setdefault(row["response_id"], []).append(span)
    return result
