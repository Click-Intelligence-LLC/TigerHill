import { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface ErrorMessageProps {
  title?: string;
  description?: string;
  className?: string;
  icon?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  secondaryAction?: ReactNode;
}

export const ErrorMessage = ({
  title = "Something went wrong",
  description = "We couldn’t complete your request. Please try again.",
  className,
  icon,
  actionLabel = "Try again",
  onAction,
  secondaryAction,
}: ErrorMessageProps) => (
  <div
    className={cn(
      "flex flex-col gap-4 rounded-2xl border border-status-danger/20 bg-status-danger/5 p-6 text-sm text-text shadow-card",
      className,
    )}
  >
    <div className="flex items-start gap-3">
      <span className="rounded-xl bg-status-danger/20 p-2 text-status-danger">
        {icon ?? <AlertTriangle className="h-5 w-5" aria-hidden />}
      </span>
      <div className="space-y-1">
        <p className="text-base font-semibold">{title}</p>
        <p className="text-text-muted">{description}</p>
      </div>
    </div>
    <div className="flex flex-wrap items-center gap-3">
      {onAction ? (
        <Button variant="destructive" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
      {secondaryAction}
    </div>
  </div>
);
