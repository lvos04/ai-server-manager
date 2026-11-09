/**
 * Statusweergave in Peil (ONTWERPTAAL §4, HUB_PEIL_ONTWERP §2.4). Regels:
 * - groen ("Gezond") alleen voor *gemeten en goed*; een geslaagde test, "gekoppeld", "aan" of "draait" is neutraal;
 * - verouderd is nooit gezond; onbekend is nooit 0 en nooit groen;
 * - open besluiten en dichte gates zijn geen storing (geen rood/amber), rood alleen bij gemeten falen;
 * - elke status heeft een woord + icoon (niet alleen kleur).
 */

/** Assen: gezondheid (healthy…not_yet) en de neutrale vormen voor toestanden die geen gezondheid zijn. */
export type Tone =
  | "healthy"
  | "degraded"
  | "down"
  | "unknown"
  | "stale"
  | "paused"
  | "unlinked"
  | "not_yet"
  | "neutral"
  | "info"
  | "gate";

export type IconKey =
  | "draait"
  | "gekoppeld"
  | "ingesteld"
  | "geslaagd"
  | "ingetrokken"
  | "open"
  | "ingevuld"
  | "getest"
  | "slot"
  | "slot-open"
  | "min"
  | "rol"
  | "aan"
  | "rotatie";

export interface StatusView {
  tone: Tone;
  label: string;
  /** Vaste koppeling (ONTWERPTAAL §7 + OB-13) voor neutrale pillen; gezondheid gebruikt altijd het eigen icoon. */
  icon?: IconKey;
}

export const WORD: Record<Exclude<Tone, "neutral" | "info" | "gate">, string> = {
  healthy: "Gezond",
  degraded: "Beperkt",
  down: "Storing",
  unknown: "Onbekend",
  stale: "Verouderd",
  paused: "Gepauzeerd",
  unlinked: "Niet gekoppeld",
  not_yet: "Nog niet beschikbaar",
};

const UNKNOWN: StatusView = { tone: "unknown", label: "Onbekend" };

/** API-status (healthy/degraded/down/unknown) → weergave. Alles wat geen bekende status is, is Onbekend. */
export function healthView(status: string | null | undefined, verouderd = false): StatusView {
  if (verouderd) return { tone: "stale", label: "Verouderd" };
  switch (status) {
    case "healthy":
      return { tone: "healthy", label: "Gezond" };
    case "degraded":
      return { tone: "degraded", label: "Beperkt" };
    case "down":
      return { tone: "down", label: "Storing" };
    default:
      return UNKNOWN;
  }
}

/** Inventarissoort: vers = geen badge (de tijd zegt genoeg, K3); verouderd = Verouderd; anders Onbekend. */
export function kindStatus(status: string | null | undefined, verouderd = false): StatusView | null {
  if (status === "ok" && !verouderd) return null;
  if (verouderd) return { tone: "stale", label: "Verouderd" };
  return UNKNOWN;
}

/** Besluitstatus (C-10): nooit een statuskleur — open is geen storing. */
export function decisionStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "Getest":
      return { tone: "neutral", label: "Getest", icon: "getest" };
    case "Ingevuld":
      return { tone: "neutral", label: "Ingevuld (nog niet getest)", icon: "ingevuld" };
    case "Geblokkeerd":
      return { tone: "gate", label: "Geblokkeerd" };
    case "N.v.t.":
      return { tone: "neutral", label: "N.v.t.", icon: "min" };
    case "Open":
      return { tone: "neutral", label: "Open", icon: "open" };
    default:
      return UNKNOWN;
  }
}

/** Gate (C-11): dicht = slot, neutraal-sterk ("Dit is geen storing"); onbekend opent nooit. */
export function gateStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "toegestaan":
      return { tone: "neutral", label: "Toegestaan", icon: "slot-open" };
    case "geblokkeerd":
      return { tone: "gate", label: "Geblokkeerd" };
    default:
      return { tone: "unknown", label: "Onbekend (blijft dicht)" };
  }
}

/** Pool: Gezond / Beperkt (DEGRADED) / Storing (FAULTED, UNAVAIL, niet gezond); niet vers = Onbekend. */
export function poolHealth(gezond: boolean | null | undefined, fresh: boolean, poolStatus?: string | null): StatusView {
  if (!fresh) return UNKNOWN;
  const s = (poolStatus ?? "").toUpperCase();
  if (s === "DEGRADED") return { tone: "degraded", label: "Beperkt" };
  if (["FAULTED", "UNAVAIL", "OFFLINE", "REMOVED", "SUSPENDED"].includes(s)) return { tone: "down", label: "Storing" };
  if (gezond === true) return { tone: "healthy", label: "Gezond" };
  if (gezond === false) return { tone: "down", label: "Storing" };
  return UNKNOWN;
}

