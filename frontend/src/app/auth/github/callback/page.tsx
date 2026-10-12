"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { apiClient, ApiError, setAccessToken, setRefreshToken } from "@/lib/api-client";
import type { TokenPair, User } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";

function GitHubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return; // StrictMode double-invoke guard -- this exchange is one-shot
    hasRun.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setError("Missing code or state from GitHub's redirect.");
      return;
    }

    apiClient
      .post<{ user: User; tokens: TokenPair }>("/auth/github/callback", { code, state })
      .then(({ tokens }) => {
        setAccessToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
        router.push("/dashboard");
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "GitHub connection failed. Please try again.");
      });
  }, [searchParams, router]);

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
        {error ? (
          <>
            <p className="text-sm text-danger">{error}</p>
            <Link href="/login" className="text-sm text-blueprint hover:underline">
              Back to login
            </Link>
          </>
        ) : (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-blueprint" />
            <p className="text-sm text-paper-dim">Connecting your GitHub account…</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function GitHubCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-blueprint-canvas px-4">
      <Suspense
        fallback={
          <Card className="w-full max-w-sm">
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-blueprint" />
              <p className="text-sm text-paper-dim">Loading…</p>
            </CardContent>
          </Card>
        }
      >
        <GitHubCallbackContent />
      </Suspense>
    </div>
  );
}
