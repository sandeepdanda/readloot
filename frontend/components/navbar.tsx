"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PlusCircle,
  Search,
  RotateCcw,
  BookOpen,
  BarChart3,
  Trophy,
  Settings,
  MoreHorizontal,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/discover", label: "Discover", icon: Sparkles },
  { href: "/add", label: "Add Word", icon: PlusCircle },
  { href: "/search", label: "Search", icon: Search },
  { href: "/review", label: "Review", icon: RotateCcw },
  { href: "/books", label: "Books", icon: BookOpen },
  { href: "/stats", label: "Stats", icon: BarChart3 },
  { href: "/achievements", label: "Achievements", icon: Trophy },
  { href: "/settings", label: "Settings", icon: Settings },
];

// Mobile bottom bar shows a subset of 5 items + More menu
const mobileItems = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/add", label: "Add", icon: PlusCircle },
  { href: "/review", label: "Review", icon: RotateCcw },
  { href: "/books", label: "Books", icon: BookOpen },
  { href: "/stats", label: "Stats", icon: BarChart3 },
];

const moreItems = [
  { href: "/discover", label: "Discover", icon: Sparkles },
  { href: "/search", label: "Search", icon: Search },
  { href: "/achievements", label: "Achievements", icon: Trophy },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const [showMore, setShowMore] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  // Close the More menu when clicking outside
  useEffect(() => {
    if (!showMore) return;
    function handleClick(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setShowMore(false);
      }
    }
    document.addEventListener("pointerdown", handleClick);
    return () => document.removeEventListener("pointerdown", handleClick);
  }, [showMore]);

  const moreIsActive = moreItems.some((item) => pathname === item.href);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-60 md:flex-col md:fixed md:inset-y-0 border-r border-border bg-card">
        <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
          <span className="text-xl">📖</span>
          <span className="font-bold text-lg text-foreground">
            ReadLoot
          </span>
        </div>
        <nav aria-label="Main navigation" className="flex-1 px-2 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Mobile bottom tab bar */}
      <nav
        role="navigation"
        aria-label="Main navigation"
        className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t border-border bg-card"
      >
        {/* More menu popover */}
        {showMore && (
          <div
            ref={moreRef}
            className="absolute bottom-full right-2 mb-2 rounded-lg border border-border bg-card shadow-lg p-2 min-w-[160px]"
          >
            {moreItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setShowMore(false)}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                    active
                      ? "text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}

        <div className="flex justify-around py-2">
          {mobileItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}

          {/* More button */}
          <button
            type="button"
            aria-expanded={showMore}
            aria-haspopup="true"
            onClick={() => setShowMore((v) => !v)}
            className={cn(
              "flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring",
              showMore || moreIsActive
                ? "text-primary"
                : "text-muted-foreground",
            )}
          >
            <MoreHorizontal className="h-5 w-5" />
            More
          </button>
        </div>
      </nav>
    </>
  );
}
