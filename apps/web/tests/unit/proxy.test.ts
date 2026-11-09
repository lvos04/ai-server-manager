import { describe, expect, it } from "vitest";
// @ts-expect-error -- JavaScript-module van de webserver (zonder typedeclaraties)
import { MAX_BODY_BYTES, bodyCounter, declaredTooLarge, downstreamHeaders, isApiPath, normalizeIp, parseTrusted, payloadTooLargeBody, unavailableBody, upstreamHeaders } from "../../server/proxy.mjs";

describe("API-doorgang van de webserver", () => {
  it("alleen API-paden gaan naar de API", () => {
    for (const p of ["/api/v1/auth/me", "/api", "/healthz", "/readyz", "/connector/v1/health", "/api/v1/x?y=1"]) expect(isApiPath(p), p).toBe(true);
    for (const p of ["/", "/server", "/apiary", "/healthz/x", "/_next/static/a.js", "/api/../server"]) expect(isApiPath(p), p).toBe(false);
  });

  it("vervalste X-Forwarded-* van de client worden genegeerd; het echte adres wordt gezet", () => {
    const h = upstreamHeaders(
      { host: "nas:30400", "x-forwarded-for": "203.0.113.9", "x-forwarded-proto": "https", forwarded: "for=1.2.3.4", cookie: "a=b", connection: "keep-alive" },
      { remoteAddress: "::ffff:192.0.2.10", encrypted: false, trusted: new Set() },
    );
    expect(h["x-forwarded-for"]).toBe("192.0.2.10");
    expect(h["x-forwarded-proto"]).toBe("http");
    expect(h["x-forwarded-host"]).toBe("nas:30400");
    expect(h.forwarded).toBeUndefined();
    expect(h.connection).toBeUndefined();
    expect(h.cookie).toBe("a=b");
  });

  it("een expliciet vertrouwde reverse proxy mag de keten en https doorgeven", () => {
    const h = upstreamHeaders(
      { "x-forwarded-for": "198.51.100.7", "x-forwarded-proto": "https" },
      { remoteAddress: "192.0.2.1", encrypted: false, trusted: parseTrusted(" 192.0.2.1 ,") },
    );
    expect(h["x-forwarded-for"]).toBe("198.51.100.7, 192.0.2.1");
    expect(h["x-forwarded-proto"]).toBe("https");
  });

  it("hulpfuncties", () => {
    expect(normalizeIp(undefined)).toBe("onbekend");
    expect(normalizeIp("::1")).toBe("::1");
    expect(downstreamHeaders({ "transfer-encoding": "chunked", "set-cookie": ["a=1", "b=2"], etag: "x" })).toEqual({ "set-cookie": ["a=1", "b=2"], etag: "x" });
    const body = unavailableBody("t-1");
    expect(body.code).toBe("api_unavailable");
    expect(body.message).toContain("Logs");
    expect(body.trace_id).toBe("t-1");
  });

  it("1 MiB-grens (contract 1.2 §5): Content-Length en chunked tellen; 413 in het contractformaat", () => {
    expect(MAX_BODY_BYTES).toBe(1048576);
    expect(declaredTooLarge({ "content-length": "1048577" })).toBe(true);
    expect(declaredTooLarge({ "content-length": "1048576" })).toBe(false);
    expect(declaredTooLarge({ "content-length": ["2000000"] })).toBe(true);
    expect(declaredTooLarge({})).toBe(false); // chunked: geen header, de teller beslist
    expect(declaredTooLarge({ "content-length": "abc" })).toBe(false); // ongeldig: de API geeft 400
    const over = bodyCounter();
    expect(over(1024 * 1024)).toBe(false); // precies 1 MiB mag
    expect(over(1)).toBe(true); // één byte meer niet
    const small = bodyCounter(10);
    expect([small(4), small(6), small(1)]).toEqual([false, false, true]);
    const body = payloadTooLargeBody("t-2");
    expect(body).toEqual({
      code: "payload_too_large",
      message: "Het verzoek is te groot (maximaal 1 MiB).",
      details: { max_bytes: 1048576 },
      trace_id: "t-2",
    });
  });
});
