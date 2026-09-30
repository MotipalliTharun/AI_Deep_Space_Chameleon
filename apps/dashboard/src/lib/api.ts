/**
 * Fetch wrapper for the dashboard API.
 *
 * - Sends cookies (httpOnly access/refresh tokens set by the API).
 * - Echoes the `sc_csrf` cookie in `X-CSRF-Token` on state-changing requests.
 * - On a 401, refreshes the session once (single in-flight refresh shared by
 *   concurrent callers) and retries the original request.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const NO_REFRESH_PATHS = ["/v1/auth/login", "/v1/auth/signup", "/v1/auth/refresh", "/v1/auth/logout"];

let refreshInFlight: Promise<boolean> | null = null;
let onSessionExpired: (() => void) | null = null;

/** Called when a refresh fails, so the app can drop to the sign-in screen. */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

export function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) return decodeURIComponent(trimmed.slice(prefix.length));
  }
  return null;
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "http_error";
  let message = `Request failed (${res.status}).`;
  try {
    const body: unknown = await res.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      code = "validation_error";
      message = detail
        .map((d: { msg?: string; loc?: unknown[] }) => {
          const field = d.loc?.[d.loc.length - 1];
          return field ? `${String(field)}: ${d.msg ?? "invalid"}` : (d.msg ?? "invalid");
        })
        .join(" ");
    } else if (detail && typeof detail === "object") {
      const d = detail as { code?: string; message?: string };
      code = d.code ?? code;
      message = d.message ?? message;
    }
  } catch {
    // Non-JSON body: keep the generic message.
  }
  return new ApiError(res.status, code, message);
}

function send(path: string, init: RequestInit): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie("sc_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  return fetch(path, { ...init, method, headers, credentials: "include" });
}

async function doRefresh(): Promise<boolean> {
  // The CSRF cookie lives as long as the refresh cookie; without it there is
  // no session to refresh, so skip a request that can only fail.
  if (!readCookie("sc_csrf")) return false;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const res = await send("/v1/auth/refresh", { method: "POST" });
    if (res.ok) return true;
    // 409: another tab refreshed at the same moment; its new cookies are ours too.
    if (res.status !== 409) return false;
    await new Promise((r) => setTimeout(r, 150 * (attempt + 1)));
  }
  return false;
}

export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= doRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await send(path, init);
  if (res.status === 401 && !NO_REFRESH_PATHS.includes(path)) {
    if (await refreshSession()) {
      res = await send(path, init);
    } else {
      onSessionExpired?.();
    }
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body: unknown) =>
    apiRequest<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
};
