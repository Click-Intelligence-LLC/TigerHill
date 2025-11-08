-- TigerHill Database Schema v1
-- Initial schema with traces, events, and captures tables
-- Date: 2025-11-03

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- =============================================================================
-- Table: traces
-- Purpose: Store trace metadata and statistics
-- =============================================================================

CREATE TABLE IF NOT EXISTS traces (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Business key
    trace_id TEXT NOT NULL UNIQUE,

    -- Basic information
    agent_name TEXT NOT NULL,
    task_id TEXT,

    -- Time information
    start_time REAL NOT NULL,  -- Unix timestamp
    end_time REAL,              -- Unix timestamp
    duration_seconds REAL,      -- Duration in seconds

    -- Status
    status TEXT NOT NULL DEFAULT 'running'
        CHECK(status IN ('running', 'completed', 'failed')),

    -- Statistics (redundant fields for fast queries)
    total_events INTEGER DEFAULT 0 CHECK(total_events >= 0),
    llm_calls_count INTEGER DEFAULT 0 CHECK(llm_calls_count >= 0),
    total_tokens INTEGER DEFAULT 0 CHECK(total_tokens >= 0),
    total_cost_usd REAL DEFAULT 0.0 CHECK(total_cost_usd >= 0),

    -- Quality metrics (reserved for future use)
    quality_score REAL CHECK(quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)),
    cost_efficiency REAL CHECK(cost_efficiency IS NULL OR (cost_efficiency >= 0 AND cost_efficiency <= 100)),

    -- Metadata
    tags TEXT,                  -- JSON array: ["tag1", "tag2"]
    metadata TEXT,              -- JSON object: {"key": "value"}

    -- Audit fields
    created_at REAL NOT NULL DEFAULT (julianday('now')),
    updated_at REAL NOT NULL DEFAULT (julianday('now'))
);

-- =============================================================================
-- Table: events
-- Purpose: Store trace events
-- =============================================================================

CREATE TABLE IF NOT EXISTS events (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign key
    trace_id TEXT NOT NULL,

    -- Event information
    event_type TEXT NOT NULL,
    timestamp REAL NOT NULL,    -- Unix timestamp
    sequence_number INTEGER NOT NULL CHECK(sequence_number >= 0),

    -- Event data
    data TEXT NOT NULL,         -- JSON object

    -- Audit
    created_at REAL NOT NULL DEFAULT (julianday('now')),

    -- Foreign key constraint
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);

-- =============================================================================
-- Table: captures (Reserved for PromptCapture)
-- Purpose: Store LLM request/response captures
-- =============================================================================

CREATE TABLE IF NOT EXISTS captures (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Business key
    capture_id TEXT NOT NULL UNIQUE,

    -- Optional associations
    trace_id TEXT,
    event_id INTEGER,

    -- LLM information
    provider TEXT NOT NULL,     -- openai, anthropic, google
    model TEXT NOT NULL,        -- gpt-4, claude-3-opus

    -- Request information
    request TEXT NOT NULL,      -- JSON: {prompt, system_prompt, temperature, ...}

    -- Response information
    response TEXT NOT NULL,     -- JSON: {content, finish_reason, ...}

    -- Token statistics
    prompt_tokens INTEGER DEFAULT 0 CHECK(prompt_tokens >= 0),
    completion_tokens INTEGER DEFAULT 0 CHECK(completion_tokens >= 0),
    total_tokens INTEGER DEFAULT 0 CHECK(total_tokens >= 0),

    -- Cost and performance
    cost_usd REAL DEFAULT 0.0 CHECK(cost_usd >= 0),
    latency_seconds REAL DEFAULT 0.0 CHECK(latency_seconds >= 0),

    -- Tool calls (optional)
    tool_calls TEXT,            -- JSON array

    -- Time information
    timestamp REAL NOT NULL,

    -- Audit
    created_at REAL NOT NULL DEFAULT (julianday('now')),

    -- Foreign key constraints
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE SET NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL
);

-- =============================================================================
-- Table: schema_version
-- Purpose: Track database schema versions
-- =============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL DEFAULT (julianday('now')),
    description TEXT
);

-- Insert initial version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema with traces, events, and captures tables');

