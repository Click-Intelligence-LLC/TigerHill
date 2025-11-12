import * as React from "react";
import { cn } from "@/lib/utils";

export interface StatsCardProps {
  label: string;
  value: string | number;
  trend?: {
    value: number;
    isPositive?: boolean;
  };
  className?: string;
}

/**
 * StatsCard component matching stitch design
 * Displays a metric with label and optional trend indicator
 */
export const StatsCard: React.FC<StatsCardProps> = ({
  label,
  value,
  trend,
  className,
}) => {
  return (
    <div
      className={cn(
        // Minimal card design
        "flex flex-col gap-1 rounded-lg border bg-surface p-4",
        "border-border dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))]",
        className,
      )}
    >
      {/* Label */}
      <p className="text-sm font-medium text-[rgb(var(--text-muted))]">
        {label}
      </p>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <p className="text-2xl font-semibold text-[rgb(var(--text))]">
          {value}
        </p>

        {/* Trend indicator */}
        {trend && (
          <span
            className={cn(
              "text-sm font-medium",
              trend.isPositive !== false
                ? "text-status-success"
                : "text-status-danger",
            )}
          >
            {trend.isPositive !== false ? "↑" : "↓"}
            {Math.abs(trend.value)}%
          </span>
        )}
      </div>
    </div>
  );
};

StatsCard.displayName = "StatsCard";

export default StatsCard;
