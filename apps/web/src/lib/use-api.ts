"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiRequest, HubApiError } from "./api";

export interface ApiState<T> {
  data: T | undefined;
  error: HubApiError | undefined;
  loading: boolean;
  etag: string | null;
  reload: () => Promise<void>;
}

/**
 * Gegevens van de API laden. Bij een fout worden oude gegevens NIET als actueel getoond: `data` wordt leeg en de fout
 * zichtbaar (onbekend is nooit groen). Optioneel periodiek vernieuwen zodat "laatst bijgewerkt" echt blijft.
 */
export function useApi<T>(path: string | null, refreshMs?: number): ApiState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<HubApiError | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const [etag, setEtag] = useState<string | null>(null);
  const ctrl = useRef<AbortController | null>(null);

  // State alleen in promise-callbacks zetten (geen synchrone setState in een effect).
  const fetchData = useCallback((): Promise<void> => {
    if (path === null) return Promise.resolve();
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    return apiRequest<T>(path, { signal: c.signal })
      .then((res) => {
        if (c.signal.aborted) return;
        setData(res.data);
        setEtag(res.etag);
        setError(undefined);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if ((e instanceof DOMException && e.name === "AbortError") || c.signal.aborted) return;
        setData(undefined);
        setError(e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e)));
        setLoading(false);
      });
  }, [path]);

  const reload = useCallback(async () => {
    setLoading(true);
    await fetchData();
  }, [fetchData]);

  useEffect(() => {
    void fetchData();
    if (!refreshMs) return () => ctrl.current?.abort();
    const t = setInterval(() => void fetchData(), refreshMs);
    return () => {
      clearInterval(t);
      ctrl.current?.abort();
    };
  }, [fetchData, refreshMs]);

  return { data, error, loading, etag, reload };
}

/** Wacht op een job (inventaris vernieuwen) tot hij klaar of mislukt is. */
export async function waitForJob(id: string, timeoutMs = 90_000): Promise<{ status: string; resultaat: Record<string, unknown> }> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { data } = await apiRequest<{ status: string; resultaat: Record<string, unknown> }>(`/api/v1/jobs/${id}`);
    if (data.status === "done" || data.status === "failed") return data;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new HubApiError(0, "timeout", "De taak duurt langer dan verwacht; vernieuw de pagina later.");
}
