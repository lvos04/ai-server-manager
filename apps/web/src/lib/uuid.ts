/**
 * UUID v4 voor Idempotency-Key's. `crypto.randomUUID` bestaat alleen in een "secure context" (HTTPS of localhost);
 * de Hub draait in P0 vaak via http://<NAS-adres>:30400, dus valt dit terug op `crypto.getRandomValues` (dat wél
 * overal beschikbaar is). Nooit Math.random.
 */
export function uuidv4(cryptoImpl: Crypto | undefined = globalThis.crypto): string {
  if (!cryptoImpl || typeof cryptoImpl.getRandomValues !== "function") {
    throw new Error("Geen veilige toevalsbron beschikbaar in deze browser.");
  }
  if (typeof cryptoImpl.randomUUID === "function") {
    try {
      return cryptoImpl.randomUUID();
    } catch {
      // val terug op getRandomValues
    }
  }
  const b = new Uint8Array(16);
  cryptoImpl.getRandomValues(b);
  b[6] = ((b[6] ?? 0) & 0x0f) | 0x40;
  b[8] = ((b[8] ?? 0) & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
