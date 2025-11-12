import * as React from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "./Spinner";

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "destructive";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-brand text-white hover:bg-brand-dark focus-visible:ring-brand shadow-sm",
  secondary:
    "bg-surface text-[rgb(var(--text))] border border-border hover:border-brand hover:text-brand shadow-sm dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))]",
  outline:
    "border border-border text-[rgb(var(--text))] hover:border-brand hover:text-brand bg-transparent dark:border-[rgb(var(--border-dark))]",
  ghost:
    "text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text))] hover:bg-[rgb(var(--surface-muted))] dark:hover:bg-[rgb(var(--surface-elevated))]",
  destructive:
    "bg-status-danger text-white hover:bg-red-500 focus-visible:ring-status-danger shadow-sm",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-9 rounded-button px-3 text-sm",
  md: "h-10 rounded-button px-4 text-sm",
  lg: "h-11 rounded-button px-6 text-base",
  icon: "h-10 w-10 rounded-xl",
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref,
  ) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <Spinner size="sm" className="text-brand-foreground" />
      )}
      {!isLoading && leftIcon ? (
        <span className="flex items-center">{leftIcon}</span>
      ) : null}
      {children && (
        <span className={cn({ "sr-only": size === "icon" })}>{children}</span>
      )}
      {!isLoading && rightIcon ? (
        <span className="flex items-center">{rightIcon}</span>
      ) : null}
    </button>
  ),
);
Button.displayName = "Button";
