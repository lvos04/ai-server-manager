"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest, HubApiError, type ApiOptions } from "./api";
import { useOnline } from "./pwa";
import { brontijd } from "./format";
import { LIJST_MAX_LEEFTIJD_MS, lijstIsVers } from "./lijstversheid";
import { useCatalogClock } from "./use-catalog-clock";
import { useApi, type ApiState } from "./use-api";

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

type Tijdveld = "observed_at" | "bijgewerkt_op" | "afgeleid_op";
type Bronmoment = Partial<Record<Tijdveld, string | null>>;

/** Een gezamenlijke bevestiging is zo oud als de oudste vereiste lezing. Elke brontijd moet bekend zijn. */
export function useBronstand<T>(bron: ApiState<T>, ...tijden: (string | null | undefined)[]) {
  const momenten = tijden.map(brontijd);
  const nu = useCatalogClock(momenten.flatMap(t => [t - 1, t + LIJST_MAX_LEEFTIJD_MS]));
  const oudste = Math.min(...momenten);
  const bekend = Number.isFinite(oudste) && momenten.every(t => t <= nu);
  const bronTijd = bekend ? new Date(oudste).toISOString() : null;
  return { ...bron, bronTijd, stale: bron.stale || (bron.data !== undefined && !lijstIsVers(bronTijd, nu)) };
}

export function useBronlijst<T>(pad: string | null, veld: Tijdveld = "observed_at", interval = 30_000) {
  const bron = useMeting<T & Bronmoment>(pad, undefined, interval);
  return useBronstand(bron, bron.data?.[veld]);
}

interface Pagina<T> extends Bronmoment { items: T[]; next_cursor: string | null }

/** Herlees ook geladen vervolgpagina's. Een geweigerd recht wist daarmee de hele selectie. */
export function usePaginaLijst<T>(pad: string | null, sleutel: (rij: T) => string, veld: Tijdveld = "bijgewerkt_op") {
  const [selectie, kies] = useState({ pad, aantal: 1 });
  const aantal = selectie.pad === pad ? selectie.aantal : 1;
  const lees = useCallback(async (url: string, opts: ApiOptions = {}) => {
    const eerste = await apiRequest<Pagina<T>>(url, opts);
    const rijen = new Map<string, T>();
    const gezien = new Set<string>();
    let pagina = eerste.data;
    let oudste = Infinity;
    for (let i = 1; ; i++) {
      const tijd = brontijd(pagina[veld]);
      oudste = Math.min(oudste, tijd <= Date.now() ? tijd : NaN);
      for (const rij of pagina.items) if (!rijen.has(sleutel(rij))) rijen.set(sleutel(rij), rij);
      const cursor = pagina.next_cursor;
      if (!cursor || i >= aantal) break;
      if (gezien.has(cursor)) throw new HubApiError(0, "onbekend", "Ongeldige vervolgpagina.");
      gezien.add(cursor);
      pagina = (await apiRequest<Pagina<T>>(`${url}&cursor=${encodeURIComponent(cursor)}`, opts)).data;
    }
    const observed_at = Number.isFinite(oudste) ? new Date(oudste).toISOString() : null;
    return { ...eerste, data: { items: [...rijen.values()], next_cursor: pagina.next_cursor, observed_at } };
  }, [aantal, sleutel, veld]);
  const bron = useMeting(pad, lees);
  return { ...useBronstand(bron, bron.data?.observed_at), meer: () => kies({ pad, aantal: aantal + 1 }) };
}
