import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", leadingIcon, trailingIcon, ...props }, ref) => (
    <div
      className={cn(
        "flex w-full items-center gap-2 rounded-md border bg-surface px-3 py-2 text-sm shadow-sm transition focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/30",
        "border-border dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))]",
        className,
      )}
    >
      {leadingIcon ? (
        <span className="text-[rgb(var(--text-muted))]">{leadingIcon}</span>
      ) : null}
      <input
        ref={ref}
        type={type}
        className="flex-1 bg-transparent text-sm text-[rgb(var(--text))] placeholder:text-[rgb(var(--text-muted))] focus:outline-none"
        {...props}
      />
      {trailingIcon ? (
        <span className="text-[rgb(var(--text-muted))]">{trailingIcon}</span>
      ) : null}
    </div>
  ),
);
Input.displayName = "Input";
