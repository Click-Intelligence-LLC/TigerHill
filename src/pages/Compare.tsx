import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import type { IntentDiff, SessionsResponse } from "@/types";
import { GitCompare, Brain, Shuffle } from "lucide-react";
import SessionSelector from "@/components/SessionSelector";
import ComparisonResult from "@/components/ComparisonResult";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export default function ComparePage() {
  const [sessionId1, setSessionId1] = useState("");
  const [sessionId2, setSessionId2] = useState("");
  const [intentPanelOpen, setIntentPanelOpen] = useState(false);
  const [compareTrigger, setCompareTrigger] = useState(0);
  const [intentTrigger, setIntentTrigger] = useState(0);

  const sessionsQuery = useQuery<SessionsResponse>({
    queryKey: ["sessions", { limit: 200 }],
    queryFn: () => apiClient.getSessionsV3({ limit: 200, offset: 0 }),
  });

  const sessions = sessionsQuery.data?.sessions ?? [];
  const canCompare = sessionId1 && sessionId2 && sessionId1 !== sessionId2;

  const comparisonQuery = useQuery({
    queryKey: ["comparison", sessionId1, sessionId2, compareTrigger],
    queryFn: () => apiClient.compareSessions(sessionId1, sessionId2),
    enabled: !!canCompare && compareTrigger > 0,
  });

  const intentComparisonQuery = useQuery<{ intent_diff: IntentDiff }>({
    queryKey: ["intent-comparison", sessionId1, sessionId2, intentTrigger],
    queryFn: () => apiClient.compareSessionIntents(sessionId1, sessionId2),
    enabled: !!canCompare && intentPanelOpen && intentTrigger > 0,
  });


  const handleCompare = () => {
    if (!canCompare) {
      toast.error("请选择两个不同的会话进行对比");
      return;
    }
    setCompareTrigger((prev) => prev + 1);
  };

  const handleToggleIntent = () => {
    if (!canCompare) {
      toast.error("请先选择两个会话");
      return;
    }
    setIntentPanelOpen((prev) => !prev);
    if (!intentPanelOpen) {
      setIntentTrigger((prev) => prev + 1);
    }
  };

  const handleSwap = () => {
    setSessionId1(sessionId2);
    setSessionId2(sessionId1);
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Dashboard", href: "/" }, { label: "差异对比" }]} />

      <Card>
        <CardHeader>
          <CardTitle>选择要对比的会话</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <SessionSelector
              label="会话 A"
              sessions={sessions}
              selectedSessionId={sessionId1}
              onSessionChange={setSessionId1}
            />
            <SessionSelector
              label="会话 B"
              sessions={sessions}
              selectedSessionId={sessionId2}
              onSessionChange={setSessionId2}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              leftIcon={<Shuffle className="h-4 w-4" />}
              onClick={handleSwap}
              disabled={!sessionId1 || !sessionId2}
            >
              交换
            </Button>
            <Button
              variant="primary"
              leftIcon={<GitCompare className="h-4 w-4" />}
              onClick={handleCompare}
              disabled={comparisonQuery.isFetching}
            >
              {comparisonQuery.isFetching ? "正在对比…" : "开始对比"}
            </Button>
            <Button
              variant={intentPanelOpen ? "primary" : "outline"}
              leftIcon={<Brain className="h-4 w-4" />}
              onClick={handleToggleIntent}
            >
              {intentPanelOpen ? "隐藏意图对比" : "显示意图对比"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {comparisonQuery.isFetching && (
        <Card>
          <CardContent className="flex h-40 items-center justify-center">
            <Spinner />
          </CardContent>
        </Card>
      )}

      {comparisonQuery.data && (
        <div className="space-y-4">
          <ComparisonSummary data={comparisonQuery.data} />
          <ComparisonResult data={comparisonQuery.data} />
        </div>
      )}

      {intentPanelOpen && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-status-info" />
              意图对比
            </CardTitle>
          </CardHeader>
          <CardContent>
            {intentComparisonQuery.isFetching && (
              <div className="flex h-32 items-center justify-center">
                <Spinner />
              </div>
            )}
            {intentComparisonQuery.data ? (
              <div className="space-y-6">
                <IntentDiffGrid
                  title="新增意图"
                  variant="success"
                  items={intentComparisonQuery.data.intent_diff.added_intents}
                />
                <IntentDiffGrid
                  title="删除意图"
                  variant="danger"
                  items={intentComparisonQuery.data.intent_diff.removed_intents}
                />
                <IntentDiffGrid
                  title="修改意图"
                  variant="warning"
                  items={intentComparisonQuery.data.intent_diff.modified_intents.map(
                    (item) => item.new_intent || item.old_intent,
                  )}
                />
              </div>
            ) : (
              !intentComparisonQuery.isFetching && (
                <p className="text-sm text-text-muted">暂无意图差异数据。</p>
              )
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface ComparisonSummaryProps {
  data: Awaited<ReturnType<typeof apiClient.compareSessions>>;
}

const ComparisonSummary = ({ data }: ComparisonSummaryProps) => {
  const summary = data.comparison;
  return (
    <Card>
      <CardContent className="grid gap-4 pt-6 md:grid-cols-3">
        <SummaryTile
          label="相似度"
          value={`${summary.similarity.toFixed(1)}%`}
          accent="text-brand"
        />
        <SummaryTile
          label="差异数量"
          value={summary.differences.toString()}
          accent="text-status-warning"
        />
        <SummaryTile
          label="变更概览"
          value={
            <div className="flex items-center gap-2 text-sm">
              <Badge variant="success">
                +{summary.change_summary?.added ?? 0}
              </Badge>
              <Badge variant="warning">
                ~{summary.change_summary?.modified ?? 0}
              </Badge>
              <Badge variant="danger">
                -{summary.change_summary?.removed ?? 0}
              </Badge>
            </div>
          }
        />
      </CardContent>
    </Card>
  );
};

interface SummaryTileProps {
  label: string;
  value: string | React.ReactNode;
  accent?: string;
}

const SummaryTile = ({ label, value, accent }: SummaryTileProps) => (
  <div className="rounded-2xl border border-border bg-background-subtle/60 p-4">
    <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
    <div className={`mt-2 text-2xl font-semibold ${accent ?? "text-text"}`}>
      {value}
    </div>
  </div>
);

interface IntentDiffGridProps {
  title: string;
  variant: "success" | "danger" | "warning";
  items: IntentDiff["added_intents"];
}

const IntentDiffGrid = ({ title, variant, items }: IntentDiffGridProps) => {
  if (!items?.length) return null;
  const badgeVariant =
    variant === "success" ? "success" : variant === "danger" ? "danger" : "warning";
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-text">{title}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((unit) => (
          <div
            key={unit?.id ?? `${unit?.intent_type}-${unit?.start_pos}`}
            className="rounded-2xl border border-border bg-background-subtle/60 p-4"
          >
            <div className="flex items-center justify-between text-sm">
              <Badge variant={badgeVariant}>{unit?.intent_type ?? "未知"}</Badge>
              <span className="text-text-muted">
                信心 {(((unit?.confidence ?? 0) * 100).toFixed(1))}%
              </span>
            </div>
            <div className="mt-2 text-xs text-text-muted">
              Tokens {unit?.tokens ?? 0} · 复杂度{" "}
              {unit?.complexity_score !== undefined
                ? unit.complexity_score.toFixed(2)
                : "—"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
