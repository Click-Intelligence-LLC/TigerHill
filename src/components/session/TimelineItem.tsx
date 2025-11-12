import { useState } from "react";
import * as React from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ConversationFlowEntry } from "@/types";
import { formatDate } from "@/utils";
import { ClipboardCopy, ChevronDown, ChevronUp, FileCode, CheckCircle } from "lucide-react";
import { toast } from "sonner";

interface TypeMetadata {
  label: string;
  emoji: string;
  badge: "outline" | "success" | "danger" | "warning" | "info";
  category: "request" | "response";
}

const TYPE_META: Record<string, TypeMetadata> = {
  // === REQUEST COMPONENTS (sent TO the LLM) ===
  system: {
    label: "System Instruction",
    emoji: "⚙️",
    badge: "outline",
    category: "request",
  },
  user: {
    label: "User Input",
    emoji: "👤",
    badge: "outline",
    category: "request",
  },
  assistant: {
    label: "Assistant",
    emoji: "🤖",
    badge: "info",
    category: "request",
  },
  tool_definition: {
    label: "Tool Definition",
    emoji: "🔧",
    badge: "outline",
    category: "request",
  },
  environment: {
    label: "Environment",
    emoji: "🌐",
    badge: "outline",
    category: "request",
  },
  context: {
    label: "Context",
    emoji: "📄",
    badge: "outline",
    category: "request",
  },
  conversation_history: {
    label: "History",
    emoji: "📜",
    badge: "outline",
    category: "request",
  },

  // === RESPONSE SPANS (received FROM the LLM) ===
  text: {
    label: "Response",
    emoji: "💬",
    badge: "info",
    category: "response",
  },
  thinking: {
    label: "Thinking",
    emoji: "🧠",
    badge: "outline",
    category: "response",
  },
  tool_call: {
    label: "Tool Call",
    emoji: "🛠️",
    badge: "warning",
    category: "response",
  },
  tool_result: {
    label: "Tool Result",
    emoji: "✅",
    badge: "success",
    category: "response",
  },
  code_block: {
    label: "Code",
    emoji: "💻",
    badge: "outline",
    category: "response",
  },
  error: {
    label: "Error",
    emoji: "⚠️",
    badge: "danger",
    category: "response",
  },
};

/**
 * Get type metadata with fallback for unknown types
 */
function getTypeMeta(type: string): TypeMetadata {
  if (TYPE_META[type]) {
    return TYPE_META[type];
  }

  // Fallback for unknown types
  if (import.meta.env.DEV) {
    console.warn(`[TimelineItem] Unknown entry type: "${type}". Using fallback metadata.`);
  }

  // Infer category from type name
  const lowerType = type.toLowerCase();
  const requestKeywords = ["system", "user", "context", "history", "example", "instruction"];
  const responseKeywords = ["text", "thinking", "output", "result", "response"];

  const isRequest = requestKeywords.some(kw => lowerType.includes(kw));
  const isResponse = responseKeywords.some(kw => lowerType.includes(kw));

  return {
    label: type,
    emoji: "💬",
    badge: "outline",
    category: isRequest ? "request" : isResponse ? "response" : "response", // default to response
  };
}

interface TimelineItemProps {
  entry: ConversationFlowEntry;
  index: number;
}

