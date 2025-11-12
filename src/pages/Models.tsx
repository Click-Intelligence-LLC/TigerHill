import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { ModelStatsResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Bot, TrendingUp, Clock, CheckCircle } from "lucide-react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { BarChart } from "@/components/charts/BarChart";

export default function ModelsPage() {
  const modelStatsQuery = useQuery<ModelStatsResponse>({
    queryKey: ["model-stats"],
    queryFn: () => apiClient.getModelStats(),
  });

  if (modelStatsQuery.isLoading) {
    return (
      <div className="flex h-80 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const stats = modelStatsQuery.data?.model_stats ?? [];
  if (!stats.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-text-muted">
          暂无模型统计数据
        </CardContent>
      </Card>
    );
  }

  const aggregate = useMemo(() => {
    const totalSessions = stats.reduce((sum, item) => sum + item.session_count, 0);
    const weightedSuccess =
      stats.reduce((sum, item) => sum + item.success_rate * item.session_count, 0) /
      (totalSessions || 1);
    const avgDuration =
      stats.reduce((sum, item) => sum + item.avg_duration * item.session_count, 0) /
      (totalSessions || 1);
    const errorTotal = stats.reduce((sum, item) => sum + item.error_count, 0);
    const topModel = stats[0]?.model ?? "未知";
    return { totalSessions, weightedSuccess, avgDuration, errorTotal, topModel };
  }, [stats]);

  const sessionChart = {
    labels: stats.map((item) => item.model),
    datasets: [
      {
        label: "会话数",
        data: stats.map((item) => item.session_count),
        backgroundColor: "rgba(43, 140, 238, 0.8)",
      },
      {
        label: "错误数",
        data: stats.map((item) => item.error_count),
        backgroundColor: "rgba(248, 113, 113, 0.8)",
      },
    ],
  };

  const successChart = {
    labels: stats.map((item) => item.model),
    datasets: [
      {
        label: "成功率 %",
        data: stats.map((item) => item.success_rate),
        backgroundColor: "rgba(16, 185, 129, 0.8)",
      },
    ],
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Dashboard", href: "/" }, { label: "模型交互" }]} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <InsightTile
          icon={<Bot className="h-5 w-5 text-brand" />}
          label="模型总数"
          value={stats.length}
        />
        <InsightTile
          icon={<TrendingUp className="h-5 w-5 text-status-success" />}
          label="平均成功率"
          value={`${aggregate.weightedSuccess.toFixed(1)}%`}
        />
        <InsightTile
          icon={<Clock className="h-5 w-5 text-status-warning" />}
          label="平均持续时间"
          value={`${Math.round(aggregate.avgDuration)}s`}
        />
        <InsightTile
          icon={<CheckCircle className="h-5 w-5 text-status-info" />}
          label="热门模型"
          value={aggregate.topModel}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>模型使用统计</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <BarChart data={sessionChart} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>模型成功率</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <BarChart data={successChart} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>模型详细指标</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-3 text-left">模型</th>
                <th className="px-4 py-3 text-left">会话数</th>
                <th className="px-4 py-3 text-left">平均时长</th>
                <th className="px-4 py-3 text-left">成功率</th>
                <th className="px-4 py-3 text-left">错误数</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-surface">
              {stats.map((model) => (
                <tr key={model.model} className="text-sm">
                  <td className="px-4 py-3 font-medium text-text">{model.model}</td>
                  <td className="px-4 py-3 text-text">
                    {model.session_count.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-text-muted">
                    {Math.round(model.avg_duration)}s
                  </td>
                  <td className="px-4 py-3 text-text">
                    {model.success_rate.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-text-danger">
                    {model.error_count.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

interface InsightTileProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}

const InsightTile = ({ icon, label, value }: InsightTileProps) => (
  <Card>
    <CardContent className="flex items-center gap-4 pt-6">
      <div className="rounded-full bg-background-subtle/60 p-3">{icon}</div>
      <div>
        <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
        <p className="text-2xl font-semibold text-text">{value}</p>
      </div>
    </CardContent>
  </Card>
);
