import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Title,
} from "chart.js";

let registered = false;

export const registerCharts = () => {
  if (registered) return;
  ChartJS.register(
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    BarElement,
    ArcElement,
    Tooltip,
    Legend,
    Title,
  );
  registered = true;
};

const rgbFromVariable = (value: string | null, alpha?: number) => {
  if (!value) return alpha != null ? `rgba(148,163,184,${alpha})` : "rgb(148,163,184)";
  const trimmed = value.trim();
  if (!trimmed) {
    return alpha != null ? `rgba(148,163,184,${alpha})` : "rgb(148,163,184)";
  }
  if (alpha == null) {
    return `rgb(${trimmed})`;
  }
  const parts = trimmed.split(/\s+/).map((part) => part.trim());
  return `rgba(${parts.join(",")},${alpha})`;
};

export const getChartTheme = () => {
  if (typeof window === "undefined") {
    return {
      axisColor: "rgb(148,163,184)",
      gridColor: "rgba(226,232,240,0.4)",
      legendColor: "rgb(148,163,184)",
    };
  }
  const root = getComputedStyle(document.documentElement);
  const textMuted = root.getPropertyValue("--text-muted");
  const border = root.getPropertyValue("--border");
  return {
    axisColor: rgbFromVariable(textMuted),
    gridColor: rgbFromVariable(border, 0.35),
    legendColor: rgbFromVariable(textMuted),
  };
};
