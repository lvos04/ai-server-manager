import { describe, expect, it, vi } from "vitest";
import { apiRequest, HubApiError, readCookie } from "@/lib/api";
import { uuidv4 } from "@/lib/uuid";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function fakeFetch(status: number, body: string, headers: Record<string, string> = {}) {
  return vi.fn(async (...args: [string, RequestInit?]) => {
    void args;
    return new Response(body, { status, headers });
  });
}

describe("uuidv4 (Idempotency-Key)", () => {
  it("geeft een geldige v4-UUID", () => {
    expect(uuidv4()).toMatch(UUID_RE);
  });

  it("werkt ook zonder crypto.randomUUID (http://<NAS-adres> is geen secure context)", () => {
    const fake = { getRandomValues: (a: Uint8Array) => globalThis.crypto.getRandomValues(a) } as unknown as Crypto;
    const ids = new Set(Array.from({ length: 50 }, () => uuidv4(fake)));
    expect(ids.size).toBe(50);
    for (const id of ids) expect(id).toMatch(UUID_RE);
  });

  it("weigert zonder veilige toevalsbron", () => {
    expect(() => uuidv4({} as Crypto)).toThrow(/toevalsbron/);
  });
});

describe("apiRequest", () => {
  it("leest cookies", () => {
    expect(readCookie("hub_csrf", "a=1; hub_csrf=abc%3D; b=2")).toBe("abc=");
    expect(readCookie("x", "a=1")).toBeNull();
  });

  it("GET zonder CSRF/Idempotency-Key, met ETag terug", async () => {
    const f = fakeFetch(200, '{"ok":true}', { ETag: 'W/"D03-2"' });
    const res = await apiRequest<{ ok: boolean }>("/api/v1/x", { fetchImpl: f as unknown as typeof fetch, cookieString: "hub_csrf=t" });
    expect(res).toEqual({ data: { ok: true }, status: 200, etag: 'W/"D03-2"' });
    const init = f.mock.calls[0]![1]!;
    expect(init.headers).toEqual({ Accept: "application/json" });
    expect(init.credentials).toBe("same-origin");
  });

  it("mutaties sturen CSRF-token, Idempotency-Key (hergebruikt bij herhaling) en If-Match", async () => {
    const f = fakeFetch(200, "{}");
    await apiRequest("/api/v1/y", { method: "PUT", body: { a: 1 }, idempotencyKey: "k-1", ifMatch: 'W/"1"', fetchImpl: f as unknown as typeof fetch, cookieString: "hub_csrf=tok" });
    const h = f.mock.calls[0]![1]!.headers as Record<string, string>;
    expect(h["X-CSRF-Token"]).toBe("tok");
    expect(h["Idempotency-Key"]).toBe("k-1");
    expect(h["If-Match"]).toBe('W/"1"');
    expect(h["Content-Type"]).toBe("application/json");
    await apiRequest("/api/v1/y", { method: "POST", fetchImpl: f as unknown as typeof fetch, cookieString: "" });
    expect((f.mock.calls[1]![1]!.headers as Record<string, string>)["Idempotency-Key"]).toMatch(UUID_RE);
  });

  it("contractfout → HubApiError met code, NL-bericht, details en trace-id", async () => {
    const f = fakeFetch(422, JSON.stringify({ code: "validation_error", message: "De waarde voldoet niet.", details: { fouten: [] }, trace_id: "t-1" }));
    await expect(apiRequest("/api/v1/z", { fetchImpl: f as unknown as typeof fetch })).rejects.toMatchObject({
      status: 422,
      code: "validation_error",
      message: "De waarde voldoet niet.",
      details: { fouten: [] },
      traceId: "t-1",
    });
  });

  it("netwerkfout en niet-JSON-antwoord geven een Nederlandse foutcode", async () => {
    const down = vi.fn(async () => {
      throw new TypeError("fetch failed");
    });
    await expect(apiRequest("/api/v1/z", { fetchImpl: down as unknown as typeof fetch })).rejects.toMatchObject({ code: "network_error", status: 0 });
    const html = fakeFetch(502, "<html>Bad gateway</html>");
    const err = await apiRequest("/api/v1/z", { fetchImpl: html as unknown as typeof fetch }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(HubApiError);
    expect((err as HubApiError).code).toBe("unexpected_response");
    expect((err as HubApiError).message).toContain("HTTP 502");
  });

  it("204 zonder inhoud is geen fout", async () => {
    const f = vi.fn(async () => new Response(null, { status: 204 }));
    const res = await apiRequest("/api/v1/auth/logout", { method: "POST", fetchImpl: f as unknown as typeof fetch });
    expect(res.status).toBe(204);
    expect(res.data).toBeNull();
  });
});
