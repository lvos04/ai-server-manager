"use client";

import { useCallback, useRef, useState } from "react";
import { apiRequest, HubApiError, type Method } from "./api";
import { uuidv4 } from "./uuid";

export interface ActionState<T> {
  busy: boolean;
  error: HubApiError | null;
  result: T | null;
  /** Voert de mutatie uit; bij een herhaalde poging van dezelfde handeling wordt dezelfde Idempotency-Key gebruikt. */
  run: (path: string, opts?: { method?: Method; body?: unknown; ifMatch?: string | null }) => Promise<T | null>;
  reset: () => void;
}

/**
 * Eén mutatie (POST/PUT/PATCH) met busy/fout/resultaat. De Idempotency-Key blijft gelijk tot een geslaagde poging, zodat
 * "Opnieuw proberen" na een netwerkfout nooit dubbel uitvoert (contract §5).
 */
export function useAction<T = unknown>(): ActionState<T> {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<HubApiError | null>(null);
  const [result, setResult] = useState<T | null>(null);
  const key = useRef<string>(uuidv4());
  const run = useCallback(async (path: string, opts: { method?: Method; body?: unknown; ifMatch?: string | null } = {}) => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiRequest<T>(path, { method: opts.method ?? "POST", body: opts.body, ifMatch: opts.ifMatch, idempotencyKey: key.current });
      key.current = uuidv4();
      setResult(res.data);
      return res.data;
    } catch (e) {
      const err = e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e));
      // Een inhoudelijke weigering (4xx) is een nieuwe handeling bij een volgende poging; netwerk/5xx: zelfde sleutel.
      if (err.status >= 400 && err.status < 500) key.current = uuidv4();
      setError(err);
      return null;
    } finally {
      setBusy(false);
    }
  }, []);
  const reset = useCallback(() => {
    setError(null);
    setResult(null);
  }, []);
  return { busy, error, result, run, reset };
}
