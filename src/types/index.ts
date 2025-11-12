// 基础枚举与类型
export type SessionStatus = 'success' | 'error' | 'timeout' | 'cancelled';
export type SessionSort = 'newest' | 'oldest' | 'longest' | 'shortest';

// 会话及嵌套结构
export interface Session {
  id: string;
  title: string;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  status: SessionStatus;
  total_turns: number;
  total_interactions?: number; // V3 field: total number of interactions (requests + responses)
  primary_model?: string;
  primary_provider?: string;
  model?: string; // legacy alias for UI
  provider?: string; // derived alias
  metadata?: Record<string, any>;
}

export interface ConversationTurn {
  type: 'user_input' | 'ai_response' | 'tool_call' | 'error' | 'function_return' | string;
  timestamp: string;
  content?: string | null;
  metadata?: Record<string, any>;
}

export type ConversationFlowEntry = ConversationTurn;

export interface PromptComponent {
  id: string;
  request_id: string;
  component_type: string;
  role?: string;
  content?: string;
  content_json?: Record<string, any>;
  order_index: number;
  token_count?: number;
  source?: string;
  template_id?: string;
  metadata?: Record<string, any>;
}

export interface ResponseSpan {
  id: string;
  response_id: string;
  span_type: string;
  order_index: number;
  content?: string;
  content_json?: Record<string, any>;
  stream_index?: number;
  timestamp?: number;
  start_char?: number;
  end_char?: number;
  token_count?: number;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: Record<string, any>;
  tool_call_id?: string;
  language?: string;
  is_executable?: boolean;
  metadata?: Record<string, any>;
}

export interface LLMResponse {
  id: string;
  request_id: string;
  timestamp: string;
  status_code?: number;
  headers?: Record<string, any>;
  response_time_ms?: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cached_tokens?: number;
  estimated_cost_usd?: number;
  is_success?: boolean;
  finish_reason?: string;
  error_type?: string;
  error_message?: string;
  error_code?: string;
  retry_after?: number;
  raw_body?: Record<string, any>;
  metadata?: Record<string, any>;
  spans?: ResponseSpan[];
}

export interface RequestResponse {
  id: string;
  method: string;
  url: string;
  endpoint_url?: string;
  provider?: string;
  model?: string;
  headers?: Record<string, any> | null;
  request_headers?: Record<string, any> | null;
  request_body?: any;
  raw_body?: any;
  status_code?: number;
  response_headers?: Record<string, any> | null;
  response_body?: any;
  response_time_ms?: number;
  timestamp: string;
  components?: PromptComponent[];
  response?: LLMResponse;
  metadata?: Record<string, any>;
}

export interface Turn {
  id: string;
  session_id: string;
  turn_number: number;
  timestamp: string;
  metadata?: Record<string, any>;
  requests: RequestResponse[];
}

export interface SessionTurnsResponse {
  session: Session;
  turns: Turn[];
  page: number;
  limit: number;
  total_turns: number;
}

export interface SessionDetail extends Session {
  conversation_flow: ConversationFlowEntry[];
  turns: Turn[];
}

export interface SessionsResponse {
  sessions: Session[];
  total: number;
  limit: number;
  next_cursor?: string | null;
  sort?: SessionSort;
  page?: number;
}

export interface TrendsResponse {
  trends: TrendData[];
}

export interface TrendData {
  date: string;
  session_count: number;
  avg_duration: number;
}

export interface ModelStats {
  model: string;
  session_count: number;
  avg_duration: number;
  success_rate: number;
  error_count: number;
}

export interface ModelStatsResponse {
  model_stats: ModelStats[];
}

export interface SessionDetailsResponse {
  session?: Session;
  request_responses: RequestResponse[];
}

export interface StatsOverview {
  total_sessions: number;
  avg_duration: string;
  top_model: string;
  success_rate: number;
  session_volume_last_7_days: number;
  session_volume_change: number;
  response_time_ms?: {
    p50: number | null;
    p90: number | null;
    p99: number | null;
  };
  error_breakdown?: Record<string, number>;
}

export interface ComparisonChangeSummary {
  added: number;
  removed: number;
  modified: number;
}

export interface ComparisonResult {
  session_a: Session;
  session_b: Session;
  comparison: {
    similarity: number;
    differences: number;
    diff_lines: string[];
    change_summary?: ComparisonChangeSummary;
  };
}

