-- TigerHill Gemini CLI Dashboard - Schema V3
-- Unified interaction model: merges requests/responses, eliminates turns table

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Core session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    status TEXT CHECK(status IN ('success', 'error', 'timeout', 'cancelled')),
    total_turns INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,  -- NEW: track total request/response count
    primary_model TEXT,
    primary_provider TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unified interactions table (replaces turns, llm_requests, llm_responses)
CREATE TABLE IF NOT EXISTS llm_interactions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number REAL NOT NULL,  -- Can be integer (1, 2) or fractional (6.1, 6.2) after split
    sequence INTEGER NOT NULL,  -- Position within turn (0, 1, 2, ...)
    type TEXT NOT NULL CHECK(type IN ('request', 'response')),

    -- Request-specific fields (NULL for responses)
    request_id TEXT,  -- Original request ID from JSON (for linking request/response)
    user_input TEXT,
    system_instruction TEXT,
    contents JSON,  -- Full contents array from Gemini
    model TEXT,
    temperature REAL,
    max_tokens INTEGER,
    top_p REAL,
    top_k INTEGER,
    generation_config JSON,  -- Full generation config object

    -- Response-specific fields (NULL for requests)
    status_code INTEGER,
    duration_ms REAL,
    finish_reason TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cached_tokens INTEGER,
    estimated_cost_usd REAL,
    is_success BOOLEAN,
    error_type TEXT,
    error_message TEXT,
    error_code TEXT,
    retry_after INTEGER,

    -- Common fields
    content TEXT,  -- Extracted content for easy access (request=user_input, response=extracted from raw_response)
    timestamp REAL NOT NULL,
    method TEXT,
    url TEXT,
    endpoint_url TEXT,
    protocol TEXT,
    provider TEXT,
    headers JSON,
    raw_request JSON,  -- Complete original request body
    raw_response JSON,  -- Complete original response body
    metadata JSON,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure uniqueness within session
    UNIQUE(session_id, turn_number, sequence)
);

-- Decomposed prompt components (updated foreign key)
CREATE TABLE IF NOT EXISTS prompt_components (
    id TEXT PRIMARY KEY,
    interaction_id TEXT NOT NULL REFERENCES llm_interactions(id) ON DELETE CASCADE,

    component_type TEXT NOT NULL,  -- 'system', 'user', 'assistant', 'conversation_history', 'context', 'environment', 'example', 'tool_definition', 'few_shot'
    role TEXT,            -- 'system', 'user', 'assistant', 'tool'
    content TEXT,
    content_json JSON,    -- For structured content (tool definitions, etc.)
    order_index INTEGER NOT NULL,  -- Ordering within request

    -- Token accounting
    token_count INTEGER,

    -- Metadata
    source TEXT,      -- Where this component came from (e.g., 'system_instruction', 'user_input', 'conversation_history')
    template_id TEXT, -- If from a template
    metadata JSON,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Response spans for decomposed output (updated foreign key)
CREATE TABLE IF NOT EXISTS response_spans (
    id TEXT PRIMARY KEY,
    interaction_id TEXT NOT NULL REFERENCES llm_interactions(id) ON DELETE CASCADE,

    span_type TEXT NOT NULL,  -- 'text', 'thinking', 'tool_call', 'tool_result', 'function_call', 'function_return', 'code_block', 'citation', 'error', 'metadata'
    order_index INTEGER NOT NULL,

    -- Content (use appropriate field based on type)
    content TEXT,           -- For text, thinking, error messages
    content_json JSON,      -- For structured content (tool calls, function results)

    -- Position in streaming response
    stream_index INTEGER,   -- Position in stream
    timestamp REAL,         -- When this span was received (for streaming)
    start_char INTEGER,     -- Character position in full response
    end_char INTEGER,

    -- Token information
    token_count INTEGER,

    -- Tool/function call specifics (if applicable)
    tool_name TEXT,
    tool_input JSON,
    tool_output JSON,
    tool_call_id TEXT,

    -- Code block specifics (if applicable)
    language TEXT,
    is_executable BOOLEAN,

    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(primary_model);
CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(primary_provider);

-- Interaction indexes (optimized for v3 queries)
CREATE INDEX IF NOT EXISTS idx_interactions_session ON llm_interactions(session_id, turn_number, sequence);
CREATE INDEX IF NOT EXISTS idx_interactions_turn ON llm_interactions(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_interactions_request_id ON llm_interactions(request_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON llm_interactions(type);
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON llm_interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_interactions_provider_model ON llm_interactions(provider, model);

-- Component and span indexes
CREATE INDEX IF NOT EXISTS idx_prompt_components_interaction ON prompt_components(interaction_id, order_index);
CREATE INDEX IF NOT EXISTS idx_prompt_components_type ON prompt_components(component_type);
CREATE INDEX IF NOT EXISTS idx_response_spans_interaction ON response_spans(interaction_id, order_index);
CREATE INDEX IF NOT EXISTS idx_response_spans_type ON response_spans(span_type);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (3, 'Unified interaction model: merged requests/responses, eliminated turns table');
