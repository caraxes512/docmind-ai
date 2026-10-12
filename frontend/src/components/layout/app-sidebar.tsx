"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Settings, User as UserIcon, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/profile", label: "Profile", icon: UserIcon },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const initials = (user?.full_name || user?.email || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-ink-700 bg-ink-800">
      <div className="flex h-16 items-center px-5">
        <Link href="/dashboard" className="font-display text-base font-semibold text-paper">
          DocMind AI
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded px-3 py-2 text-sm font-medium text-paper-dim transition-colors hover:bg-ink-700 hover:text-paper",
                isActive && "bg-ink-700 text-paper"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-2.5 border-t border-ink-700 p-3">
        <Avatar className="h-8 w-8">
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-paper">{user?.full_name || user?.email}</p>
        </div>
        <button
          onClick={logout}
          className="rounded p-1.5 text-paper-dim transition-colors hover:bg-ink-700 hover:text-paper"
          aria-label="Log out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}
