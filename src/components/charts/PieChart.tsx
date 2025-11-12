import { useMemo, useRef } from "react";
import { Doughnut } from "react-chartjs-2";
import type { ChartData, ChartOptions } from "chart.js";
import { getChartTheme, registerCharts } from "./chartConfig";
import { useChartExport } from "./useChartExport";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils";
import { useThemeStore } from "@/stores/themeStore";

registerCharts();

interface PieChartProps {
  title?: string;
  data: ChartData<"doughnut">;
  options?: ChartOptions<"doughnut">;
  filename?: string;
  className?: string;
}

export const PieChart = ({
  title,
  data,
  options,
  filename = "pie-chart",
  className,
}: PieChartProps) => {
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
        <Doughnut
          ref={chartRef}
          data={data}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: "right", labels: { color: palette.legendColor } },
            },
            ...options,
          }}
        />
      </div>
    </div>
  );
};
