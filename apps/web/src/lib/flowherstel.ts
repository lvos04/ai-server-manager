import type { ActieVerzoek, DiffRegel, Preview } from "./acties";
import { UUID } from "./backups";

export const FLOWHERSTEL = "automation.flows.restore";

export function menselijkHerstel(v: ActieVerzoek) {
  return v.action_id === FLOWHERSTEL && v.actor?.type === "user" && v.risk_class === "R2"
    && v.target?.app_id === "home-control-hub" && v.target.resource === "node_red";
}

function record(x: unknown): Record<string, unknown> {
  return x !== null && typeof x === "object" && !Array.isArray(x) ? x as Record<string, unknown> : {};
}

export function herstelbewijs(v: ActieVerzoek) {
  const rb = record(v.resultaat?.readback);
  const id = rb.snapshot_id;
  const sha = rb.checksum_sha256;
  if (v.status !== "uitgevoerd" || !menselijkHerstel(v) || rb.gelezen !== true || rb.gelijk_aan_momentopname !== true
    || typeof id !== "string" || !UUID.test(id) || typeof sha !== "string" || !/^[0-9a-f]{64}$/.test(sha)
    || v.resultaat?.after_hash !== `sha256:${sha}`) return null;
  return id;
}

export function flowStatus(v: ActieVerzoek, oud = false) {
  if (v.status === "uitgevoerd" && (oud || (v.action_id === FLOWHERSTEL && !herstelbewijs(v)))) return "onbekend";
  return v.status;
}

const NODE_ID = /^[0-9a-f]{1,16}(?:\.[0-9a-f]{1,16})?$/i;
const TYPES = new Set(["tab", "subflow", "inject", "debug", "change", "switch", "link in", "link out", "link call",
  "catch", "status", "comment", "function", "delay", "trigger", "junction", "hub-events", "hub-action"]);
const VELDEN = new Set(["name", "label", "x", "y", "z", "wires", "type", "disabled", "d", "info", "rules", "outputs", "props", "repeat", "topic", "payload", "func", "links"]);

/** Een eigenaar levert een diff per node met veldnamen. Alleen volledig verklaarbare rijen mogen naar de preview. */
export function flowDiff(preview: Preview | null | undefined): { regels: DiffRegel[]; onveilig: boolean } {
  const onveilig = { regels: [], onveilig: true };
  const w = record(preview?.wijziging);
  const diff = record(w.diff);
  const aantallen = record(diff.aantallen);
  if (!Object.keys(w).every(k => ["soort", "eigenaar", "preview_hash_eigenaar", "requires_backup", "diff"].includes(k))) return onveilig;
  if (w.soort !== FLOWHERSTEL || w.eigenaar !== "home-control-hub" || diff.afgekapt !== false || diff.waarden_getoond !== false
    || !Object.keys(diff).every(k => ["aantallen", "afgekapt", "waarden_getoond", "gelijk", "toegevoegd", "verwijderd", "gewijzigd"].includes(k))) return onveilig;
  const regels: DiffRegel[] = [];
  for (const soort of ["toegevoegd", "verwijderd", "gewijzigd"] as const) {
    const rijen = diff[soort];
    if (!Array.isArray(rijen) || rijen.length !== aantallen[soort]) return onveilig;
    for (const rij of rijen) {
      const r = record(rij);
      if (typeof r.id !== "string" || !NODE_ID.test(r.id) || typeof r.type !== "string" || !TYPES.has(r.type)
        || !(r.z === null || (typeof r.z === "string" && NODE_ID.test(r.z)))
        || !Object.keys(r).every(k => ["id", "type", "z", ...(soort === "gewijzigd" ? ["velden"] : [])].includes(k))) return onveilig;
      let omschrijving = r.type;
      if (soort === "gewijzigd") {
        if (!Array.isArray(r.velden) || !r.velden.length || !r.velden.every(k => typeof k === "string" && VELDEN.has(k))) return onveilig;
        omschrijving += ` · velden ${r.velden.join(", ")}`;
      }
      regels.push({ soort, veld: `Node ${r.id}${r.z ? ` · flow ${r.z}` : ""}`, ...(soort === "verwijderd" ? { was: omschrijving } : { wordt: omschrijving }) });
    }
  }
  // Een herstel met alleen een wijziging van inloggegevens levert geen veldregels op bij de Hub.
  return regels.length ? { regels, onveilig: false } : onveilig;
}
