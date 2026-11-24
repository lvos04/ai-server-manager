/** Appcatalogus (B01-002): typen en weergavehulpen. */
import type { Blokkade } from "./acties";
import type { StatusView } from "./status";
import { healthView } from "./status";
import { brontijd, formatTime } from "./format";

interface Meting {
  status: string;
  reason_code: string | null;
  melding: string;
  observed_at: string | null;
  geldig_tot?: string | null;
  laatste_status?: string | null;
  verouderd?: boolean;
}

export interface Gezondheid extends Meting {
  laatst_getest: string | null;
  oorzaak: string | null;
  binnenkant_vereist: boolean;
  componenten?: Component[];
}

export interface Component extends Meting {
  soort: "truenas" | "buitenkant" | "binnenkant" | string;
  bron: string;
  detail?: string;
  staat?: string | null;
  latency_ms?: number;
  uptime_24u?: number;
}

export interface CatalogApp {
  id: string;
  runtime_id: string;
  naam: string;
  titel: string;
  app_id: string | null;
  adaptertype: string;
  soort: string;
  installatiewijze: string;
  image: { repository: string | null; tag: string | null; digest: string | null };
  versie: string | null;
  runtime_staat: string | null;
  gezondheid: Gezondheid;
  deep_link: string | null;
  eigenaar: { repo: string | null; soort: string };
  aanwezig: boolean;
  eerst_gezien: string | null;
  laatst_gezien: string | null;
  verdwenen_sinds: string | null;
  laatst_getest: string | null;
}

export interface CatalogList {
  items: CatalogApp[];
  totaal: number;
  per_status: Record<"healthy" | "degraded" | "down" | "unknown", number>;
  overige_geldig_tot?: string | null;
  next_cursor: string | null;
  inventaris: { status: string | null; reason_code: string | null; observed_at: string | null; verouderd: boolean | null };
  observed_at: string;
}

export interface CatalogDetail extends CatalogApp {
  actiebeleid?: {
    policy_hash: string;
    geldig_tot: string;
    acties: Record<string, { risk_class: string; goedkeuring_nodig: boolean; blokkades: Blokkade[] }>;
  } | null;
  gezondheid: Gezondheid & { componenten: Component[] };
  deep_link_detail: { url: string | null; reden: string | null; bron: string | null };
  catalogus: Record<string, unknown> | null;
  image_historie: { op: string; tag: string | null; digest: string | null; repository: string | null }[];
  poorten: { host_ip: string; protocol: string; host_poort: number; container_poort: number }[];
  opslag: { bron: string; doel: string; type: string; soort: string; dataset: string | null }[];
  datasets: string[];
  resourcegrenzen: { status: string; reden: string; toelichting: string };
  documentatie: string | null;
  gezondheidsprofiel: { binnenkant: string | null; binnenkant_vereist: boolean };
  dienst: { id: string; app_id: string; status: string; versie: string } | null;
  bron: { nas: string; methode: string; observed_at: string } | null;
  acties: { id: string; beschikbaar: boolean; url?: string | null; reden: string | null; vereiste_rol?: string; risico?: string }[];
}

export const INSTALLATIE: Record<string, string> = {
  custom_app: "Custom App (standaardformulier)",
  custom_compose: "Compose (YAML) — buiten het platformbeleid",
  catalog_app: "Catalogusapp",
  onbekend: "Onbekend",
};

export const EIGENAAR: Record<string, string> = {
  hub: "Hub (deze app)",
  eigen: "Eigen dienst",
  bestaand: "Bestaande app",
  derde: "Derde partij",
};

const RANG: Record<string, number> = { down: 0, degraded: 1, unknown: 2, healthy: 3 };

/** Slechtste status eerst (Storing > Beperkt > Onbekend > Gezond), dan naam (OB-08). */
export function sortApps(items: CatalogApp[], opNaam = false): CatalogApp[] {
  return [...items].sort(
    (a, b) => (opNaam ? 0 : (RANG[a.gezondheid.status] ?? 2) - (RANG[b.gezondheid.status] ?? 2)) || a.titel.localeCompare(b.titel, "nl"),
  );
}

/** De API levert de kortste geldigheidsduur van de bronnen voor deze status. */
export function vervalgrens(m: Meting): number {
  return m.status === "unknown" ? NaN : brontijd(m.geldig_tot);
}

export function actueleMeting<T extends Meting>(m: T, ophaalfout: boolean, nu: number): T {
  if (m.status === "unknown") return m;
  const op = brontijd(m.observed_at);
  if (!Number.isFinite(op) || op > nu) {
    return { ...m, status: "unknown", observed_at: null, reason_code: "meettijd_onbekend", melding: "De meettijd ontbreekt of is ongeldig." };
  }
  if (!ophaalfout && !m.verouderd && nu <= vervalgrens(m)) return m;
  return {
    ...m,
    status: "unknown",
    laatste_status: m.status,
    verouderd: true,
    reason_code: ophaalfout ? "ophalen_mislukt" : "meting_verouderd",
    melding: ophaalfout ? "De meting kon niet worden vernieuwd." : "De meting is verlopen.",
  };
}

export function appHealth(g: Meting): StatusView {
  const historisch = g.verouderd || g.laatste_status || g.reason_code === "meting_verouderd" || g.reason_code === "inventaris_verouderd";
  if (g.status === "unknown" && g.observed_at && historisch) {
    return { tone: "stale", label: `Laatst bekend · ${formatTime(g.observed_at)}` };
  }
  return healthView(g.status);
}

export function meetToelichting(m: Meting): string {
  if (m.status === "unknown" && (m.laatste_status === "down" || m.laatste_status === "degraded")) {
    return `${m.melding} Laatst bekend: ${healthView(m.laatste_status).label}.`.trim();
  }
  return m.melding;
}

export function catalogusTellingen(d: CatalogList, getoond: CatalogApp[], ophaalfout: boolean, nu: number): CatalogList["per_status"] {
  const counts = { healthy: 0, degraded: 0, down: 0, unknown: 0 };
  if (d.totaal > d.items.length) {
    if (!ophaalfout && nu <= brontijd(d.overige_geldig_tot)) {
      Object.assign(counts, d.per_status);
      for (const a of d.items) counts[a.gezondheid.status as keyof typeof counts]--;
    } else {
      counts.unknown = d.totaal - d.items.length;
    }
  }
  for (const a of getoond) counts[a.gezondheid.status as keyof typeof counts]++;
  return counts;
}

export const COMPONENT_LABEL: Record<string, string> = {
  truenas: "TrueNAS-staat",
  buitenkant: "Buitenkant (Uptime Kuma)",
  binnenkant: "Binnenkant",
};

/** Uitleg bij een ontbrekende of onbekende component (reason_code → NL). */
export const REDEN: Record<string, string> = {
  binnenkant_ontbreekt: "Geen controle van binnenuit.",
  geen_monitor: "Geen Uptime Kuma-monitor gekoppeld.",
  inventaris_verouderd: "De inventaris is verouderd.",
  app_gestopt: "De app is gestopt in TrueNAS.",
};
