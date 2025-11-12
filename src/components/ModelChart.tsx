import { ModelStats } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BarChart } from "@/components/charts/BarChart";

interface ModelChartProps {
  data: ModelStats[];
}

export default function ModelChart({ data }: ModelChartProps) {
  if (!data.length) {
    return (
      <Card>
        <CardContent className="flex h-60 items-center justify-center text-sm text-text-muted">
          暂无模型数据
        </CardContent>
      </Card>
    );
  }

  const chartData = {
    labels: data.map((item) => item.model),
    datasets: [
      {
        label: "会话数",
        data: data.map((item) => item.session_count),
        backgroundColor: "rgba(43, 140, 238, 0.7)",
      },
      {
        label: "错误数",
        data: data.map((item) => item.error_count),
        backgroundColor: "rgba(248, 113, 113, 0.7)",
      },
    ],
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>模型使用统计</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <BarChart data={chartData} />
      </CardContent>
    </Card>
  );
}
