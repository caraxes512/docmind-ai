"use client";

import { useState } from "react";
import { Github } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient, ApiError } from "@/lib/api-client";

export default function SettingsPage() {
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnectGithub = async () => {
    // A full-page browser redirect can't carry an Authorization header, so
    // we first fetch the authorize URL as a normal authenticated request
    // (the backend embeds our user id in the OAuth state token server-side
    // — see GET /auth/github/authorize-url), THEN navigate. The actual
    // redirect to GitHub never needs to carry auth itself.
    setError(null);
    setIsConnecting(true);
    try {
      const { url } = await apiClient.get<{ url: string }>("/auth/github/authorize-url");
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't start GitHub connection. Please try again.");
      setIsConnecting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <h1 className="mb-8 font-display text-2xl font-medium text-paper">Settings</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Github className="h-5 w-5 text-paper" />
            <CardTitle>GitHub connection</CardTitle>
          </div>
          <CardDescription>
            Connect GitHub to clone private repositories and enable AI-generated commit messages, PR
            descriptions, and release notes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {user?.github_username ? (
            <div className="flex items-center justify-between">
              <Badge variant="success">Connected as {user.github_username}</Badge>
              <Button variant="outline" size="sm">
                Disconnect
              </Button>
            </div>
          ) : (
            <>
              <Button size="sm" onClick={handleConnectGithub} disabled={isConnecting}>
                <Github className="h-4 w-4" /> {isConnecting ? "Redirecting…" : "Connect GitHub"}
              </Button>
              {error && <p className="mt-2 text-sm text-danger">{error}</p>}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
