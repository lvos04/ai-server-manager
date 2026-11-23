"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest, HubApiError, type ApiOptions } from "./api";
import { useOnline } from "./pwa";
import { useApi } from "./use-api";

const bewaar = (e: HubApiError) => ![401, 403, 404].includes(e.status);

/** Ook na terugkeer online blijft de stand oud tot deze bron opnieuw is gelezen. */
export function useMeting<T>(pad: string | null, request = apiRequest<T>, interval = 30_000) {
  const s = useApi<T>(pad, interval, bewaar, request);
  const online = useOnline();
  const [sinds, setSinds] = useState(0);
  const { reload } = s;
  useEffect(() => {
    const herstel = () => { setSinds(Date.now()); void reload(); };
    window.addEventListener("online", herstel);
    return () => window.removeEventListener("online", herstel);
  }, [reload]);
  return { ...s, stale: !!s.stale || !online || (sinds > 0 && !(Date.parse(s.lastOk ?? "") >= sinds)) };
}

interface Pagina<T> { items: T[]; next_cursor: string | null }

/** Herlees ook geladen vervolgpagina's. Een geweigerd recht wist daarmee de hele selectie. */
export function usePaginaLijst<T>(pad: string | null, sleutel: (rij: T) => string) {
  const [aantal, setAantal] = useState(1);
  const lees = useCallback(async (url: string, opts: ApiOptions = {}) => {
    const eerste = await apiRequest<Pagina<T>>(url, opts);
    const rijen = new Map<string, T>();
    const gezien = new Set<string>();
    let pagina = eerste.data;
    for (let i = 1; ; i++) {
      for (const rij of pagina.items) if (!rijen.has(sleutel(rij))) rijen.set(sleutel(rij), rij);
      const cursor = pagina.next_cursor;
      if (!cursor || i >= aantal) break;
      if (gezien.has(cursor)) throw new HubApiError(0, "onbekend", "Ongeldige vervolgpagina.");
      gezien.add(cursor);
      pagina = (await apiRequest<Pagina<T>>(`${url}&cursor=${encodeURIComponent(cursor)}`, opts)).data;
    }
    return { ...eerste, data: { items: [...rijen.values()], next_cursor: pagina.next_cursor } };
  }, [aantal, sleutel]);
  return { ...useMeting<Pagina<T>>(pad, lees), meer: () => setAantal(n => n + 1) };
}
