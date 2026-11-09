/**
 * Where the PLATO API lives, resolved in the browser so one build works on every device:
 * - NEXT_PUBLIC_API_URL=https://api.example.com → that URL.
 * - NEXT_PUBLIC_API_URL=same-origin            → the page's own origin (API behind the same reverse proxy).
 * - unset                                     → same host as the page, port 8000. A phone opening
 *   http://192.168.1.20:3000 therefore talks to http://192.168.1.20:8000 instead of its own "localhost".
 */
export function apiUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_API_URL || "").trim().replace(/\/$/, "");
  if (typeof window === "undefined") return configured && configured !== "same-origin" ? configured : "http://localhost:8000";
  if (configured === "same-origin") return window.location.origin;
  if (configured) return configured;
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

export function wsUrl(): string {
  return apiUrl().replace(/^http/, "ws");
}

const TOKEN_KEY = "plato.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — session-only auth */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  const isPublic = path.startsWith("/api/auth/login") || path.startsWith("/api/auth/register") || path === "/api/billing/plans";
  if (!token && !isPublic) {
    // Not signed in: don't send a request that can only fail; go to the login page instead.
    if (typeof window !== "undefined" && window.location.pathname !== "/login") window.location.href = "/login";
    throw new ApiError(401, "Not signed in");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`${apiUrl()}${path}`, { ...init, headers, body });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/")) {
    setToken(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: { msg: string }) => d.msg).join("; ") : msg;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
