/**
 * Statuskleuren en -labels. Regel (contract §1): onbekend is `unknown`, nooit groen. Elke status heeft een tekstlabel
 * (niet alleen kleur) zodat hij ook zonder kleur en met een screenreader te lezen is.
 */

export type Tone = "ok" | "info" | "warn" | "bad" | "unknown" | "neutral";

export interface StatusView {
  tone: Tone;
  label: string;
}

const UNKNOWN: StatusView = { tone: "unknown", label: "Onbekend" };

export function kindStatus(status: string | null | undefined, verouderd = false): StatusView {
  if (status === "ok" && !verouderd) return { tone: "ok", label: "Actueel" };
  if (verouderd) return { tone: "unknown", label: "Verouderd (onbekend)" };
  return UNKNOWN;
}

export function decisionStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "Getest":
      return { tone: "ok", label: "Getest" };
    case "Ingevuld":
      return { tone: "info", label: "Ingevuld (nog niet getest)" };
    case "Geblokkeerd":
      return { tone: "bad", label: "Geblokkeerd" };
    case "N.v.t.":
      return { tone: "neutral", label: "N.v.t." };
    case "Open":
      return { tone: "warn", label: "Open" };
    default:
      return UNKNOWN;
  }
}

export function gateStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "toegestaan":
      return { tone: "ok", label: "Toegestaan" };
    case "geblokkeerd":
      return { tone: "bad", label: "Geblokkeerd" };
    default:
      return UNKNOWN;
  }
}

export function poolHealth(gezond: boolean | null | undefined, fresh: boolean): StatusView {
  if (!fresh) return UNKNOWN;
  if (gezond === true) return { tone: "ok", label: "Gezond" };
  if (gezond === false) return { tone: "bad", label: "Niet gezond" };
  return UNKNOWN;
}

/** TrueNAS-staat van een app. "Draait" is geen bewijs van gezond: daarom info, niet groen. */
export function appState(status: string | null | undefined): StatusView {
  switch (status) {
    case "draait":
      return { tone: "info", label: "Draait (gezondheid onbekend)" };
    case "gestopt":
      return { tone: "warn", label: "Gestopt" };
    case "gecrasht":
      return { tone: "bad", label: "Gecrasht" };
    case "bezig":
      return { tone: "info", label: "Bezig" };
    default:
      return UNKNOWN;
  }
}

export function coverageStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "gedekt":
      return { tone: "ok", label: "Gedekt" };
    case "geverifieerd":
      return { tone: "ok", label: "Geverifieerd" };
    case "niet_gedekt":
      return { tone: "bad", label: "Niet gedekt" };
    case "ontbreekt":
      return { tone: "bad", label: "Ontbreekt" };
    case "verouderd":
      return { tone: "warn", label: "Verouderd" };
    case "binnen":
      return { tone: "ok", label: "Binnen doel" };
    case "overschreden":
      return { tone: "bad", label: "Doel overschreden" };
    default:
      return UNKNOWN;
  }
}

export function testResult(resultaat: string | null | undefined): StatusView {
  if (resultaat === "geslaagd") return { tone: "ok", label: "Geslaagd" };
  if (resultaat === "mislukt") return { tone: "bad", label: "Mislukt" };
  return { tone: "unknown", label: "Geen hersteltest" };
}

export function measurementStatus(status: string | null | undefined): StatusView {
  switch (status) {
    case "geslaagd":
      return { tone: "ok", label: "Meting geslaagd" };
    case "afwijking":
      return { tone: "warn", label: "Afwijking" };
    case "voorstel":
      return { tone: "info", label: "Voorstel (kies zelf)" };
    case "mislukt":
      return { tone: "bad", label: "Meting mislukt" };
    default:
      return UNKNOWN;
  }
}

/** Slechtste toon van een lijst (voor een samenvatting). Onbekend weegt zwaarder dan ok: nooit "alles groen". */
export function worstTone(tones: Tone[]): Tone {
  const order: Tone[] = ["bad", "unknown", "warn", "info", "neutral", "ok"];
  for (const t of order) if (tones.includes(t)) return t;
  return "unknown";
}
