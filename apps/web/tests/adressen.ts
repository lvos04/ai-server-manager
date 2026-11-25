/** Synthetisch clientadres uit TEST-NET-1 (RFC 5737). */
export function documentatieAdres(host: number): string {
  return [192, 0, 2, host].join(".");
}
