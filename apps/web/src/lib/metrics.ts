/** Tijdreeksen (B09-003) lezen voor grafieken: punten → reeksen met eerlijke gaten (nooit doorgetrokken, nooit 0). */
import type { Punt } from "@/components/LineChart";

export interface Series {
  id: number;
  onderwerp_type: string;
  onderwerp_id: string;
  metriek: string;
  eenheid: string;
  bron: string;
  labels: Record<string, string | null>;
  laatste_waarde: number | null;
  laatst_bekend: { waarde: number; observed_at: string } | null;
  observed_at: string | null;
  status: string;
  verouderd: boolean;
}

export interface QueryResult {
  reeks: Series;
  van: string;
  tot: string;
  resolutie: "ruw" | "5m" | "1u";
  punten: { ts: string; waarde?: number | null; gemiddelde?: number | null }[];
  afgekapt: boolean;
}

export type Periode = "1u" | "6u" | "24u" | "7d" | "30d";
export const PERIODES: { id: Periode; label: string; ms: number }[] = [
  { id: "1u", label: "1 u", ms: 3_600_000 },
  { id: "6u", label: "6 u", ms: 6 * 3_600_000 },
  { id: "24u", label: "24 u", ms: 24 * 3_600_000 },
  { id: "7d", label: "7 d", ms: 7 * 86_400_000 },
  { id: "30d", label: "30 d", ms: 30 * 86_400_000 },
];

export const RESOLUTIE_LABEL: Record<string, string> = { ruw: "ruwe metingen", "5m": "gemiddelde per 5 minuten", "1u": "gemiddelde per uur" };

/**
 * Pad voor /metrics/query. `van` staat op de hele minuut en `tot` ontbreekt (de Hub neemt dan "nu"): het pad blijft
 * zo binnen een minuut gelijk. Review: met `van`/`tot` op de milliseconde veranderde het pad bij elke weergave, haalde
 * useApi eindeloos opnieuw op (± 1300 aanvragen in 6 s) en zei elke grafiek ten onrechte "Geen meting in deze periode".
 */
export function queryPath(seriesId: number, periode: Periode, now = Date.now()): string {
  const ms = PERIODES.find((p) => p.id === periode)?.ms ?? 6 * 3_600_000;
  const van = new Date(Math.floor((now - ms) / 60_000) * 60_000).toISOString();
  return `/api/v1/metrics/query?series=${seriesId}&van=${encodeURIComponent(van)}`;
}

const STAP: Record<string, number> = { "5m": 300_000, "1u": 3_600_000 };

/**
 * Punten → grafiekrijen. Een gat (geen meting langer dan 2,5× de normale afstand) wordt een expliciete null, zodat de
 * lijn onderbreekt en de tabel "Geen meting" toont.
 */
export function toRows(q: QueryResult | undefined, key: string): Punt[] {
  if (!q) return [];
  const pts = q.punten
    .map((p) => ({ t: Date.parse(p.ts), v: p.waarde ?? p.gemiddelde ?? null }))
    .filter((p) => !Number.isNaN(p.t))
    .sort((a, b) => a.t - b.t);
  if (pts.length < 2) return pts.map((p) => ({ t: p.t, [key]: p.v }));
  const diffs = pts.slice(1).map((p, i) => p.t - pts[i]!.t).sort((a, b) => a - b);
  const typical = STAP[q.resolutie] ?? diffs[Math.floor(diffs.length / 2)] ?? 60_000;
  const out: Punt[] = [];
  pts.forEach((p, i) => {
    if (i > 0 && p.t - pts[i - 1]!.t > typical * 2.5) out.push({ t: pts[i - 1]!.t + typical, [key]: null });
    out.push({ t: p.t, [key]: p.v });
  });
  return out;
}

/** Twee reeksen samenvoegen op tijd (bijv. netwerk ontvangen/verzonden). */
export function mergeRows(a: Punt[], b: Punt[]): Punt[] {
  const map = new Map<number, Punt>();
  for (const r of [...a, ...b]) map.set(r.t, { ...(map.get(r.t) ?? { t: r.t }), ...r });
  return [...map.values()].sort((x, y) => x.t - y.t);
}

/** Bron-id van een reeks → leesbaar ("truenas.reporting.realtime" → "TrueNAS (reporting.realtime)"). */
export function bronLabel(bron: string | null | undefined): string | null {
  if (!bron) return null;
  const [soort, ...rest] = bron.split(".");
  const naam: Record<string, string> = { truenas: "TrueNAS", beszel: "Beszel", uptime_kuma: "Uptime Kuma", kuma: "Uptime Kuma", hub: "Hub" };
  const n = naam[soort ?? ""];
  return n ? (rest.length ? `${n} (${rest.join(".")})` : n) : bron;
}
