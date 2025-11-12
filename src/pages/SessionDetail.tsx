import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SessionHeader } from "@/components/session/SessionHeader";
import { ConversationTimeline } from "@/components/session/ConversationTimeline";
import {
  IntentAnalysisComponent,
  IntentFlowAnalysisComponent,
} from "@/components/IntentAnalysis";
import { formatDuration } from "@/utils";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { Brain } from "lucide-react";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [showIntent, setShowIntent] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const sessionQuery = useQuery({
    queryKey: ["session", id, showHistory],
    queryFn: () => apiClient.getSession(id!, { exclude_history: !showHistory }),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes - toggling back uses cached data
  });

  const intentQuery = useQuery({
    queryKey: ["session-intent", id],
    queryFn: () => apiClient.getSessionWithIntent(id!),
    enabled: !!id && showIntent,
  });

  if (sessionQuery.isLoading) {
    return (
      <div className="flex h-80 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (sessionQuery.error || !sessionQuery.data) {
    toast.error("Failed to load session details");
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-[rgb(var(--text-muted))]">
          Unable to load session. Please try again later.
        </CardContent>
      </Card>
    );
  }

  const session = sessionQuery.data;

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: "Dashboard", href: "/" },
          { label: "Sessions", href: "/session" },
          { label: session.title ?? "Session Details" },
        ]}
      />
      <div className="flex items-center justify-between">
        <div />
        <div className="flex items-center gap-3">
          <Badge variant="outline">Duration: {formatDuration(session.duration_seconds)}</Badge>
          <Button
            variant={showIntent ? "primary" : "outline"}
            leftIcon={<Brain className="h-4 w-4" />}
            onClick={() => setShowIntent((prev) => !prev)}
          >
            {showIntent ? "Hide Intent Analysis" : "Show Intent Analysis"}
          </Button>
        </div>
      </div>

      <SessionHeader session={session} />

      <ConversationTimeline
        entries={session.conversation_flow}
        showHistory={showHistory}
        onToggleHistory={() => setShowHistory(prev => !prev)}
        isLoading={sessionQuery.isFetching}
      />

      {showIntent && (
        <Card>
          <CardHeader>
            <CardTitle>Intent Analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {intentQuery.isLoading && (
              <div className="flex h-40 items-center justify-center">
                <Spinner />
              </div>
            )}

            {intentQuery.data ? (
              <>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {intentQuery.data.conversation_flow
                    .filter((turn) => turn.intent_analysis)
                    .map((turn) => (
                      <Card key={`${turn.timestamp}-${turn.type}`}>
                        <CardContent className="space-y-3 pt-6">
                          <p className="text-sm font-medium text-[rgb(var(--text))]">
                            {turn.type}
                          </p>
                          {turn.intent_analysis && (
                            <IntentAnalysisComponent analysis={turn.intent_analysis} />
                          )}
                        </CardContent>
                      </Card>
                    ))}
                </div>
                {intentQuery.data.intent_flow_analysis && (
                  <IntentFlowAnalysisComponent
                    flowAnalysis={intentQuery.data.intent_flow_analysis}
                  />
                )}
              </>
            ) : (
              !intentQuery.isLoading && (
                <p className="text-sm text-[rgb(var(--text-muted))]">
                  No intent analysis results available.
                </p>
              )
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
