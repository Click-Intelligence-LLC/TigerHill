import { useState, memo } from "react";
import { ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { TimelineItem } from "./TimelineItem";
import { ConversationFlowEntry } from "@/types";
import { cn } from "@/lib/utils";

export interface TimelineBlockProps {
  type: "request" | "response";
  entries: ConversationFlowEntry[];
  index: number;
  defaultExpanded?: boolean;
}

const BLOCK_CONFIG = {
  request: {
    label: "Request",
    icon: "📤",
    bgColor: "bg-blue-50 dark:bg-blue-500/10",
    borderColor: "border-blue-200 dark:border-blue-500/30",
    textColor: "text-blue-700 dark:text-blue-300",
  },
  response: {
    label: "Response",
    icon: "📥",
    bgColor: "bg-green-50 dark:bg-green-500/10",
    borderColor: "border-green-200 dark:border-green-500/30",
    textColor: "text-green-700 dark:text-green-300",
  },
};

const TimelineBlockComponent = ({
  type,
  entries,
  index,
  defaultExpanded = true,
}: TimelineBlockProps) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const config = BLOCK_CONFIG[type];

  return (
    <div className={cn("rounded-lg border", config.borderColor)}>
      {/* Collapsible Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex w-full items-center justify-between p-4 transition-colors duration-200",
          config.bgColor,
          "hover:opacity-80"
        )}
        aria-expanded={expanded}
        aria-label={`${config.label} block ${index + 1}`}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg" aria-hidden="true">{config.icon}</span>
          <span className={cn("font-medium", config.textColor)}>
            {config.label} #{index + 1}
          </span>
          <Badge variant="outline" className="text-xs">
            {entries.length} {entries.length === 1 ? "item" : "items"}
          </Badge>
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform duration-200",
            config.textColor,
            expanded && "rotate-180"
          )}
          aria-hidden="true"
        />
      </button>

      {/* Entries - only render when expanded for performance */}
      {expanded && (
        <div className="space-y-3 p-4">
          <ol className="space-y-4">
            {entries.map((entry, idx) => (
              <TimelineItem
                key={`${entry.timestamp}-${idx}`}
                entry={entry}
                index={idx}
              />
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

// Memoize to prevent unnecessary re-renders
export const TimelineBlock = memo(TimelineBlockComponent);
