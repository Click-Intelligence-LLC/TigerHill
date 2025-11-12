import { ConversationFlowEntry } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { TimelineBlock } from "./TimelineBlock";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useMemo } from "react";
import { groupEntriesByRequestResponse } from "@/utils/timeline";
import { History, EyeOff } from "lucide-react";

interface ConversationTimelineProps {
  entries: ConversationFlowEntry[];
  showHistory?: boolean;
  onToggleHistory?: () => void;
  isLoading?: boolean;
}

export const ConversationTimeline = ({
  entries,
  showHistory = false,
  onToggleHistory,
  isLoading = false
}: ConversationTimelineProps) => {
  const groupedEntries = useMemo(() => groupEntriesByRequestResponse(entries), [entries]);

  if (!entries.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-[rgb(var(--text-muted))]">
          No conversation content
        </CardContent>
      </Card>
    );
  }

  const scrollToBlock = (idx: number) => {
    const node = document.querySelector(`[data-block="${idx}"]`);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <CardTitle>Conversation Flow</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          {onToggleHistory && (
            <Button
              variant={showHistory ? "primary" : "outline"}
              size="sm"
              leftIcon={showHistory ? <EyeOff className="h-4 w-4" /> : <History className="h-4 w-4" />}
              onClick={onToggleHistory}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Spinner className="h-3 w-3" />
                  <span className="ml-2">Loading...</span>
                </>
              ) : (
                showHistory ? "Hide History" : "Show History"
              )}
            </Button>
          )}
          <div className="flex flex-wrap gap-2 text-xs text-[rgb(var(--text-muted))]">
            {groupedEntries.slice(0, 6).map((group, idx) => (
              <Button
                key={`${group.timestamp}-${idx}`}
                variant="outline"
                size="sm"
                onClick={() => scrollToBlock(idx)}
              >
                {group.type === "request" ? "📤" : "📥"} #{idx + 1}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {groupedEntries.map((group, idx) => (
            <div key={`${group.timestamp}-${idx}`} data-block={idx}>
              <TimelineBlock
                type={group.type}
                entries={group.entries}
                index={idx}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