-- =============================================================================
-- Indexes for traces table
-- =============================================================================

-- Unique index on business key
CREATE UNIQUE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id);

-- Single column indexes (common query fields)
CREATE INDEX IF NOT EXISTS idx_traces_agent_name ON traces(agent_name);
CREATE INDEX IF NOT EXISTS idx_traces_start_time ON traces(start_time);
CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
CREATE INDEX IF NOT EXISTS idx_traces_total_tokens ON traces(total_tokens);
CREATE INDEX IF NOT EXISTS idx_traces_total_cost ON traces(total_cost_usd);
CREATE INDEX IF NOT EXISTS idx_traces_quality_score ON traces(quality_score);

-- Composite indexes (common query scenarios)
CREATE INDEX IF NOT EXISTS idx_traces_agent_status ON traces(agent_name, status);
CREATE INDEX IF NOT EXISTS idx_traces_status_time ON traces(status, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_traces_agent_time ON traces(agent_name, start_time DESC);

-- =============================================================================
-- Indexes for events table
-- =============================================================================

-- Foreign key index
CREATE INDEX IF NOT EXISTS idx_events_trace_id ON events(trace_id);

-- Query indexes
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- Composite index for trace event ordering
CREATE INDEX IF NOT EXISTS idx_events_trace_seq ON events(trace_id, sequence_number);

-- =============================================================================
-- Indexes for captures table
-- =============================================================================

-- Unique index on business key
CREATE UNIQUE INDEX IF NOT EXISTS idx_captures_capture_id ON captures(capture_id);

-- Foreign key indexes
CREATE INDEX IF NOT EXISTS idx_captures_trace_id ON captures(trace_id);
CREATE INDEX IF NOT EXISTS idx_captures_event_id ON captures(event_id);

-- Query indexes
CREATE INDEX IF NOT EXISTS idx_captures_provider ON captures(provider);
CREATE INDEX IF NOT EXISTS idx_captures_model ON captures(model);
CREATE INDEX IF NOT EXISTS idx_captures_timestamp ON captures(timestamp);
CREATE INDEX IF NOT EXISTS idx_captures_total_tokens ON captures(total_tokens);
CREATE INDEX IF NOT EXISTS idx_captures_cost ON captures(cost_usd);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_captures_provider_model ON captures(provider, model);

-- =============================================================================
-- Triggers
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_traces_timestamp
AFTER UPDATE ON traces
FOR EACH ROW
BEGIN
    UPDATE traces SET updated_at = julianday('now') WHERE id = NEW.id;
END;

-- Auto-increment total_events when inserting event
CREATE TRIGGER IF NOT EXISTS increment_event_count
AFTER INSERT ON events
FOR EACH ROW
BEGIN
    UPDATE traces
    SET total_events = total_events + 1
    WHERE trace_id = NEW.trace_id;
END;

-- Auto-decrement total_events when deleting event
CREATE TRIGGER IF NOT EXISTS decrement_event_count
AFTER DELETE ON events
FOR EACH ROW
BEGIN
    UPDATE traces
    SET total_events = total_events - 1
    WHERE trace_id = OLD.trace_id;
END;

-- =============================================================================
-- Views (optional, for convenience)
-- =============================================================================

-- View: Recent completed traces
CREATE VIEW IF NOT EXISTS recent_traces AS
SELECT
    trace_id,
    agent_name,
    start_time,
    end_time,
    duration_seconds,
    status,
    total_events,
    llm_calls_count,
    total_tokens,
    total_cost_usd,
    quality_score
FROM traces
WHERE status IN ('completed', 'failed')
ORDER BY start_time DESC;

-- View: Trace summary with event counts
CREATE VIEW IF NOT EXISTS trace_summary AS
SELECT
    t.trace_id,
    t.agent_name,
    t.status,
    t.start_time,
    t.total_events,
    COUNT(DISTINCT e.event_type) as event_types_count
FROM traces t
LEFT JOIN events e ON t.trace_id = e.trace_id
GROUP BY t.trace_id;

-- =============================================================================
-- Analysis queries
-- =============================================================================

-- Analyze tables to update statistics
ANALYZE;

-- Verify schema
SELECT 'Schema v1 initialized successfully' as status;
