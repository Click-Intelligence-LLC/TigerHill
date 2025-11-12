import { cn } from "@/lib/utils";

type SpinnerSize = "sm" | "md" | "lg";

const sizeMap: Record<SpinnerSize, string> = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-8 w-8",
};

export interface SpinnerProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: SpinnerSize;
}

export const Spinner = ({
  size = "md",
  className,
  ...props
}: SpinnerProps) => (
  <span
    role="status"
    aria-live="polite"
    className={cn(
      "inline-flex shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent",
      sizeMap[size],
      className,
    )}
    {...props}
  />
);
