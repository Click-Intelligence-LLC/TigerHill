# Schema v2 Overview

The dashboard persists imported sessions in SQLite using a normalized graph that captures every request/response component. The schema is defined in `backend/database/schema_v2.sql` and summarized below.

## Entity Relationships

```
sessions (1) ──< turns (1) ──< llm_requests (1) ──< prompt_components
                                      │
                                      └── llm_responses (1) ──< response_spans
```

- Every **session** contains ordered **turns**.
- Each **turn** can issue multiple **llm_requests**.
- Every request generates zero or more **prompt_components** (system/user/tool chunks).
- Each request may have one **llm_response** which in turn emits zero or more **response_spans** (text/tool output/chunk metadata).

## Table Details

### `sessions`
| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) | Stable session identifier (from capture). |
| `title`, `status`, `total_turns` | Presentation metadata. |
| `start_time`, `end_time`, `duration_seconds` | Timestamps stored as ISO strings. |
| `primary_model`, `primary_provider` | Derived from first detected request. |
| `metadata` (JSON) | Agent name, source tags, etc. |

Indexes:
- `idx_sessions_start_time`
- `idx_sessions_model`
- `idx_sessions_status`

### `turns`
| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) |
| `session_id` (FK → sessions.id) |
| `turn_number` | Zero-based ordering within the session. |
| `timestamp` | When the turn started. |
| `metadata` (JSON) | Raw capture snapshot. |

Indexes:
- `idx_turns_session`

### `llm_requests`
| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) |
| `turn_id` (FK → turns.id) |
| `request_id` | Provider-generated identifier (if present). |
| `provider`, `protocol`, `model`, `endpoint_url` | Detection + normalization output. |
| `temperature`, `max_tokens`, `top_p`, `top_k`, `frequency_penalty`, `presence_penalty` | Normalized params. |
| `stop_sequences` (JSON), `other_params` (JSON) | Additional config. |
| `headers` (JSON) | Redacted headers. |
| `raw_body` (JSON) | Original provider body for debugging. |
| `metadata` (JSON) | Capture trace info. |

Indexes:
- `idx_requests_turn`
- `idx_requests_provider`
- `idx_requests_model`

### `prompt_components`
Captures decomposed prompt pieces in display order.

| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) |
| `request_id` (FK → llm_requests.id) |
| `component_type` | `system`, `user`, `assistant`, `tool_definition`, `context`, etc. |
| `role`, `content`, `content_json` | Text and structured payload for the component. |
| `order_index` | Maintains original order within the request. |
| `token_count` | Estimated using tiktoken heuristics. |
| `source` | Origin (messages, tool_call, systemInstruction, …). |

Indexes:
- `idx_components_request`
- `idx_components_type`

### `llm_responses`
| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) |
| `request_id` (FK → llm_requests.id) |
| `timestamp` | Response time. |
| `status_code`, `response_time_ms` | HTTP metadata. |
| `input_tokens`, `output_tokens`, `total_tokens` | Usage metrics pulled from provider payload. |
| `is_success`, `finish_reason` | Derived from provider/protocol heuristics. |
| `error_type`, `error_message`, `error_code`, `retry_after` | Classified via `ErrorClassifier`. |
| `headers`, `raw_body`, `metadata` | Additional debugging context. |

Indexes:
- `idx_responses_request`
- `idx_responses_status`
- `idx_responses_error_type`

### `response_spans`
Stores decomposed model output (text chunks, thinking segments, tool calls, code blocks).

| Column | Notes |
| --- | --- |
| `id` (TEXT, PK) |
| `response_id` (FK → llm_responses.id) |
| `span_type` | `text`, `tool_call`, `code`, `thinking`, etc. |
| `order_index`, `stream_index` | Preserve streaming order (if streamed). |
| `content`, `content_json` | Span payload. |
| `tool_name`, `tool_input`, `tool_output`, `tool_call_id` | For tool invocations. |
| `language`, `is_executable` | Code metadata. |
| `start_char`, `end_char`, `token_count` | Positioning metrics. |
| `metadata` (JSON) | Provider-specific annotations. |

Indexes:
- `idx_spans_response`
- `idx_spans_span_type`

## Metadata & Versioning

- Schema migrations tracked via `schema_version` table.
- `backend/scripts/migrate_schema_v1_to_v2.py` upgrades legacy databases.
- WAL mode is recommended for high-volume imports (see `docs/deployment/guide.md`).

Use `backend/database.py` helpers (`insert_session`, `insert_turn`, etc.) instead of raw SQL when writing tests or scripts to keep JSON serialization consistent.
