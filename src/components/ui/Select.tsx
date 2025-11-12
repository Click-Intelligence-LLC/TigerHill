import * as React from "react";
import { cn } from "@/lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  helperText?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, label, helperText, ...props }, ref) => (
    <label className="flex w-full flex-col gap-1 text-sm">
      {label ? (
        <span className="text-xs font-medium uppercase tracking-wide text-[rgb(var(--text-muted))]">
          {label}
        </span>
      ) : null}
      <div
        className={cn(
          "rounded-md border bg-surface px-3 py-2 text-sm shadow-sm focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/30",
          "border-border dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))]",
        )}
      >
        <select
          ref={ref}
          className={cn(
            "w-full bg-transparent text-sm text-[rgb(var(--text))] outline-none",
            className,
          )}
          {...props}
        >
          {children}
        </select>
      </div>
      {helperText ? (
        <span className="text-xs text-[rgb(var(--text-muted))]">{helperText}</span>
      ) : null}
    </label>
  ),
);
Select.displayName = "Select";
