// Doorzetten van API-verkeer van de web-UI naar de interne Hub-API (pure functies, getest met vitest).
//
// Alleen deze paden gaan naar de API; al het andere is de web-UI. De API luistert in de alles-in-één image alleen op
// 127.0.0.1, dus dit is de enige weg naar binnen. Doorstuurheaders (X-Forwarded-*) van de client worden NOOIT
// vertrouwd: de echte client-IP (voor rate-limits en het sessie-overzicht) wordt hier zelf gezet, tenzij het verzoek
// van een expliciet vertrouwde reverse proxy komt (HUB_WEB_TRUSTED_PROXIES, standaard leeg).

export const API_PREFIXES = ["/api/", "/connector/"];
export const API_EXACT = new Set(["/api", "/healthz", "/readyz"]);

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "proxy-connection",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);
const FORWARDING = new Set(["forwarded", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host", "x-forwarded-port", "x-real-ip"]);

/** @param {string} url pad + query van het inkomende verzoek */
export function isApiPath(url) {
  const pathname = (url || "/").split("?")[0] || "/";
  if (pathname.includes("..")) return false;
  return API_EXACT.has(pathname) || API_PREFIXES.some((p) => pathname.startsWith(p));
}

/** '::ffff:192.0.2.1' → '192.0.2.1'; leeg → 'onbekend' */
export function normalizeIp(addr) {
  if (!addr) return "onbekend";
  return addr.startsWith("::ffff:") ? addr.slice(7) : addr;
}

/** @param {string | undefined} raw komma-gescheiden lijst van IP-adressen */
export function parseTrusted(raw) {
  return new Set(
    String(raw || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(normalizeIp),
  );
}

/**
 * Headers voor het verzoek naar de API.
 * @param {Record<string, string | string[] | undefined>} incoming
 * @param {{ remoteAddress?: string, encrypted?: boolean, trusted?: Set<string> }} conn
 */
export function upstreamHeaders(incoming, conn) {
  /** @type {Record<string, string | string[]>} */
  const out = {};
  const remote = normalizeIp(conn.remoteAddress);
  const fromTrustedProxy = conn.trusted?.has(remote) ?? false;
  for (const [k, v] of Object.entries(incoming)) {
    if (v === undefined) continue;
    const key = k.toLowerCase();
    if (HOP_BY_HOP.has(key) || FORWARDING.has(key)) continue;
    out[key] = v;
  }
  const first = (v) => (Array.isArray(v) ? v[0] : v) || "";
  if (fromTrustedProxy && first(incoming["x-forwarded-for"])) {
    out["x-forwarded-for"] = `${first(incoming["x-forwarded-for"])}, ${remote}`;
    const proto = first(incoming["x-forwarded-proto"]).toLowerCase();
    out["x-forwarded-proto"] = proto === "https" ? "https" : conn.encrypted ? "https" : "http";
  } else {
    out["x-forwarded-for"] = remote;
    out["x-forwarded-proto"] = conn.encrypted ? "https" : "http";
  }
  if (incoming.host) out["x-forwarded-host"] = first(incoming.host);
  return out;
}

/** Headers van het API-antwoord terug naar de browser (zonder hop-by-hop-headers). */
export function downstreamHeaders(headers) {
  /** @type {Record<string, string | string[]>} */
  const out = {};
  for (const [k, v] of Object.entries(headers)) {
    if (v === undefined || HOP_BY_HOP.has(k.toLowerCase())) continue;
    out[k] = v;
  }
  return out;
}

/** Nederlandse foutbody (contractformaat §5) als de API niet bereikbaar is. */
export function unavailableBody(traceId) {
  return {
    code: "api_unavailable",
    message: "De Hub-API is (nog) niet bereikbaar. Wacht even: de app start mogelijk nog op. Blijft dit zo, kijk dan in TrueNAS bij Apps → ai-server-manager → Logs.",
    details: {},
    trace_id: traceId,
  };
}
