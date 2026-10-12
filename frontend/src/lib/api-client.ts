import type { TokenPair } from "@/lib/types";

// Base path is same-origin "/api/v1" — next.config.mjs rewrites this to the
// FastAPI backend in local dev, so the browser never needs backend CORS
// beyond what Step 5 already configured for direct (non-proxied) access.
const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// In-memory token store. Deliberately NOT localStorage for the access token
// (reduces the XSS blast radius — a compromised page can't read tokens out
// of a JS variable it doesn't have a reference to, whereas localStorage is
// readable by any script on the page). The trade-off: a hard page refresh
// loses the in-memory access token, so AuthProvider re-authenticates via
// the refresh token on mount. The refresh token itself is currently kept in
// localStorage as a pragmatic default — see the note in auth-context.tsx for
// why this is a known, flagged compromise rather than an oversight.
let inMemoryAccessToken: string | null = null;

export function setAccessToken(token: string | null) {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("docmind_refresh_token");
}

export function setRefreshToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("docmind_refresh_token", token);
  else window.localStorage.removeItem("docmind_refresh_token");
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  // Coalesce concurrent 401s into a single refresh call rather than firing
  // one refresh request per failed request (common when several queries
  // land on an expired token at the same moment after a tab wakes from sleep).
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const data: TokenPair = await res.json();
        setAccessToken(data.access_token);
        setRefreshToken(data.refresh_token);
        return data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
  skipAuthRefresh?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isFormData = false, skipAuthRefresh = false } = options;

  const headers: Record<string, string> = {};
  if (!isFormData) headers["Content-Type"] = "application/json";
  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  });

  if (res.status === 401 && !skipAuthRefresh) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, { ...options, skipAuthRefresh: true });
    }
  }

  if (!res.ok) {
    let code = "unknown_error";
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
    } catch {
      // response body wasn't JSON (e.g. a 502 from infra) — fall back to defaults above
    }
    throw new ApiError(message, code, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData, isFormData: true }),
};
