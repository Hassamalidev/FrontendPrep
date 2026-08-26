/**
 * The HTTP layer.
 *
 * Three things this handles that every caller would otherwise repeat:
 *
 *  - **Transparent refresh.** A 401 triggers one refresh attempt and one retry.
 *    Concurrent 401s share a single in-flight refresh promise, so a dashboard
 *    firing four requests against an expired token refreshes once, not four
 *    times -- which matters because the backend revokes the session family when
 *    a rotated refresh token is replayed.
 *  - **Error normalisation.** FastAPI returns `{detail}` for business errors and
 *    `{detail, errors[]}` for validation failures. Both arrive here as one
 *    `ApiError` with a `fieldErrors` map a form can read directly.
 *  - **Session expiry.** When refresh itself fails the tokens are cleared and
 *    subscribers are notified, so the app can redirect to sign-in from one place.
 */

import { tokens } from "./tokens";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }

  /** True when the failure is the user's input rather than a server problem. */
  get isValidation(): boolean {
    return this.status === 422 || Object.keys(this.fieldErrors).length > 0;
  }
}

type Listener = () => void;
const expiryListeners = new Set<Listener>();

/** Notified when the session ends and cannot be recovered. */
export function onSessionExpired(listener: Listener): () => void {
  expiryListeners.add(listener);
  return () => expiryListeners.delete(listener);
}

function endSession(): void {
  tokens.clear();
  expiryListeners.forEach((listener) => listener());
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || "Request failed";
  const fieldErrors: Record<string, string> = {};

  try {
    const body = await response.json();
    if (typeof body?.detail === "string") detail = body.detail;

    // Our own handler flattens pydantic errors to {field, message}.
    if (Array.isArray(body?.errors)) {
      for (const entry of body.errors) {
        if (entry?.field) fieldErrors[entry.field] = entry.message ?? "Invalid value";
      }
    } else if (Array.isArray(body?.detail)) {
      // Raw FastAPI shape, in case a route bypasses the handler.
      for (const entry of body.detail) {
        const field = Array.isArray(entry?.loc) ? entry.loc.slice(1).join(".") : "";
        if (field) fieldErrors[field] = entry.msg ?? "Invalid value";
      }
      detail = "Please check the highlighted fields.";
    }
  } catch {
    /* a non-JSON body (a proxy error page, say) keeps the status text */
  }

  return new ApiError(response.status, detail, fieldErrors);
}

let refreshInFlight: Promise<boolean> | null = null;

/** Exchange the refresh token. Shared across concurrent callers. */
function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  const refreshToken = tokens.refresh();
  if (!refreshToken) return Promise.resolve(false);

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;

      const pair = await response.json();
      tokens.save({ access_token: pair.access_token, refresh_token: pair.refresh_token });
      return true;
    } catch {
      return false;
    } finally {
      // Cleared in a microtask so callers awaiting this promise all see the
      // same result before a new refresh can start.
      queueMicrotask(() => {
        refreshInFlight = null;
      });
    }
  })();

  return refreshInFlight;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
  /** Skip the Authorization header (used by login/register). */
  anonymous?: boolean;
};

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${BASE_URL}${path}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.append(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function send(path: string, options: RequestOptions, retrying = false): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const access = tokens.access();
  if (!options.anonymous && access) headers.Authorization = `Bearer ${access}`;

  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (response.status !== 401 || options.anonymous || retrying) return response;

  // One refresh, one retry. If the refresh fails the session is genuinely over.
  const recovered = await refreshSession();
  if (!recovered) {
    endSession();
    return response;
  }
  return send(path, options, true);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

/**
 * Multipart upload.
 *
 * Kept beside `request` rather than folded into it because the two differ in
 * exactly one way that matters: the browser must set its own `Content-Type` so
 * the multipart boundary is correct. Everything else -- the bearer token, the
 * single-flight refresh, the error shape -- is shared.
 */
export async function uploadForm<T>(path: string, body: FormData): Promise<T> {
  const send = async (retrying = false): Promise<Response> => {
    const headers: Record<string, string> = {};
    const access = tokens.access();
    if (access) headers.Authorization = `Bearer ${access}`;

    const response = await fetch(buildUrl(path), { method: "POST", headers, body });
    if (response.status !== 401 || retrying) return response;

    const recovered = await refreshSession();
    if (!recovered) {
      endSession();
      return response;
    }
    return send(true);
  };

  const response = await send();
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    request<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown, options: Omit<RequestOptions, "body" | "method"> = {}) =>
    request<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
