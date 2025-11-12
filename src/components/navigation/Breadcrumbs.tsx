import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export const Breadcrumbs = ({ items, className }: BreadcrumbsProps) => (
  <nav className={cn("flex items-center gap-2 text-sm text-text-muted", className)}>
    {items.map((item, index) => (
      <div key={`${item.label}-${index}`} className="flex items-center gap-2">
        {item.href ? (
          <Link to={item.href} className="hover:text-text">
            {item.label}
          </Link>
        ) : (
          <span className="text-text">{item.label}</span>
        )}
        {index < items.length - 1 && <ChevronRight className="h-4 w-4" />}
      </div>
    ))}
  </nav>
);
