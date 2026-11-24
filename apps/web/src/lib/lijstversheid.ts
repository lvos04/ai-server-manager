import { brontijd } from "./format";

// Dezelfde bovengrens als voor een inventarisbron. Een kortere geldigheid van een individuele meting blijft gelden.
export const LIJST_MAX_LEEFTIJD_MS = 15 * 60_000;

export function lijstIsVers(tijd: string | null | undefined, nu: number): boolean {
  const leeftijd = nu - brontijd(tijd);
  return leeftijd >= 0 && leeftijd <= LIJST_MAX_LEEFTIJD_MS;
}