/** TrueNAS-staat van een app: een neutrale pil — "Draait" is geen bewijs van gezond. Gecrasht = gemeten falen. */
export function appState(status: string | null | undefined): StatusView {
  switch ((status ?? "").toLowerCase()) {
    case "draait":
    case "running":
      return { tone: "neutral", label: "Draait", icon: "draait" };
    case "gestopt":
    case "stopped":
      return { tone: "neutral", label: "Gestopt", icon: "draait" };
    case "gecrasht":
    case "crashed":
      return { tone: "down", label: "Storing (gecrasht)" };
    case "bezig":
    case "deploying":
    case "stopping":
      return { tone: "info", label: "Bezig" };
    default:
      return UNKNOWN;
  }
}

/** Back-updekking (DekkingsMatrix C-33): symbool + woord, geen kleurvlakken; overschreden = Beperkt (gemeten). */
export function coverageStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "gedekt":
      return { tone: "neutral", label: "Gedekt", icon: "geslaagd" };
    case "geverifieerd":
      return { tone: "neutral", label: "Geverifieerd", icon: "geslaagd" };
    case "niet_gedekt":
      return { tone: "neutral", label: "Niet gedekt", icon: "min" };
    case "ontbreekt":
      return { tone: "neutral", label: "Ontbreekt", icon: "min" };
    case "verouderd":
      return { tone: "stale", label: "Verouderd" };
    case "binnen":
      return { tone: "neutral", label: "Binnen doel", icon: "geslaagd" };
    case "overschreden":
      return { tone: "degraded", label: "Doel overschreden" };
    default:
      return UNKNOWN;
  }
}

/** Hersteltest (TestResultaat C-58): Geslaagd neutraal, Mislukt = gemeten falen, geen test = Onbekend. */
export function testResult(resultaat: string | null | undefined): StatusView {
  if (resultaat === "geslaagd") return { tone: "neutral", label: "Geslaagd", icon: "geslaagd" };
  if (resultaat === "mislukt") return { tone: "down", label: "Mislukt" };
  return { tone: "unknown", label: "Geen hersteltest" };
}

export function measurementStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "geslaagd":
      return { tone: "neutral", label: "Meting geslaagd", icon: "geslaagd" };
    case "afwijking":
      return { tone: "degraded", label: "Afwijking" };
    case "voorstel":
      return { tone: "info", label: "Voorstel (kies zelf)" };
    case "mislukt":
      return { tone: "down", label: "Meting mislukt" };
    default:
      return UNKNOWN;
  }
}

/** Telt mee voor de totaalstatus? Gepauzeerd, nog-niet, neutraal, info en gate tellen niet mee (Peil §4.3). */
export function counts(t: Tone): boolean {
  return t === "healthy" || t === "degraded" || t === "down" || t === "unknown" || t === "stale" || t === "unlinked";
}

/**
 * Slechtste gezondheid van een lijst (OB-06): Storing > Beperkt > (Deels) Onbekend > Gezond. Verouderd en
 * niet-gekoppeld tellen als onbekend. Zonder meetbare onderdelen: Onbekend (nooit "alles gezond").
 */
export function worstTone(tones: Tone[]): "healthy" | "degraded" | "down" | "unknown" {
  const c = tones.filter(counts);
  if (c.includes("down")) return "down";
  if (c.includes("degraded")) return "degraded";
  if (!c.length || c.some((t) => t === "unknown" || t === "stale" || t === "unlinked")) return "unknown";
  return "healthy";
}

/** Vaste woorden van de totaalstatus (ONTWERPTAAL §11.1). */
export const TOTAAL_LABEL: Record<"healthy" | "degraded" | "down" | "unknown", string> = {
  healthy: "Alles gezond",
  degraded: "Beperkt",
  down: "Storing",
  unknown: "Deels onbekend",
};

/** Ernst (OB-05): de API kent drie niveaus; Hoog en Laag worden in P1 niet gebruikt. */
export type Ernst = "kritiek" | "hoog" | "middel" | "laag" | "info";
export function ernstVan(api: string | null | undefined): Ernst {
  if (api === "kritiek") return "kritiek";
  if (api === "waarschuwing") return "middel";
  if (api === "info") return "info";
  return "middel";
}
export const ERNST_LABEL: Record<Ernst, string> = { kritiek: "Kritiek", hoog: "Hoog", middel: "Middel", laag: "Laag", info: "Info" };
export const ERNST_RANG: Record<Ernst, number> = { kritiek: 0, hoog: 1, middel: 2, laag: 3, info: 4 };

/** Zekerheid (OB-04): getal → woord, nooit een percentage. */
export type Zekerheid = "zeker" | "waarschijnlijk" | "onzeker" | "weet_niet";
export function zekerheidVan(z: number | null | undefined): Zekerheid {
  if (typeof z !== "number" || !Number.isFinite(z)) return "weet_niet";
  if (z >= 0.85) return "zeker";
  if (z >= 0.6) return "waarschijnlijk";
  return "onzeker";
}
export const ZEKERHEID_LABEL: Record<Zekerheid, string> = {
  zeker: "Zeker",
  waarschijnlijk: "Waarschijnlijk",
  onzeker: "Onzeker",
  weet_niet: "Ik weet het niet",
};
