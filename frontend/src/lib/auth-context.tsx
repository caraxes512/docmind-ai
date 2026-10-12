"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiClient, ApiError, setAccessToken, setRefreshToken } from "@/lib/api-client";
import type { TokenPair, User } from "@/lib/types";

/**
 * Token storage trade-off (documented here deliberately, not just in
 * conversation): the access token lives in memory only (see api-client.ts);
 * the refresh token is persisted to localStorage so a page refresh doesn't
 * force a full re-login. This is a pragmatic default, not the ideal
 * architecture — storing a refresh token in any JS-readable storage means
 * an XSS bug anywhere in the app can steal it. The correct fix is having
 * the backend set the refresh token as an httpOnly, Secure, SameSite=strict
 * cookie directly on /auth/login and /auth/refresh responses, so the
 * frontend never touches it at all. That requires changing Step 3's auth
 * endpoint contract (Set-Cookie instead of a JSON field) and is flagged as
 * a Step 11 hardening item rather than silently shipped as-is.
 */

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const loadCurrentUser = useCallback(async () => {
    try {
      const currentUser = await apiClient.get<User>("/auth/me");
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // On a fresh page load there's no in-memory access token yet. Calling
    // /auth/me anyway is intentional: api-client's 401 handler will attempt
    // a refresh using the localStorage refresh token before this rejects,
    // so a returning user with a valid refresh token still ends up logged in.
    loadCurrentUser();
  }, [loadCurrentUser]);

  const applyTokens = (tokens: TokenPair) => {
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
  };

  const login = async (email: string, password: string) => {
    const tokens = await apiClient.post<TokenPair>("/auth/login", { email, password });
    applyTokens(tokens);
    await loadCurrentUser();
  };

  const register = async (email: string, password: string, fullName?: string) => {
    const result = await apiClient.post<{ user: User; tokens: TokenPair }>("/auth/register", {
      email,
      password,
      full_name: fullName || null,
    });
    applyTokens(result.tokens);
    setUser(result.user);
  };

  const logout = () => {
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}

export { ApiError };
