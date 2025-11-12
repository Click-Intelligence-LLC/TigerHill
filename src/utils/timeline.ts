import { ConversationFlowEntry } from "@/types";

export interface GroupedEntry {
  type: "request" | "response";
  entries: ConversationFlowEntry[];
  timestamp: string;
}

/**
 * Type metadata for category inference
 */
const TYPE_CATEGORIES: Record<string, "request" | "response"> = {
  // Request types
  system: "request",
  user: "request",
  assistant: "request",
  tool_definition: "request",
  environment: "request",
  context: "request",
  conversation_history: "request",

  // Response types
  text: "response",
  thinking: "response",
  tool_call: "response",
  tool_result: "response",
  code_block: "response",
  error: "response",
};

/**
 * Infer category from type name for unknown types
 */
function inferCategory(type: string): "request" | "response" {
  const lowerType = type.toLowerCase();

  // Check request keywords
  const requestKeywords = ["system", "user", "context", "history", "example", "instruction"];
  if (requestKeywords.some(kw => lowerType.includes(kw))) {
    return "request";
  }

  // Check response keywords
  const responseKeywords = ["text", "thinking", "output", "result", "response"];
  if (responseKeywords.some(kw => lowerType.includes(kw))) {
    return "response";
  }

  // Default to response (most common)
  return "response";
}

/**
 * Get category for an entry type
 */
function getCategory(type: string): "request" | "response" {
  if (TYPE_CATEGORIES[type]) {
    return TYPE_CATEGORIES[type];
  }

  const inferred = inferCategory(type);

  if (import.meta.env.DEV) {
    console.log(`[Timeline] Inferred category "${inferred}" for unknown type "${type}"`);
  }

  return inferred;
}

/**
 * Group conversation flow entries into Request and Response blocks
 *
 * Groups sequential entries of the same category together.
 * For example: [system, user, text, thinking] becomes:
 * - Request block: [system, user]
 * - Response block: [text, thinking]
 *
 * @param entries - Flat list of conversation flow entries
 * @returns Grouped entries with request/response blocks
 */
export function groupEntriesByRequestResponse(
  entries: ConversationFlowEntry[]
): GroupedEntry[] {
  if (!entries || entries.length === 0) {
    return [];
  }

  const groups: GroupedEntry[] = [];
  let currentRequest: ConversationFlowEntry[] = [];
  let currentResponse: ConversationFlowEntry[] = [];

  for (const entry of entries) {
    const category = getCategory(entry.type);

    if (category === "request") {
      // Flush previous response if exists
      if (currentResponse.length > 0) {
        groups.push({
          type: "response",
          entries: currentResponse,
          timestamp: currentResponse[0].timestamp,
        });
        currentResponse = [];
      }
      currentRequest.push(entry);
    } else {
      // category === "response"
      // Flush previous request if exists
      if (currentRequest.length > 0) {
        groups.push({
          type: "request",
          entries: currentRequest,
          timestamp: currentRequest[0].timestamp,
        });
        currentRequest = [];
      }
      currentResponse.push(entry);
    }
  }

  // Flush remaining entries
  if (currentRequest.length > 0) {
    groups.push({
      type: "request",
      entries: currentRequest,
      timestamp: currentRequest[0].timestamp,
    });
  }
  if (currentResponse.length > 0) {
    groups.push({
      type: "response",
      entries: currentResponse,
      timestamp: currentResponse[0].timestamp,
    });
  }

  return groups;
}
