/**
 * Acties, previews en goedkeuringen in de browser (S-P2-170; ontwerp docs/ontwerp/HUB_P2_ONTWERP.md S-061 t/m S-066).
 *
 * Alleen getypte velden uit `GET /api/v1/actions/{id}` en `GET /api/v1/policy`; vrije tekst (de reden van een voorstel,
 * een weigeringsreden, een foutbericht van de executor) komt nooit in beeld. De server beslist over elk recht; de UI
 * leest alleen de sessierol uit `GET /api/v1/auth/me` om bediening te verbergen.
 */
import type { StatusView } from "./status";

export type RisicoKlasse = "R0" | "R1" | "R2" | "R3";

export interface Blokkade {
  id: string;
  code: string;
  reden: string;
}

export interface Goedkeuring {
  approval_id: string;
  approved_by: string;
  approved_at: string | null;
  expires_at: string | null;
  preview_hash: string;
  resource_etag: string;
  policy_hash: string;
  risk_class: string;
  backup_checkpoint_id: string | null;
  gebruikt_op: string | null;
  vervallen_op: string | null;
  vervallen_reden: string | null;
}

export interface Preview {
  omschrijving?: string;
  requires_backup?: boolean;
  kritiek?: boolean;
  huidig?: unknown;
  wijziging?: unknown;
  dataretentie?: string;
  terugdraaien?: string;
}

export interface ActieVerzoek {
  request_id: string;
  status: string;
  action_id: string;
  target: Record<string, unknown>;
  actor: { type: string; id: string };
  risk_class: string;
  risk_claim: string | null;
  risk_claim_genegeerd: boolean;
  rule_ids: string[];
  goedkeuring_nodig: boolean;
  policy_hash: string;
  uitvoerder: string;
  resource_etag: string | null;
  preview_hash: string | null;
  preview: Preview | null;
  blokkades: Blokkade[];
  goedkeuring: Goedkeuring | null;
  resultaat: Record<string, unknown> | null;
  aangemaakt_op: string | null;
  bijgewerkt_op: string | null;
  geldig_tot: string | null;
  gestart_op: string | null;
  uitgevoerd_op: string | null;
}

export interface ActieLijst {
  items: ActieVerzoek[];
  next_cursor: string | null;
  bijgewerkt_op: string;
}

export interface BeleidsActie {
  action_id: string;
  omschrijving: string;
  uitvoerder: string;
  doel: string;
  risk_class: string;
  risk_class_kritiek: string | null;
  risk_class_custom_app: string | null;
  requires_backup: boolean;
  cooldown_seconden: number | null;
}

export interface Beleid {
  policy_hash: string;
  acties: BeleidsActie[];
  verboden: { id: string; code: string; reden: string }[];
  gereserveerd: { id: string; code: string; reden: string }[];
  beschermd: { id: string; app: string; acties: string[] | null; reden: string }[];
}

export const WACHTLIJST = "/api/v1/actions?status=wacht_op_goedkeuring&limit=50";

export function risicoKlasse(v: string | null | undefined): RisicoKlasse | null {
  return v === "R0" || v === "R1" || v === "R2" || v === "R3" ? v : null;
}

/** ONTWERPTAAL §4.5: het woord staat altijd bij de klasse. */
export const RISICO_WOORD: Record<RisicoKlasse, string> = {
  R0: "Alleen lezen",
  R1: "Omkeerbaar",
  R2: "Goedkeuring nodig",
  R3: "Destructief — extra bevestiging",
};

const STATUS: Record<string, StatusView> = {
  wacht_op_goedkeuring: { tone: "gate", label: "Wacht op goedkeuring" },
  klaar: { tone: "neutral", label: "Klaar om uit te voeren", icon: "open" },
  goedgekeurd: { tone: "info", label: "Goedgekeurd, nog niet uitgevoerd" },
  afgewezen: { tone: "neutral", label: "Afgewezen", icon: "min" },
  geweigerd: { tone: "down", label: "Geweigerd door het beleid" },
  bezig: { tone: "info", label: "Uitvoering bezig" },
  uitgevoerd: { tone: "neutral", label: "Uitgevoerd en gecontroleerd", icon: "geslaagd" },
  mislukt: { tone: "down", label: "Mislukt" },
  afwijking: { tone: "degraded", label: "Gestopt: afwijking na uitvoering" },
  onbekend: { tone: "unknown", label: "Uitkomst onbekend" },
  verlopen: { tone: "paused", label: "Verlopen" },
};

