import { koppelstatus, veiligAdres, type Koppeling } from "@/app/instellingen/diensten/adapterweergave";

export const KOPPELSCHERM = "/instellingen/diensten";

/** Meetkwaliteit inline bij het getal (Peil C-07). Onbekend is nooit een getal en nooit 0. */
export type Zekerheid = "gemeten" | "geschat" | "onbekend";

/** Antwoord van `GET /api/v1/adapterkoppelingen/{id}/mediaguard` (hub/adapters/mediaguard_lezen.py). */
export interface BronCijfer {
  status: "gemeten" | "onbekend";
  waarde: number | null;
  observed_at: string | null;
  reden: string | null;
}

export interface MediaGuardOverzicht {
  wanted: BronCijfer;
  status: BronCijfer;
  downloads: BronCijfer;
  av1: BronCijfer;
  incidenten: BronCijfer;
  noodstop: { status: "gemeten" | "onbekend"; actief: boolean | null; sinds: string | null; observed_at: string | null; reden: string | null };
  mediaservers: { status: "onbekend"; servers: null; reden: string };
  /** Strengste geldigheid per gegeven in seconden (bron, nooit ruimer dan 900 s); de noodstop volgt `status`. */
  max_age_s?: Partial<Record<"wanted" | "status" | "av1" | "incidenten", number>>;
}

export const MAX_AGE_MS = 900_000;

/** Grens in ms; ontbreekt (oudere Hub) = 900 s, een ongeldige waarde = direct verouderd, nooit ruimer dan 900 s. */
function grensMs(o: MediaGuardOverzicht | null, id: string): number {
  const s = (o?.max_age_s as Record<string, unknown> | undefined)?.[id];
  if (s === undefined) return MAX_AGE_MS;
  return typeof s === "number" && Number.isInteger(s) && s >= 0 ? Math.min(s * 1000, MAX_AGE_MS) : 0;
}

export interface Cijfer {
  id: string;
  titel: string;
  waarde: number | null;
  zekerheid: Zekerheid;
  observedAt: string | null;
  verouderd: boolean;
  reden: string | null;
}

export interface Mediaserver {
  label: string;
  verbonden: boolean | null;
  kijkpauze: boolean | null;
}

export interface MediaGuardWeergave {
  id: string;
  installatie: string;
  servers: Mediaserver[] | null;
  serversReden: string | null;
  noodstop: { actief: boolean | null; sinds: string | null; reden: string | null; observedAt: string | null };
  cijfers: Cijfer[];
}

export interface MsoWeergave {
  id: string;
  installatie: string;
  adres: string | null;
  gezondheid: { tekst: string; zekerheid: Zekerheid; observedAt: string | null; verouderd: boolean; reden: string | null };
}

const CIJFERS = [
  ["wanted", "Wanted · open"],
  ["status", "Status · mislukte jobs"],
  ["downloads", "Downloads · in de wachtrij"],
  ["av1", "AV1 · lopende encodes"],
  ["incidenten", "Incidenten · open"],
] as const;

/** BESLOTEN: MSO-onderdelen zonder bewezen leesrecht (MSO-leesbewijs volgt in versie 2). */
export const MSO_ONBEKEND = "onbekend: leesrecht niet bevestigd";

function installatie(k: Koppeling) {
  return veiligAdres(k.basis_url) ? new URL(k.basis_url).host : "Installatie zonder geldig adres";
}

/** Een meettijd die te lezen is en niet in de toekomst ligt; anders null. */
function meettijd(t: string | null, nu: number): number | null {
  const ms = t === null ? NaN : Date.parse(t);
  return Number.isFinite(ms) && ms <= nu ? ms : null;
}

/**
 * Alleen een `gemeten` waarde met geldige meettijd wordt een getal. Ouder dan de door de Hub geleverde grens
 * (zelf meegerekend in de browser, ook tussen twee peilingen; standaard 15 minuten) of een lijst die niet meer
 * ververst (`oud`) blijft zichtbaar als verouderd, nooit als actueel. Zonder overzicht is alles onbekend met `fout`.
 */
