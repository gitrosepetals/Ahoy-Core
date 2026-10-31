"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "@/components/ThemeProvider";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`ahoy-btn-ghost !px-3 !py-1.5 ${className}`}
      aria-label={isDark ? "Switch to light deck" : "Switch to dark deck"}
      title={isDark ? "Day watch (light)" : "Night watch (dark)"}
    >
      {isDark ? "Day watch" : "Night watch"}
    </button>
  );
}

/** Corner control when a page has no top chrome (Ship hosts its own toggle). */
export function ThemeToggleDock() {
  const pathname = usePathname() || "";
  if (pathname.startsWith("/ship")) return null;

  return (
    <div className="fixed right-3 top-3 z-50">
      <ThemeToggle />
    </div>
  );
}