/** Een onbekende status is nooit een succes. */
export function statusView(status: string): StatusView {
  return STATUS[status] ?? { tone: "unknown", label: "Onbekende status" };
}

const ACTIE_WERKWOORD: Record<string, string> = {
  "app.install": "Installeren",
  "app.uninstall": "Verwijderen",
  "app.update": "Bijwerken",
  "app.rollback": "Terugzetten",
  "app.stop": "Stoppen",
  "app.start": "Starten",
  "app.restart": "Herstarten",
};

export function werkwoord(actionId: string): string {
  return ACTIE_WERKWOORD[actionId] ?? "Goedkeuren";
}

const DOEL_VELDEN = ["app_id", "dataset", "snapshot", "resource", "host_id"] as const;
const DOEL_RE = /^[A-Za-z0-9][A-Za-z0-9_.@/:-]{0,199}$/;

/** Alleen bekende doelvelden met een vaste vorm (zoals ``veilig_doel`` in de API). */
export function doelVelden(target: Record<string, unknown> | null | undefined): [string, string][] {
  return DOEL_VELDEN.flatMap((k) => {
    const w = target?.[k];
    return typeof w === "string" && DOEL_RE.test(w) ? [[k, w] as [string, string]] : [];
  });
}

/** De naam van het doel (vaste vorm), of null als het doel geen herkenbare naam heeft. */
export function doelNaam(target: Record<string, unknown> | null | undefined): string | null {
  for (const k of DOEL_VELDEN) {
    const w = target?.[k];
    if (typeof w === "string" && DOEL_RE.test(w)) return w;
  }
  return null;
}

/** R3: de gevaarknop werkt alleen bij exact dezelfde naam (geen trim, geen hoofdletterongevoeligheid). */
export function naamKlopt(invoer: string, naam: string | null): boolean {
  return naam !== null && invoer === naam;
}

// ------------------------------------------------------------------ weigeren (R-ONTWERP-1)
/** Vaste weigeringsredenen. Alleen deze teksten verschijnen ooit weer in beeld; een andere reden is vrije tekst. */
export const WEIGER_REDENEN = [
  "Het doel klopt niet.",
  "De wijziging is niet nodig.",
  "Het risico is te groot.",
  "Eerst een back-up maken.",
  "Op een ander moment uitvoeren.",
] as const;

export const REDEN_ONTOONBAAR = "Afgewezen — reden niet weer te geven";

export function weigerReden(resultaat: Record<string, unknown> | null | undefined): string {
  const m = resultaat?.message;
  return typeof m === "string" && (WEIGER_REDENEN as readonly string[]).includes(m) ? `Afgewezen — ${m}` : REDEN_ONTOONBAAR;
}

// ------------------------------------------------------------------ vervallen
const VELD_LABEL: Record<string, string> = {
  preview_hash: "de preview",
  resource_etag: "het doel",
  policy_hash: "het risicobeleid",
  risk_class: "de risicoklasse",
  action_scope: "de reikwijdte",
  backup_checkpoint_id: "het herstelpunt",
};

export const VOORSTEL_VERLOPEN = "Voorstel verlopen. Vraag een nieuw voorstel aan.";

export function vervallenTekst(velden: string[]): string {
  const namen = [...new Set(velden.map((v) => VELD_LABEL[v] ?? "een gebonden veld"))];
  const lijst = namen.length > 1 ? `${namen.slice(0, -1).join(", ")} en ${namen.at(-1)}` : (namen[0] ?? "een gebonden veld");
  return `Goedkeuring vervallen: ${lijst} ${namen.length > 1 ? "zijn" : "is"} gewijzigd na de preview. Vraag een nieuw voorstel aan.`;
}

export type Hashes = Pick<ActieVerzoek, "preview_hash" | "resource_etag" | "policy_hash">;
const HASH_VELDEN = ["preview_hash", "resource_etag", "policy_hash"] as const;

/** Waarom deze preview niet meer beslist kan worden, of null. `gezien` = de hashes die de gebruiker eerst zag. */
export function vervallen(v: ActieVerzoek, gezien: Hashes | null, nu: Date): string | null {
  if (v.status === "verlopen" || (v.geldig_tot !== null && Date.parse(v.geldig_tot) <= nu.getTime())) return VOORSTEL_VERLOPEN;
  if (gezien) {
    const anders = HASH_VELDEN.filter((k) => gezien[k] !== v[k]);
    if (anders.length) return vervallenTekst([...anders]);
  }
  const reden = v.goedkeuring?.vervallen_reden;
  if (reden?.startsWith("gewijzigd:") && !v.goedkeuring?.gebruikt_op) return vervallenTekst(reden.slice(10).split(","));
  return null;
}

