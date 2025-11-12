import { useCallback } from "react";
import type { MutableRefObject } from "react";
import type { Chart, ChartType, DefaultDataPoint } from "chart.js";

export const useChartExport = <T extends ChartType>(
  chartRef: MutableRefObject<Chart<T, DefaultDataPoint<T>, unknown> | null>,
  filename: string,
) => {
  const downloadPNG = useCallback(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const a = document.createElement("a");
    a.href = chart.toBase64Image();
    a.download = `${filename}.png`;
    a.click();
  }, [chartRef, filename]);

  const downloadSVG = useCallback(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const canvas = chart.canvas;
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
        <foreignObject width="100%" height="100%">
          ${canvas.outerHTML}
        </foreignObject>
      </svg>`;
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }, [chartRef, filename]);

  return { downloadPNG, downloadSVG };
};
