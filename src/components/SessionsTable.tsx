import { Badge } from "@/components/ui/Badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/Empty";
import { Session } from "@/types";
import { formatDate, formatDuration } from "@/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

interface SessionsTableProps {
  sessions: Session[];
  total: number;
  page: number;
  limit: number;
  isLoading: boolean;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
}

const statusVariant: Record<string, { label: string; variant: "success" | "warning" | "danger" | "info" | "outline" }> =
  {
    success: { label: "成功", variant: "success" },
    error: { label: "失败", variant: "danger" },
    timeout: { label: "超时", variant: "warning" },
    cancelled: { label: "取消", variant: "outline" },
  };

const limits = [10, 20, 50];

export default function SessionsTable({
  sessions,
  total,
  page,
  limit,
  isLoading,
  onPageChange,
  onLimitChange,
}: SessionsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / limit));

  if (isLoading) {
    return (
      <Card className="flex h-64 items-center justify-center">
        <Spinner className="text-brand" />
      </Card>
    );
  }

  if (!sessions.length) {
    return (
      <EmptyState
        title="没有符合条件的会话"
        description="调整过滤条件或导入新的会话数据。"
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>会话列表</CardTitle>
          <div className="flex items-center gap-2 text-sm text-text-muted">
            每页
            <select
              value={limit}
              onChange={(event) => onLimitChange(Number(event.target.value))}
              className="rounded-xl border border-border bg-transparent px-2 py-1 text-sm"
            >
              {limits.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            条
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-x-auto rounded-2xl border border-border">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-surface-muted text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-3 text-left">标题</th>
                <th className="px-4 py-3 text-left">模型</th>
                <th className="px-4 py-3 text-left">Provider</th>
                <th className="px-4 py-3 text-left">状态</th>
                <th className="px-4 py-3 text-left">轮数</th>
                <th className="px-4 py-3 text-left">时长</th>
                <th className="px-4 py-3 text-left">开始时间</th>
                <th className="px-4 py-3 text-left">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70 bg-surface">
              {sessions.map((session) => {
                const statusMeta =
                  statusVariant[session.status] || statusVariant.success;
                return (
                  <tr key={session.id} className="hover:bg-background-subtle/60">
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="font-medium text-text">
                          {session.title}
                        </span>
                        <span className="text-xs text-text-muted">
                          {session.id}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-text">
                      {session.model ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-sm text-text-muted">
                      {session.primary_provider ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusMeta.variant}>
                        {statusMeta.label}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-text">
                      {session.total_turns}
                    </td>
                    <td className="px-4 py-3 text-sm text-text">
                      {formatDuration(session.duration_seconds)}
                    </td>
                    <td className="px-4 py-3 text-sm text-text-muted">
                      {formatDate(session.start_time)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex flex-col gap-1">
                        <Link
                          to={`/session/${session.id}`}
                          className="text-brand hover:underline"
                        >
                          查看详情
                        </Link>
                        <Link
                          to={`/session/${session.id}/v3`}
                          className="text-blue-600 hover:underline text-xs"
                        >
                          V3 视图
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-text-muted">
            显示第{" "}
            <span className="font-medium">{(page - 1) * limit + 1}</span> 到{" "}
            <span className="font-medium">
              {Math.min(page * limit, total)}
            </span>{" "}
            条，共 <span className="font-medium">{total}</span> 条记录
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-text-muted">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page === totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
