import { TrendData } from "@/types";
import { LineChart } from "@/components/charts/LineChart";
import { format } from "date-fns";

interface TrendChartProps {
  data?: TrendData[];
}

export default function TrendChart({ data }: TrendChartProps) {
  if (!data?.length) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-text-muted">
        暂无趋势数据
      </div>
    );
  }

  const chartData = {
    labels: data.map((item) => format(new Date(item.date), "MM/dd")),
    datasets: [
      {
        label: "会话数量",
        data: data.map((item) => item.session_count),
        borderColor: "rgb(43, 140, 238)",
        backgroundColor: "rgba(43, 140, 238, 0.1)",
        tension: 0.4,
      },
      {
        label: "平均时长 (秒)",
        data: data.map((item) => item.avg_duration),
        borderColor: "rgb(16, 185, 129)",
        backgroundColor: "rgba(16, 185, 129, 0.1)",
        tension: 0.4,
        yAxisID: "y1" as const,
      },
    ],
  };

  const options = {
    maintainAspectRatio: false,
    scales: {
      y1: {
        position: "right" as const,
        grid: { drawOnChartArea: false },
      },
    },
  };

  return (
    <div className="h-80">
      <LineChart title="会话趋势 (最近7天)" data={chartData} options={options} />
    </div>
  );
}
