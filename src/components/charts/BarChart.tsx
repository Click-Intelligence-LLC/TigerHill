import { useMemo, useRef } from "react";
import { Bar } from "react-chartjs-2";
import type { ChartData, ChartOptions } from "chart.js";
import { getChartTheme, registerCharts } from "./chartConfig";
import { useChartExport } from "./useChartExport";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils";
import { useThemeStore } from "@/stores/themeStore";

registerCharts();

interface BarChartProps {
  title?: string;
  data: ChartData<"bar">;
  options?: ChartOptions<"bar">;
  filename?: string;
  className?: string;
}

export const BarChart = ({
  title,
  data,
  options,
  filename = "bar-chart",
  className,
}: BarChartProps) => {
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
        <Bar
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
