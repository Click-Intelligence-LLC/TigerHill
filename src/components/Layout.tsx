import { useState } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  GitCompare,
  Bot,
  FileText,
  Palette,
  Menu,
  X,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@/utils";
import { useThemeStore } from "@/stores/themeStore";
import { Button } from "@/components/ui/Button";

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Sessions", href: "/session", icon: MessageSquare },
  { name: "Compare", href: "/compare", icon: GitCompare },
  { name: "Models", href: "/models", icon: Bot },
  { name: "Details", href: "/details", icon: FileText },
  { name: "Design", href: "/design-system", icon: Palette },
];

export default function Layout() {
  const location = useLocation();
  const { theme, toggleTheme } = useThemeStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isActive = (path: string) =>
    location.pathname === path || (path !== "/" && location.pathname.startsWith(path));

  return (
    <div className="min-h-screen bg-[rgb(var(--background))] text-[rgb(var(--text))]">
      <div className="flex h-screen overflow-hidden">
        {/* Minimal sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 w-56 transform",
            "border-r",
            "bg-surface",
            "border-border dark:border-[rgb(var(--border-dark))]",
            "dark:bg-[rgb(var(--surface-dark))]",
            "transition-transform duration-200 ease-out",
            "md:static md:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {/* Logo */}
          <div className="flex h-16 items-center border-b border-border px-6 dark:border-[rgb(var(--border-dark))]">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-lg font-semibold text-[rgb(var(--text))]">TigerHill</span>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto md:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-4 w-4 text-[rgb(var(--text))]" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="space-y-0.5 p-3">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand/10 text-brand dark:bg-brand/20 dark:text-brand-light"
                      : "text-[rgb(var(--text-muted))] hover:bg-[rgb(var(--surface-muted))] hover:text-[rgb(var(--text))] dark:hover:bg-[rgb(var(--surface-elevated))]",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-y-auto bg-[rgb(var(--background))]">
          {/* Header */}
          <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-surface/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-surface/60 border-border dark:border-[rgb(var(--border-dark))] dark:bg-[rgb(var(--surface-dark))]/95">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-5 w-5 text-[rgb(var(--text))]" />
              </Button>
              <h1 className="text-base font-semibold text-[rgb(var(--text))]">
                {navigation.find((item) => isActive(item.href))?.name ?? "Overview"}
              </h1>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
            >
              {theme === "dark" ? (
                <Sun className="h-5 w-5 text-[rgb(var(--text))]" />
              ) : (
                <Moon className="h-5 w-5 text-[rgb(var(--text))]" />
              )}
            </Button>
          </header>

          {/* Main content */}
          <main className="flex-1 bg-[rgb(var(--background))] p-6">
            <div className="mx-auto max-w-7xl">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
