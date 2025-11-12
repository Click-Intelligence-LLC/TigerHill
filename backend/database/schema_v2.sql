-- TigerHill Gemini CLI Dashboard - Schema V2
-- Deep decomposition schema with prompt components and response spans

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
    primary_model TEXT,
    primary_provider TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation turns
CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM requests with full provider/model context
CREATE TABLE IF NOT EXISTS llm_requests (
    id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    request_id TEXT,  -- Original request ID from capture
    timestamp TIMESTAMP NOT NULL,

    -- Provider and protocol information
    provider TEXT,  -- 'openai', 'anthropic', 'gemini', 'vertex', 'azure'
    endpoint_url TEXT,
    protocol TEXT,  -- 'openai_compatible', 'anthropic', 'gemini', 'custom'

    -- Model and generation parameters
    model TEXT,
    temperature REAL,
    max_tokens INTEGER,
    top_p REAL,
    top_k INTEGER,
    frequency_penalty REAL,
    presence_penalty REAL,
    stop_sequences JSON,  -- Array of stop strings
    other_params JSON,    -- Additional provider-specific params

    -- HTTP details
    method TEXT,
    headers JSON,
    raw_body JSON,  -- Complete original request body

    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decomposed prompt components
CREATE TABLE IF NOT EXISTS prompt_components (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES llm_requests(id) ON DELETE CASCADE,

    component_type TEXT NOT NULL,  -- 'system', 'user', 'assistant', 'context', 'environment', 'example', 'tool_definition', 'few_shot'
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

-- LLM responses with error handling
CREATE TABLE IF NOT EXISTS llm_responses (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES llm_requests(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,

    -- HTTP response info
    status_code INTEGER,
    headers JSON,
    response_time_ms INTEGER,

    -- Token usage and costs
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cached_tokens INTEGER,      -- For providers supporting prompt caching
    estimated_cost_usd REAL,

    -- Success/failure
    is_success BOOLEAN,
    finish_reason TEXT,  -- 'stop', 'length', 'tool_calls', 'content_filter', 'error'

    -- Error information (if failed)
    error_type TEXT,     -- 'rate_limit', 'auth_error', 'server_error', 'timeout', 'content_filter', 'invalid_request'
    error_message TEXT,
    error_code TEXT,
    retry_after INTEGER, -- For rate limit errors

    -- Raw data preservation
    raw_body JSON,

    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Response spans for decomposed output
CREATE TABLE IF NOT EXISTS response_spans (
    id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL REFERENCES llm_responses(id) ON DELETE CASCADE,

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
CREATE INDEX IF NOT EXISTS idx_turns_session_id ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_session_turn ON turns(session_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_requests_turn_id ON llm_requests(turn_id);
CREATE INDEX IF NOT EXISTS idx_requests_provider_model ON llm_requests(provider, model);
CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON llm_requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_prompt_components_request ON prompt_components(request_id, order_index);
CREATE INDEX IF NOT EXISTS idx_prompt_components_type ON prompt_components(component_type);
CREATE INDEX IF NOT EXISTS idx_responses_request_id ON llm_responses(request_id);
CREATE INDEX IF NOT EXISTS idx_responses_status ON llm_responses(is_success, error_type);
CREATE INDEX IF NOT EXISTS idx_response_spans_response ON response_spans(response_id, order_index);
CREATE INDEX IF NOT EXISTS idx_response_spans_type ON response_spans(span_type);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (2, 'Deep decomposition schema with prompt components and response spans');
