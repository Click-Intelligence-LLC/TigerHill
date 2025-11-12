import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export const EmptyState = ({
  title = "No data available",
  description = "Import a session or adjust your filters to see results.",
  icon,
  action,
  className,
}: EmptyStateProps) => (
  <div
    className={cn(
      "flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface py-12 text-center shadow-card dark:bg-surface-dark",
      className,
    )}
  >
    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-background-subtle/60 text-brand">
      {icon ?? (
        <svg
          className="h-6 w-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" x2="12" y1="15" y2="3" />
        </svg>
      )}
    </div>
    <div className="space-y-1">
      <p className="text-lg font-semibold text-text">{title}</p>
      <p className="text-sm text-text-muted">{description}</p>
    </div>
    {action ? <div className="mt-2">{action}</div> : null}
  </div>
);
