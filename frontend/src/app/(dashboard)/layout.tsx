"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Route protection here is deliberately a client component, not Next.js
 * middleware. Middleware runs at the edge before any client JS executes,
 * but our access token lives in memory (see api-client.ts) and the refresh
 * token in localStorage — neither is readable from middleware (no
 * server-side session, no httpOnly cookie). So an unauthenticated visitor
 * WILL receive the initial HTML/JS bundle for a dashboard route before
 * being redirected client-side; they just can't fetch any actual data,
 * since every API call requires a valid access token. This is an accepted
 * trade-off of the current auth architecture (see auth-context.tsx) — the
 * httpOnly-cookie redesign flagged there would also let middleware do this
 * check properly server-side.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink-900">
        <Skeleton className="h-8 w-40" />
      </div>
    );
  }

  if (!user) return null; // redirect effect above is about to fire

  return (
    <div className="flex h-screen bg-ink-900">
      <AppSidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
