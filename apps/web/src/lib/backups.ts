import type { Coverage, Gate, GateReason } from "./types";
import { formatNumber, parseIso } from "./format";

export const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
export const APP_ID = /^[a-z0-9][a-z0-9_.-]{0,63}$/;
export const DATASET = /^[a-zA-Z0-9][a-zA-Z0-9_.-]*(?:\/[a-zA-Z0-9][a-zA-Z0-9_.-]*)*$/;
export const BRONNAMEN: Record<string, string> = {
  mediaguard: "MediaGuard-voortgang", emby_exportarchief: "Emby-exportarchief",
  "media-source-optimizer": "Media Source Optimizer", my_house: "my_house",
};

export function appNaam(id: unknown) {
  return typeof id === "string" && APP_ID.test(id) ? id : "Onbekend";
}

export function datasetNaam(id: unknown) {
  return typeof id === "string" && id.length <= 200 && DATASET.test(id) ? id : null;
}

const TIJDSTIP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;

export function meettijd(tijd: string | null | undefined, nu: number) {
  if (!tijd || !TIJDSTIP.test(tijd)) return null;
  const datum = parseIso(tijd);
  return datum && datum.getTime() <= nu ? datum.toISOString() : null;
}

export function verseApp(c: Coverage | undefined, id: string, nu: number) {
  const rij = c?.app_backups?.[id];
  return !!rij && id !== "media-source-optimizer" && !!meettijd(rij.observed_at, nu)
    && TIJDSTIP.test(rij.geldig_tot ?? "") && Date.parse(rij.geldig_tot ?? "") >= nu;
}

export function backupGate(gate: Gate | undefined, c: Coverage | undefined, oud: boolean, nu: number): Gate["status"] {
  if (!gate || oud) return "unknown";
  if (gate.status === "geblokkeerd" && !gate.toegestaan) return "geblokkeerd";
  if (!meettijd(gate.afgeleid_op, nu) || nu - Date.parse(gate.afgeleid_op) > 90_000) return "unknown";
  if (gate.status !== "toegestaan" || !gate.toegestaan || !Array.isArray(gate.redenen) || gate.redenen.length) return "unknown";
  const allesGedekt = Object.keys(BRONNAMEN).every((id) => {
    const rij = c?.app_backups?.[id];
    if (!rij) return false;
    if (id !== "mediaguard" && id !== "emby_exportarchief" && rij.vereist === false) return true;
    return rij.status === "gedekt" && verseApp(c, id, nu);
  });
  return allesGedekt ? "toegestaan" : "unknown";
}

const BESLUIT: Record<string, string> = {
  D04: "Leg de externe back-up vast in D04.", D05: "Test het snapshotbeleid in D05.", D16: "Leg de hersteldoelen vast in D16.",
};
export function gateVoorwaarde(r: GateReason): [string, string] {
  if (r.soort === "besluit" && Object.hasOwn(BESLUIT, r.id)) return [BESLUIT[r.id]!, `/onboarding/besluit/${r.id}`];
  if (r.soort === "meting") {
    if (r.id === "eigen_backup") return ["Een actuele geverifieerde export van de Hub-database ontbreekt.", "/backups#eigen-titel"];
    if (r.id === "extern_backup") return ["De externe back-up is niet aantoonbaar actueel.", "/backups/extern"];
    if (Object.hasOwn(BRONNAMEN, r.id)) return [`${BRONNAMEN[r.id]} heeft geen bevestigde back-updekking.`, "/backups#appmeldingen"];
  }
  return ["Deze voorwaarde is niet bevestigd.", "/backups"];
}

const MELDREDENEN = new Set([
  "Geen bevestigde meting van de adapter.", "De adapter is onbereikbaar of het leesrecht is niet bevestigd.",
  "De bronmeting is onvolledig of tegenstrijdig.", "De bronmeting is verlopen.",
  "De back-up is ouder dan de toegestane leeftijd.", "Een forkback-up ontbreekt of is niet geverifieerd.",
  "Een onderdeel van het herstelrapport is niet geverifieerd.", "De back-upcontrole van my_house meldt een afwijking.",
  "Geen toegestane onderhoudsroute met leesrecht.", "nog niet gemaakt (overname, P4-0)",
  "Geen afzonderlijke back-upkopie met overeenkomende controlesommen.", "De maximale archiefleeftijd is nog niet vastgelegd in D16.",
  "Het leesbewijs van de bevestigde overnamebron ontbreekt of wijkt af.", "De laatste meetpoging heeft geen bevestigde resultaten.",
  "Geen nieuwe bronmeting sinds de laatste storing.", "Een forkback-up ontbreekt.", "Geen leesrecht.",
]);

export function meldreden(reden: string | null | undefined) {
  return reden && MELDREDENEN.has(reden) ? reden : "De reden is niet beschikbaar.";
}

export interface Herstelpunt {
  id: string;
  app: string;
  checkpoint_id: string;
  gemaakt_op: string;
  snapshot: { actie_id?: string; datasets?: string[] } | null;
  db_export: { bron?: string; sha256?: string; id?: string } | null;
  status: string;
  reden: string | null;
}

export function puntDatasets(p: Herstelpunt) {
  const ds = p.snapshot?.datasets;
  if (!UUID.test(p.checkpoint_id) || p.snapshot?.actie_id !== p.checkpoint_id || !Array.isArray(ds) || !ds.length
    || ds.some(d => !datasetNaam(d)) || new Set(ds).size !== ds.length) return [];
  return ds;
}

export function databaseAanwezig(p: Herstelpunt) {
  return p.db_export?.bron === "pg_dump" && UUID.test(p.db_export.id ?? "") && /^[0-9a-f]{64}$/.test(p.db_export.sha256 ?? "");
}

const DATABASE_NODIG = new Set(["emby", "jellyfin", "jelly-leon", "mediaguard"]);
export function puntenReden(p: Herstelpunt, herkend: string | null, rpoUren: number | null | undefined, nu: number) {
  if (p.status === "ongezond") return "De hersteltest is mislukt.";
  if ((DATABASE_NODIG.has(p.app) || DATABASE_NODIG.has(herkend ?? "") || p.reden === "database_export_ontbreekt") && !databaseAanwezig(p))
    return "De vereiste database-export ontbreekt.";
  if (!puntDatasets(p).length || p.status !== "geverifieerd") return "Het herstelpunt is niet geverifieerd.";
  if (p.reden || !meettijd(p.gemaakt_op, nu) || typeof rpoUren !== "number" || !(rpoUren > 0 && Number.isFinite(rpoUren))
    || nu - Date.parse(p.gemaakt_op) > rpoUren * 3600_000) return "De leeftijd is onbekend of valt buiten de RPO.";
  return null;
}

export interface UploadTaak { id: number; status: string; beeindigd: string | null }
export function uploadStand(taak: UploadTaak, grens: number, nu: number) {
  if (taak.status !== "ok") return taak.status;
  if (!meettijd(taak.beeindigd, nu) || !(grens > 0 && Number.isFinite(grens))) return "unknown";
  return nu - Date.parse(taak.beeindigd!) > grens * 1000 ? "verouderd" : "ok";
}

export function uren(waarde: number | null | undefined) {
  return typeof waarde === "number" && Number.isFinite(waarde) && waarde >= 0 ? `${formatNumber(waarde)} uur` : "Onbekend";
}

export interface TestRecord {
  id: string; app_id: string | null; dataset: string | null; soort: string; resultaat: string; duur_minuten: number | null; uitgevoerd_op: string | null;
}
