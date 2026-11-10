/** Incidenten-inbox (B01-005): typen van de API en weergavehulpen. */
import { ernstVan, ERNST_RANG, type StatusView } from "./status";

export interface Hypothese {
  regel: string;
  tekst: string;
  bewijs: Record<string, unknown>[];
  sleutel: string | null;
  zekerheid: number | null;
  berekend_op: string | null;
}

export interface Readback {
  toestand: "actief" | "hersteld" | "onbekend" | string;
  autoritatief: boolean;
  bron: string;
  gemeten_op: string | null;
  detail: string;
}

export interface IncidentEvent {
  id: number;
  soort: string;
  op: string;
  ontvangen_op: string;
  event_type: string | null;
  bron: string;
  bron_ref: string | null;
  samenvatting: string;
  details: Record<string, unknown>;
  details_verborgen: boolean;
  trace_id: string | null;
  actor: string;
}

export interface Incident {
  id: string;
  titel: string;
  soort: string;
  ernst: string;
  /** Contract 1.3 §7: het Peil-woord uit payload.ernst, als de bron dat meegaf. */
  ernst_bron?: string | null;
  status: "open" | "erkend" | "gesnoozed" | "opgelost";
  actief: boolean;
  bron: string;
  onderwerp: { type: string; id: string; naam: string | null };
  eerste_gebeurtenis: string;
  laatste_gebeurtenis: string;
  geopend_op: string;
  aantal_gebeurtenissen: number;
  heropend: number;
  erkend: { door: string; op: string; tot: string | null } | null;
  gesnoozed: { door: string; op: string; tot: string | null; reden: string | null } | null;
  opgelost: { door: string; op: string; reden: string | null } | null;
  hypothese: Hypothese | null;
  veilige_modus: { actief: boolean; sinds: string | null };
  runbook_id: string | null;
  trace_ids: string[];
  readback: Readback | null;
  acties: string[];
  versie: number;
  bijgewerkt_op: string;
  gebeurtenissen?: IncidentEvent[];
}

export interface IncidentList {
  items: Incident[];
  next_cursor: string | null;
  bijgewerkt_op: string;
}

export interface Stap {
  tekst: string;
  soort: "lezen" | "handmatig" | "voorstel" | string;
  bron: string | null;
  action_id: string | null;
  risico: string | null;
}

export interface Onderzoek {
  incident_id: string;
  runbook: { id: string; titel: string; scenario: string; fasen: Record<string, Stap[]>; test_na_herstel: string[] } | null;
  hypothese: Hypothese | null;
  readback: Readback | null;
  veilige_modus: { actief: boolean; sinds: string | null };
  heropend: number;
}

export interface HerstelVoorstel {
  incident_id: string;
  uitvoerbaar: boolean;
  veilige_modus: boolean;
  voorstel: {
    action_id: string;
    target: Record<string, unknown>;
    parameters: Record<string, unknown>;
    risk_claim: string;
    expires_in_seconds: number;
    reason: string;
  } | null;
  reden: string;
  advies: string;
}

/** IncidentStatus (T-20a): vaste termen; gesnoozed heet in Peil "uitgesteld". */
export function incidentStatusView(i: Pick<Incident, "status" | "erkend" | "gesnoozed" | "opgelost">, tijd: (iso: string | null | undefined) => string): StatusView {
  switch (i.status) {
    case "open":
      return { tone: "neutral", label: "Open", icon: "open" };
    case "erkend":
      return { tone: "neutral", label: i.erkend?.tot ? `Erkend tot ${tijd(i.erkend.tot)}` : "Erkend", icon: "geslaagd" };
    case "gesnoozed":
      return { tone: "info", label: i.gesnoozed?.tot ? `Uitgesteld tot ${tijd(i.gesnoozed.tot)}` : "Uitgesteld" };
    case "opgelost":
      return { tone: "neutral", label: "Opgelost", icon: "geslaagd" };
    default:
      return { tone: "unknown", label: "Onbekend" };
  }
}

/** Inbox-volgorde: actief eerst, dan ernst (kritiek eerst), dan laatste gebeurtenis (nieuwste eerst). */
export function sortIncidents(items: Incident[]): Incident[] {
  return [...items].sort(
    (a, b) =>
      Number(b.actief) - Number(a.actief) ||
      ERNST_RANG[ernstVan(a.ernst, a.ernst_bron)] - ERNST_RANG[ernstVan(b.ernst, b.ernst_bron)] ||
      Date.parse(b.laatste_gebeurtenis) - Date.parse(a.laatste_gebeurtenis),
  );
}

export const FASE_LABEL: Record<string, string> = {
  observeren: "Observeren",
  isoleren: "Isoleren",
  mitigeren: "Mitigeren",
  terugdraaien: "Terugdraaien",
  bewijs: "Bewijs vastleggen",
  oorzaak: "Oorzaak",
};

export const STAP_SOORT: Record<string, string> = { lezen: "Hub toont", handmatig: "Zelf doen", voorstel: "Voorstel" };
