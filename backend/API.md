# API Reference

All endpoints are served from FastAPI (`backend/main.py`) with base URL `/api`. Responses are JSON; errors follow standard FastAPI error structure.

## Sessions

### `GET /api/sessions`
Query paginated list of sessions.

Parameters:
- `limit` (1–100), `cursor` (opaque), `sort` (`newest|oldest|longest|shortest`)
- Filters: `model`, `provider`, `status`, `start_date`, `end_date`, `search`

```http
GET /api/sessions?provider=gemini&status=success&limit=20
```

Response:
```json
{
  "sessions": [
    {
      "id": "session-123",
      "title": "gemini-cli Session",
      "start_time": "2025-01-10T12:00:00Z",
      "duration_seconds": 92,
      "status": "success",
      "total_turns": 6,
      "primary_model": "gemini-1.5-pro",
      "primary_provider": "gemini"
    }
  ],
  "total": 128,
  "next_cursor": "MjAyNS0wMS0xMFQxMjowMDowMFo=|session-123",
  "limit": 20,
  "sort": "newest"
}
```

### `GET /api/sessions/{session_id}`
Returns the session summary, full conversation flow (flattened prompt components & spans), and enriched turns array.

### `GET /api/sessions/{session_id}/turns`
Pagination over turns: `page`, `limit`.

### `GET /api/sessions/{session_id}/details`
Aggregates every request/response object for the session (used by the “请求详情” page).

### `GET /api/sessions/{session_id}/intent`
Runs `IntentAnalyzer` over the conversation flow and returns:
- `conversation_flow`: user turns annotated with `intent_analysis`
- `intent_flow_analysis`: transition matrix, patterns, and distribution

## Statistics

### `GET /api/stats/overview`
Returns aggregate metrics:
```json
{
  "total_sessions": 256,
  "avg_duration": "2m 10s",
  "top_model": "gpt-4o-mini",
  "success_rate": 83.1,
  "session_volume_last_7_days": 42,
  "session_volume_change": 12.5,
  "response_time_ms": { "p50": 210, "p90": 520, "p99": 1200 },
  "error_breakdown": { "rate_limit": 3, "timeout": 1 }
}
```

### `GET /api/stats/trends`
Query parameters: `days` (≤30) or `start_date` + `end_date`. Response contains daily buckets with `session_count` and `avg_duration`.

### `GET /api/stats/models`
Lists per-model stats: `session_count`, `avg_duration`, `success_rate`, `error_count`.

## Comparison

### `POST /api/comparison`

```http
POST /api/comparison
{
  "session_a": "session-123",
  "session_b": "session-789"
}
```

Response includes similarity percentage, change summary, and the first 200 unified diff lines. Used by `/compare`.

### `GET /api/compare/intents/{session_a}/{session_b}`
Produces semantic intent diff:

```json
{
  "intent_diff": {
    "added_intents": [{ "id": "session-789-4", "intent_type": "analysis", ... }],
    "removed_intents": [],
    "modified_intents": [
      {
        "old_intent": { "intent_type": "task_completion", "confidence": 0.44, ... },
        "new_intent": { "intent_type": "analysis", "confidence": 0.61, ... }
      }
    ],
    "intent_transitions": [
      { "old_pattern": null, "new_pattern": { "from_intent": "analysis", "to_intent": "task_completion", "frequency": 2 } }
    ]
  }
}
```

## Importer

### `POST /api/import/json-files`
Multipart upload of one or more `.json` capture files.

Response:
```json
{
  "success": true,
  "imported_files": 3,
  "skipped_files": 1,
  "total_files": 4,
  "errors": []
}
```

### `POST /api/import/jobs`
Creates a background import job (useful for bulk uploads). Returns job status immediately.

### `GET /api/import/jobs/{job_id}`
Poll job progress:
```json
{
  "id": "a3a1a2ce-6ae4-4c51-9099-712cde508a7b",
  "status": "completed",
  "processed_files": 10,
  "total_files": 10,
  "skipped_files": 1,
  "errors": [],
  "started_at": "2025-01-20T12:00:00Z",
  "finished_at": "2025-01-20T12:05:12Z",
  "summary": { "imported": 9, "skipped": 1 }
}
```

## Health

- `GET /` returns `{ "message": "Gemini CLI Dashboard API 服务运行正常" }`.
- `GET /health` returns heartbeat with timestamp.

Refer to `backend/services/importer.py` and `backend/routers/*` for implementation details, and use `docs/deployment/guide.md` for production deployment guidance.
