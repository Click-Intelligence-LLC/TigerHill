import type { ComparisonResult } from "@/types";
import { formatDate } from "@/utils";
import { DiffViewer } from "@/components/diff/DiffViewer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface ComparisonResultProps {
  data: ComparisonResult;
}

const SummaryTile = ({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | React.ReactNode;
  accent?: string;
}) => (
  <div className="rounded-2xl border border-border bg-surface-muted px-4 py-3 text-center">
    <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
    <div className={`mt-1 text-2xl font-semibold ${accent ?? "text-text"}`}>{value}</div>
  </div>
);

const SessionCard = ({
  title,
  session,
}: {
  title: string;
  session: ComparisonResult["session_a"];
}) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
    </CardHeader>
    <CardContent className="space-y-2 text-sm">
      <div className="flex items-center justify-between">
        <span className="text-text-muted">标题</span>
        <span className="text-text">{session.title}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-text-muted">模型</span>
        <span className="text-text">{session.model ?? "未知"}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-text-muted">状态</span>
        <Badge variant={session.status === "success" ? "success" : "warning"}>
          {session.status}
        </Badge>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-text-muted">轮数</span>
        <span className="text-text">{session.total_turns ?? 0}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-text-muted">开始</span>
        <span className="text-text">{formatDate(session.start_time)}</span>
      </div>
      {session.end_time && (
        <div className="flex items-center justify-between">
          <span className="text-text-muted">结束</span>
          <span className="text-text">{formatDate(session.end_time)}</span>
        </div>
      )}
    </CardContent>
  </Card>
);

export default function ComparisonResultComponent({ data }: ComparisonResultProps) {
  const { session_a, session_b, comparison } = data;
  const change = comparison.change_summary ?? { added: 0, removed: 0, modified: 0 };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>对比结果</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <SummaryTile
            label="相似度"
            value={`${comparison.similarity.toFixed(1)}%`}
            accent="text-brand"
          />
          <SummaryTile
            label="差异数量"
            value={comparison.differences.toString()}
            accent="text-status-warning"
          />
          <SummaryTile
            label="变更摘要"
            value={
              <div className="flex items-center justify-center gap-2 text-sm">
                <Badge variant="success">+{change.added}</Badge>
                <Badge variant="warning">~{change.modified}</Badge>
                <Badge variant="danger">-{change.removed}</Badge>
              </div>
            }
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <SessionCard title="会话 A" session={session_a} />
        <SessionCard title="会话 B" session={session_b} />
      </div>

      {comparison.diff_lines.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>详细差异</CardTitle>
          </CardHeader>
          <CardContent>
            <DiffViewer diffLines={comparison.diff_lines} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