export function mediaguardWeergave(k: Koppeling, o: MediaGuardOverzicht | null, nu: number, oud: boolean, fout: string): MediaGuardWeergave {
  const nietActueel = "De Hub kon MediaGuard niet opnieuw lezen.";
  const cijfers: Cijfer[] = CIJFERS.map(([id, titel]) => {
    const c = o?.[id];
    const t = c ? meettijd(c.observed_at, nu) : null;
    if (!c || c.status !== "gemeten" || typeof c.waarde !== "number" || t === null) {
      // Een bekende bronmeettijd blijft zichtbaar als "laatst gemeten" (grijs), zonder getal.
      return { id, titel, waarde: null, zekerheid: "onbekend", observedAt: t === null ? null : c!.observed_at, verouderd: t !== null, reden: c?.reden ?? fout };
    }
    const verouderd = oud || nu - t > grensMs(o, id);
    return { id, titel, waarde: c.waarde, zekerheid: "gemeten", observedAt: c.observed_at, verouderd, reden: verouderd ? (oud ? nietActueel : "meting verouderd") : null };
  });
  const n = o?.noodstop;
  const nt = n ? meettijd(n.observed_at, nu) : null;
  const noodstopVers = n?.status === "gemeten" && typeof n.actief === "boolean" && nt !== null && !oud && nu - nt <= grensMs(o, "status");
  return {
    id: k.id,
    installatie: installatie(k),
    servers: null,
    serversReden: o?.mediaservers.reden ?? fout,
    noodstop: noodstopVers
      ? { actief: n.actief, sinds: n.sinds, reden: null, observedAt: n.observed_at }
      : { actief: null, sinds: null, reden: n?.status === "gemeten" ? (oud ? nietActueel : "meting verouderd") : n?.reden ?? fout, observedAt: nt === null ? null : n!.observed_at },
    cijfers,
  };
}

/** MSO-gezondheid = de openbare verbindingstest (S-P3-040); verouderd of onbevestigd is nooit actueel. */
export function msoWeergave(k: Koppeling, nu: number, lijstVerouderd: boolean): MsoWeergave {
  const stand = koppelstatus(k, nu);
  const tijd = k.verbinding.observed_at;
  const gemeten = tijd !== null && Number.isFinite(Date.parse(tijd)) && Date.parse(tijd) <= nu;
  const bereikbaar = k.verbinding.status === "healthy" || k.verbinding.laatste_status === "healthy";
  const actueel = stand.pil.label === "Gekoppeld" && !lijstVerouderd;
  return {
    id: k.id,
    installatie: installatie(k),
    adres: veiligAdres(k.basis_url) ? k.basis_url : null,
    gezondheid: gemeten && bereikbaar
      ? { tekst: "Bereikbaar", zekerheid: "gemeten", observedAt: tijd, verouderd: !actueel, reden: actueel ? null : stand.uitleg ?? "De Hub kon de lijst niet vernieuwen." }
      : { tekst: "Onbekend", zekerheid: "onbekend", observedAt: null, verouderd: false, reden: stand.uitleg ?? null },
  };
}

export type Eigenaar = "mediaguard" | "media-source-optimizer";

/** De vijf schakels van de downloadketen (S-P3-075, hub/incidents/downloadketen.py) met het scherm van de eigenaar. */
export const KETEN: { onderdeel: string; eigenaar: Eigenaar; scherm: string }[] = [
  { onderdeel: "Diagnose van het ontbrekende item", eigenaar: "mediaguard", scherm: "/ontbrekend" },
  { onderdeel: "Downloadfouten", eigenaar: "mediaguard", scherm: "/downloads" },
  { onderdeel: "Foutredenen van de bronnen", eigenaar: "media-source-optimizer", scherm: "/downloads" },
  { onderdeel: "Categoriediagnose", eigenaar: "media-source-optimizer", scherm: "/usenet-providers" },
  { onderdeel: "Compatibiliteit met MediaGuard", eigenaar: "media-source-optimizer", scherm: "/mediaguard" },
];

/** Net als de Hub-API: alleen bij precies één koppeling met een veilig adres naar het scherm van de eigenaar. */
export function ketenLink(koppelingen: Koppeling[], eigenaar: Eigenaar, scherm: string): string {
  const eigen = koppelingen.filter((k) => k.app_id === eigenaar);
  return eigen.length === 1 && veiligAdres(eigen[0]!.basis_url) ? eigen[0]!.basis_url.replace(/\/+$/, "") + scherm : KOPPELSCHERM;
}