// ------------------------------------------------------------------ diff (C-20)
export interface DiffRegel {
  soort: "gewijzigd" | "toegevoegd" | "verwijderd";
  veld: string;
  was?: string;
  wordt?: string;
}

const MAX_TEKST = 300;
const MAX_DIEPTE = 5;
const STUURTEKEN = /[\u0000-\u001f\u007f\u2028\u2029\u202a-\u202e\u2066-\u2069]/;

class Onveilig extends Error {}

function blad(w: unknown): string {
  if (w === null || w === undefined || w === "") return "(leeg)";
  if (typeof w === "boolean") return w ? "ja" : "nee";
  if (typeof w === "number") return Number.isFinite(w) ? String(w) : "(leeg)";
  if (typeof w === "string") {
    if (w.length > MAX_TEKST || STUURTEKEN.test(w)) throw new Onveilig();
    return w === "***" ? "*** (geheim, niet getoond)" : w;
  }
  throw new Onveilig();
}

function plat(w: unknown, pad: string, diepte: number, uit: Map<string, string>): void {
  if (diepte > MAX_DIEPTE) throw new Onveilig();
  if (Array.isArray(w)) {
    if (w.every((x) => x === null || typeof x !== "object")) {
      uit.set(pad, w.length ? w.map(blad).join(", ") : "(leeg)");
      return;
    }
    w.forEach((x, i) => plat(x, `${pad}[${i}]`, diepte + 1, uit));
    return;
  }
  if (w !== null && typeof w === "object") {
    const entries = Object.entries(w as Record<string, unknown>);
    if (!entries.length) uit.set(pad, "(leeg)");
    for (const [k, x] of entries) {
      if (STUURTEKEN.test(k) || k.length > 80) throw new Onveilig();
      plat(x, pad ? `${pad}.${k}` : k, diepte + 1, uit);
    }
    return;
  }
  uit.set(pad, blad(w));
}

/**
 * Was/Wordt per veld uit `preview.huidig` en `preview.wijziging`. `onveilig` = er staat een regel in die niet volledig
 * en veilig kan worden uitgelegd (te lang, stuurtekens, te diep of geen gewone waarde): dan blokkeert de goedkeuring.
 */
export function diffRegels(preview: Preview | null | undefined): { regels: DiffRegel[]; onveilig: boolean } {
  const wijziging = preview?.wijziging;
  if (!wijziging || typeof wijziging !== "object" || Array.isArray(wijziging)) return { regels: [], onveilig: true };
  try {
    const huidig = new Map<string, string>();
    if (preview?.huidig && typeof preview.huidig === "object") plat(preview.huidig, "", 0, huidig);
    const { soort: _soort, van, ...rest } = wijziging as Record<string, unknown>;
    void _soort;
    const nieuw = new Map<string, string>();
    plat(rest, "", 0, nieuw);
    const regels: DiffRegel[] = [];
    const vanTekst = van === undefined ? null : new Map<string, string>();
    if (vanTekst) plat({ v: van }, "", 0, vanTekst);
    for (const [veld, wordt] of nieuw) {
      if ((veld === "naar" || veld === "naar_catalogusversie") && vanTekst) {
        regels.push({ soort: "gewijzigd", veld, was: [...vanTekst.values()].join(", "), wordt });
        continue;
      }
      const was = huidig.get(veld);
      if (was === undefined) regels.push({ soort: "toegevoegd", veld, wordt });
      else if (was !== wordt) regels.push({ soort: "gewijzigd", veld, was, wordt });
    }
    if ((wijziging as Record<string, unknown>).soort === "verwijderen") {
      const app = (wijziging as Record<string, unknown>).app;
      regels.unshift({ soort: "verwijderd", veld: "app", was: blad(app) });
    }
    return { regels, onveilig: false };
  } catch (e) {
    if (e instanceof Onveilig) return { regels: [], onveilig: true };
    throw e;
  }
}

/** Een getypte resultaatcode in woorden; nooit het vrije foutbericht. */
export function resultaatCode(resultaat: Record<string, unknown> | null | undefined): string | null {
  const c = resultaat?.code;
  return typeof c === "string" && /^[a-z][a-z0-9_]{0,63}$/.test(c) ? c : null;
}
