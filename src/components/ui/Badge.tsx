import { cn } from "@/lib/utils";

type BadgeVariant =
  | "default"
  | "outline"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "model";  // For model names (Gemini, etc.)

const variantMap: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  outline: "border border-gray-200 text-gray-800 dark:border-white/10 dark:text-white",
  success: "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400",
  warning: "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-400",
  danger: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
  info: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
  // Model badge from stitch design
  model: "bg-blue-100 text-blue-700 dark:bg-primary/20 dark:text-primary",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export const Badge = ({
  className,
  children,
  variant = "default",
  ...props
}: BadgeProps) => (
  <span
    className={cn(
      // Updated to match stitch design: rounded-md, not uppercase
      "inline-flex items-center rounded-md px-2 py-1 text-xs font-medium",
      variantMap[variant],
      className,
    )}
    {...props}
  >
    {children}
  </span>
);