export const TimelineItem = ({ entry, index }: TimelineItemProps) => {
  const [expanded, setExpanded] = useState(entry.type === "text" || entry.type === "thinking");
  const meta = getTypeMeta(entry.type);
  const isHistory = entry.type === "conversation_history";

  // Parse tool_call and tool_result content
  const parsedContent = React.useMemo(() => {
    if (!entry.content) return null;

    if (entry.type === "tool_call" || entry.type === "tool_result") {
      try {
        return JSON.parse(entry.content);
      } catch {
        return null;
      }
    }
    return null;
  }, [entry.content, entry.type]);

  const handleCopy = async () => {
    let textToCopy = entry.content ?? "";

    // For tool_call, copy the actual code/content
    if (entry.type === "tool_call" && parsedContent?.args?.content) {
      textToCopy = parsedContent.args.content;
    }

    await navigator.clipboard.writeText(textToCopy);
    toast.success("Content copied");
  };

  return (
    <li className="relative pl-8">
      <span className={`absolute left-0 top-3 flex h-4 w-4 -translate-x-1/2 items-center justify-center rounded-full text-xs ${isHistory ? 'bg-[rgb(var(--text-muted))]/20 opacity-60' : 'bg-brand/20'}`}>
        {meta.emoji}
      </span>
      <div className={`rounded-lg border bg-surface p-4 shadow-sm border-border dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))] ${isHistory ? 'opacity-75 bg-[rgb(var(--surface-muted))]' : ''}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Badge variant={meta.badge}>{meta.label}</Badge>
            <span className="text-xs text-[rgb(var(--text-muted))]">
              {formatDate(entry.timestamp)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded((prev) => !prev)}
              rightIcon={
                expanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )
              }
            >
              {expanded ? "Collapse" : "Expand"}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Copy content"
              onClick={handleCopy}
              disabled={!entry.content}
            >
              <ClipboardCopy className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {expanded && (
          <div className="mt-3">
            {entry.type === "tool_call" && parsedContent ? (
              // Tool Call - display formatted
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-[rgb(var(--text-muted))]">
                  <FileCode className="h-4 w-4" />
                  <span className="font-medium">Tool: {parsedContent.name || entry.metadata?.tool_name}</span>
                </div>

                {parsedContent.args?.file_path && (
                  <div className="rounded-md bg-[rgb(var(--surface-muted))] p-3">
                    <div className="text-xs text-[rgb(var(--text-muted))] mb-1">File Path:</div>
                    <code className="text-sm text-[rgb(var(--text))]">{parsedContent.args.file_path}</code>
                  </div>
                )}

                {parsedContent.args?.content && (
                  <div>
                    <div className="text-xs text-[rgb(var(--text-muted))] mb-2">Content:</div>
                    <pre className="whitespace-pre-wrap rounded-md bg-[rgb(var(--surface-muted))] p-4 text-xs text-[rgb(var(--text))] overflow-x-auto max-h-96 overflow-y-auto">
                      {parsedContent.args.content}
                    </pre>
                  </div>
                )}

                {parsedContent.args && !parsedContent.args.content && !parsedContent.args.file_path && (
                  <pre className="whitespace-pre-wrap rounded-md bg-[rgb(var(--surface-muted))] p-4 text-xs text-[rgb(var(--text))]">
                    {JSON.stringify(parsedContent.args, null, 2)}
                  </pre>
                )}
              </div>
            ) : entry.type === "tool_result" && parsedContent ? (
              // Tool Result - display formatted
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-[rgb(var(--text-muted))]">
                  <CheckCircle className="h-4 w-4" />
                  <span className="font-medium">Result: {parsedContent.name || entry.metadata?.tool_name}</span>
                </div>

                {parsedContent.response?.output && (
                  <div className="rounded-md bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 p-3">
                    <div className="text-xs text-green-700 dark:text-green-300 mb-1">Output:</div>
                    <div className="text-sm text-green-900 dark:text-green-100">{parsedContent.response.output}</div>
                  </div>
                )}

                {parsedContent.response?.error && (
                  <div className="rounded-md bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 p-3">
                    <div className="text-xs text-red-700 dark:text-red-300 mb-1">Error:</div>
                    <div className="text-sm text-red-900 dark:text-red-100">{parsedContent.response.error}</div>
                  </div>
                )}

                {!parsedContent.response?.output && !parsedContent.response?.error && (
                  <pre className="whitespace-pre-wrap rounded-md bg-[rgb(var(--surface-muted))] p-4 text-xs text-[rgb(var(--text))]">
                    {JSON.stringify(parsedContent, null, 2)}
                  </pre>
                )}
              </div>
            ) : (
              // Default display for other types
              <pre className="whitespace-pre-wrap rounded-md bg-[rgb(var(--surface-muted))] p-4 text-sm text-[rgb(var(--text))]">
                {entry.content || "(No content)"}
              </pre>
            )}
          </div>
        )}
        {entry.metadata && Object.keys(entry.metadata).length > 0 && (
          <details className="mt-3 text-xs text-[rgb(var(--text-muted))]">
            <summary className="cursor-pointer">Metadata</summary>
            <pre className="mt-2 whitespace-pre-wrap rounded-md bg-[rgb(var(--surface-muted))] p-3 text-[rgb(var(--text))]">
              {JSON.stringify(entry.metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>
      {index !== -1 && <span className="absolute left-0 top-4 h-full w-px bg-border dark:bg-[rgb(var(--border-dark))]" />}
    </li>
  );
};