export interface ImportResponse {
  success: boolean;
  imported_files: number;
  total_files: number;
  errors: string[];
  skipped_files?: number;
}

export interface ImportJobStatus {
  id: string;
  status: string;
  processed_files: number;
  total_files: number;
  skipped_files: number;
  errors: string[];
  started_at: string;
  finished_at?: string;
  summary?: Record<string, any>;
}

// 意图分析类型
export interface IntentUnit {
  id: string;
  intent_type: string;
  confidence: number;
  complexity_score: number;
  tokens: number;
  start_pos: number;
  end_pos: number;
  metadata?: Record<string, any>;
}

export interface IntentAnalysis {
  primary_intent: string;
  confidence: number;
  complexity_score: number;
  total_tokens: number;
  intent_diversity: number;
  intent_units: IntentUnit[];
}

export interface IntentFlowAnalysis {
  transition_matrix: Record<string, Record<string, number>>;
  transition_patterns: IntentTransitionPattern[];
  intent_distribution: Record<string, number>;
}

export interface IntentTransitionPattern {
  from_intent: string;
  to_intent: string;
  frequency: number;
  confidence: number;
}

export interface ConversationTurnWithIntent extends ConversationTurn {
  intent_analysis?: IntentAnalysis;
}

export interface SessionDetailWithIntent extends SessionDetail {
  conversation_flow: ConversationTurnWithIntent[];
  intent_flow_analysis?: IntentFlowAnalysis;
}

export interface IntentDiff {
  added_intents: IntentUnit[];
  removed_intents: IntentUnit[];
  modified_intents: Array<{
    old_intent: IntentUnit;
    new_intent: IntentUnit;
  }>;
  intent_transitions: {
    old_pattern: IntentTransitionPattern | null;
    new_pattern: IntentTransitionPattern | null;
  }[];
}

// ====================================================================
// V3 Unified Interaction Model Types
// ====================================================================

/**
 * Unified interaction type (V3 schema)
 * Represents both requests and responses in a single table with type discrimination
 */
export interface Interaction {
  // Common fields
  id: string;
  session_id: string;
  turn_number: number;
  sequence: number;
  type: 'request' | 'response';
  timestamp: number;

  // Request-specific fields (null for responses)
  request_id?: string;
  user_input?: string;
  system_instruction?: string;
  contents?: Array<Record<string, any>>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
  generation_config?: Record<string, any>;

  // Response-specific fields (null for requests)
  status_code?: number;
  duration_ms?: number;
  finish_reason?: string;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cached_tokens?: number;
  estimated_cost_usd?: number;
  is_success?: boolean;
  error_type?: string;
  error_message?: string;
  error_code?: string;
  retry_after?: number;

  // HTTP fields
  method?: string;
  url?: string;
  endpoint_url?: string;
  protocol?: string;
  provider?: string;
  headers?: Record<string, any>;
  raw_request?: Record<string, any>;
  raw_response?: Record<string, any>;
  metadata?: Record<string, any>;
}

/**
 * Request interaction with components (V3 schema)
 */
export interface RequestInteraction extends Interaction {
  type: 'request';
  components?: PromptComponent[];
}

/**
 * Response interaction with spans (V3 schema)
 */
export interface ResponseInteraction extends Interaction {
  type: 'response';
  spans?: ResponseSpan[];
}

/**
 * V3 Session detail with interaction stats
 */
export interface SessionV3 extends Session {
  stats?: {
    total_interactions: number;
    request_count: number;
    response_count: number;
  };
}

/**
 * V3 Interactions list response
 */
export interface SessionInteractionsResponse {
  interactions: Interaction[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * V3 Turn interactions response
 */
export interface TurnInteractionsResponse {
  session_id: string;
  turn_number: number;
  interactions: Interaction[];
}

/**
 * V3 Session stats response
 */
export interface SessionStatsResponse {
  session_id: string;
  overall: {
    total_turns: number;
    total_interactions: number;
    total_input_tokens: number;
    total_output_tokens: number;
  };
  per_turn: Array<{
    turn_number: number;
    interaction_count: number;
    request_count: number;
    response_count: number;
    total_input_tokens: number;
    total_output_tokens: number;
  }>;
}

/**
 * Grouped interactions by turn (for UI display)
 */
export interface TurnGroup {
  turn_number: number;
  interactions: Interaction[];
  request_count: number;
  response_count: number;
}
