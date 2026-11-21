import { koppelstatus, veiligAdres, type Koppeling } from "@/app/instellingen/diensten/adapterweergave";

export const KOPPELSCHERM = "/instellingen/diensten";

/** Meetkwaliteit inline bij het getal (Peil C-07). Onbekend is nooit een getal en nooit 0. */
export type Zekerheid = "gemeten" | "geschat" | "onbekend";

export interface Meting {
  status: string;
  observed_at: string | null;
  reason_code: string | null;
}

export interface MediaKoppeling extends Koppeling {
  mediaguard?: Partial<Record<string, Meting>>;
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
  noodstop: { actief: boolean | null; sinds: string | null; reden: string | null };
  cijfers: Cijfer[];
}

export interface MsoWeergave {
  id: string;
  installatie: string;
  adres: string | null;
  gezondheid: { tekst: string; zekerheid: Zekerheid; observedAt: string | null; verouderd: boolean; reden: string | null };
}

const CIJFERS = [
  ["wanted", "Wanted"],
  ["status", "Status"],
  ["downloads", "Downloads"],
  ["av1", "AV1"],
  ["incidenten", "Incidenten"],
] as const;

/** BESLOTEN: MSO-onderdelen zonder bewezen leesrecht (MSO-leesbewijs volgt in versie 2). */
export const MSO_ONBEKEND = "onbekend: leesrecht niet bevestigd";

export function reden(code: string | null | undefined): string {
  if (code === "geen_alleen_lezen_bron") return "geen alleen-lezen bron: MediaGuard biedt nog geen veilige leescontrole";
  if (code === "doelbinding") return "de bestemming is niet meer bevestigd";
  return "geen bevestigde meting";
}

function installatie(k: Koppeling) {
  return veiligAdres(k.basis_url) ? new URL(k.basis_url).host : "Installatie zonder geldig adres";
}

/**
 * De Hub-API levert voor MediaGuard alleen `unknown` met een reden (S-P3-030: geen alleen-lezen bron). Daarom wordt
 * elk cijfer hier onbekend; een waarde komt pas uit de API zodra die bron er is.
 * shortcut: geen pad voor gemeten MediaGuard-waarden, uitbreiden zodra de Hub-API ze levert (VERSIE 2).
 */
export function mediaguardWeergave(k: MediaKoppeling): MediaGuardWeergave {
  const r = k.mediaguard ?? {};
  return {
    id: k.id,
    installatie: installatie(k),
    servers: null,
    serversReden: reden(r.mediaservers?.reason_code),
    noodstop: { actief: null, sinds: null, reden: reden(r.noodstop?.reason_code) },
    cijfers: CIJFERS.map(([id, titel]) => ({
      id, titel, waarde: null, zekerheid: "onbekend", observedAt: null, verouderd: false, reden: reden(r[id]?.reason_code),
    })),
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
