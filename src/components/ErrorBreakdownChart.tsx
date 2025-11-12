import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PieChart } from "@/components/charts/PieChart";

interface ErrorBreakdownChartProps {
  data?: Record<string, number>;
}

const piePalette = ["#f87171", "#fb923c", "#facc15", "#38bdf8", "#818cf8", "#c084fc"];

export const ErrorBreakdownChart = ({ data }: ErrorBreakdownChartProps) => {
  const entries = Object.entries(data ?? {}).filter(([, value]) => value > 0);

  if (!entries.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>错误类型占比</CardTitle>
        </CardHeader>
        <CardContent className="flex h-64 items-center justify-center text-sm text-text-muted">
          暂无错误数据
        </CardContent>
      </Card>
    );
  }

  const chartData = {
    labels: entries.map(([label]) => label),
    datasets: [
      {
        label: "错误次数",
        data: entries.map(([, value]) => value),
        backgroundColor: entries.map((_, index) => piePalette[index % piePalette.length]),
        borderWidth: 0,
      },
    ],
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>错误类型占比</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <PieChart data={chartData} className="h-full" />
      </CardContent>
    </Card>
  );
};
