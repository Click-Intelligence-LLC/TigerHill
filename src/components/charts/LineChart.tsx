import { useMemo, useRef } from "react";
import { Line } from "react-chartjs-2";
import type { ChartData, ChartOptions } from "chart.js";
import { getChartTheme, registerCharts } from "./chartConfig";
import { useChartExport } from "./useChartExport";
import { Button } from "@/components/ui/Button";
import { useThemeStore } from "@/stores/themeStore";
import { cn } from "@/utils";

registerCharts();

interface LineChartProps {
  title?: string;
  data: ChartData<"line">;
  options?: ChartOptions<"line">;
  filename?: string;
  className?: string;
}

export const LineChart = ({
  title,
  data,
  options,
  filename = "line-chart",
  className,
}: LineChartProps) => {
  const chartRef = useRef(null);
  const { downloadPNG, downloadSVG } = useChartExport(chartRef, filename);
  const mode = useThemeStore((state) => state.theme);
  const palette = useMemo(() => getChartTheme(), [mode]);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        {title && <p className="text-sm font-semibold text-text">{title}</p>}
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={downloadPNG}>
            导出 PNG
          </Button>
          <Button variant="ghost" size="sm" onClick={downloadSVG}>
            导出 SVG
          </Button>
        </div>
      </div>
      <div className="relative h-72">
        <Line
          ref={chartRef}
          data={data}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color: palette.legendColor } },
            },
            scales: {
              x: {
                ticks: { color: palette.axisColor },
                grid: { color: palette.gridColor },
              },
              y: {
                ticks: { color: palette.axisColor },
                grid: { color: palette.gridColor },
              },
            },
            ...options,
          }}
        />
      </div>
    </div>
  );
};
