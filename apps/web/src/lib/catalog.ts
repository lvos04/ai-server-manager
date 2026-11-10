/** Appcatalogus (B01-002): typen en weergavehulpen. */
import type { StatusView } from "./status";
import { healthView } from "./status";

export interface Gezondheid {
  status: "healthy" | "degraded" | "down" | "unknown" | string;
  reason_code: string | null;
  melding: string;
  observed_at: string | null;
  laatst_getest: string | null;
  oorzaak: string | null;
  binnenkant_vereist: boolean;
  componenten?: Component[];
}

export interface Component {
  soort: "truenas" | "buitenkant" | "binnenkant" | string;
  bron: string;
  status: string;
  reason_code: string | null;
  melding: string;
  observed_at: string | null;
  detail?: string;
  staat?: string | null;
  verouderd?: boolean;
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
  next_cursor: string | null;
  inventaris: { status: string | null; reason_code: string | null; observed_at: string | null; verouderd: boolean | null };
  observed_at: string;
}

export interface CatalogDetail extends CatalogApp {
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

/** Gezondheid van een app: een verouderde bron is Onbekend + Verouderd, nooit gezond. */
export function appHealth(g: Pick<Gezondheid, "status" | "reason_code">): StatusView {
  if (g.reason_code === "inventaris_verouderd" || g.reason_code === "verouderd" || g.reason_code === "meting_verouderd") {
    return { tone: "stale", label: "Verouderd" };
  }
  return healthView(g.status);
}

export const COMPONENT_LABEL: Record<string, string> = {
  truenas: "TrueNAS-staat",
  buitenkant: "Buitenkant (Uptime Kuma)",
  binnenkant: "Binnenkant",
};

/** Uitleg bij een ontbrekende of onbekende component (reason_code → NL). */
export const REDEN: Record<string, string> = {
  binnenkant_niet_gebouwd: "Binnenkant volgt in fase P3 (koppeling met de app via zijn bestaande routes).",
  binnenkant_ontbreekt: "Geen controle van binnenuit.",
  geen_monitor: "Geen Uptime Kuma-monitor gekoppeld.",
  inventaris_verouderd: "De inventaris is verouderd.",
  app_gestopt: "De app is gestopt in TrueNAS.",
};
