import { uuidv4 } from "./uuid";

/** Fout van de Hub-API in het contractformaat `{code, message (NL), details, trace_id}` (contract §5). */
export class HubApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly traceId: string | undefined;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}, traceId?: string) {
    super(message);
    this.name = "HubApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.traceId = traceId;
  }
}

export type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiOptions {
  method?: Method;
  body?: unknown;
  /** Hergebruik dezelfde key bij een herhaalde poging van dezelfde handeling (geen dubbele uitvoering). */
  idempotencyKey?: string;
  ifMatch?: string | null;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  cookieString?: string;
}

export interface ApiResult<T> {
  data: T;
  status: number;
  etag: string | null;
}

export const CSRF_COOKIE = "hub_csrf";
export const UNAUTHORIZED_EVENT = "hub:niet-aangemeld";
const AUTH_PATHS = ["/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/setup/"];

export function readCookie(name: string, cookieString?: string): string | null {
  const source = cookieString ?? (typeof document !== "undefined" ? document.cookie : "");
  for (const part of source.split(";")) {
    const [k, ...rest] = part.trim().split("=");
    if (k === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

function isErrorBody(v: unknown): v is { code: string; message: string; details?: Record<string, unknown>; trace_id?: string } {
  return typeof v === "object" && v !== null && typeof (v as { code?: unknown }).code === "string" &&
    typeof (v as { message?: unknown }).message === "string";
}

export async function apiRequest<T>(path: string, opts: ApiOptions = {}): Promise<ApiResult<T>> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrf = readCookie(CSRF_COOKIE, opts.cookieString);
    if (csrf) headers["X-CSRF-Token"] = csrf;
    headers["Idempotency-Key"] = opts.idempotencyKey ?? uuidv4();
  }
  if (opts.ifMatch) headers["If-Match"] = opts.ifMatch;
  const doFetch = opts.fetchImpl ?? fetch;
  let res: Response;
  try {
    res = await doFetch(path, {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
      cache: "no-store",
      signal: opts.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new HubApiError(0, "network_error", "De Hub is niet bereikbaar. Controleer je verbinding en probeer het opnieuw.");
  }
  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = undefined;
    }
  }
  if (!res.ok) {
    // Alleen een verlopen/ontbrekende sessie (code "unauthorized") meldt de gebruiker af; een 401 met een inhoudelijke
    // code (bv. invalid_totp bij het bevestigen van het noodaccount) is een veldfout, geen afmelding.
    const sessionGone = isErrorBody(parsed) ? parsed.code === "unauthorized" : true;
    if (res.status === 401 && sessionGone && typeof window !== "undefined" && !AUTH_PATHS.some((p) => path.startsWith(p))) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    if (isErrorBody(parsed)) {
      throw new HubApiError(res.status, parsed.code, parsed.message, parsed.details ?? {}, parsed.trace_id);
    }
    throw new HubApiError(res.status, "unexpected_response", `Onverwacht antwoord van de Hub (HTTP ${res.status}).`);
  }
  if (parsed === undefined) {
    throw new HubApiError(res.status, "unexpected_response", "Onverwacht antwoord van de Hub (geen JSON).");
  }
  return { data: parsed as T, status: res.status, etag: res.headers.get("ETag") };
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return (await apiRequest<T>(path, { signal })).data;
}

export function errorMessage(err: unknown): string {
  if (err instanceof HubApiError) return err.message;
  if (err instanceof Error) return `Onverwachte fout: ${err.message}`;
  return "Onverwachte fout.";
}
