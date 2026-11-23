import { existsSync, lstatSync, mkdirSync, realpathSync } from "node:fs";
import path from "node:path";

/** Toegestane afdrukmappen: alleen fasemappen p1, p2, p3, … direct onder docs/screenshots (HUB_E2E_SHOTS). */
const FASEMAP = /^p[0-9]{1,2}$/;

/**
 * Kiest en maakt de afdrukmap `<wortel>/<fase>/<project>` voor de web-E2E. Leeg of niet gezet = p1. Elke andere waarde
 * dan een fasemap wordt geweigerd vóór er iets wordt aangemaakt. Bestaande delen moeten echte mappen zijn waarvan het
 * realpath exact onder het realpath van de wortel ligt, zodat een symbolische koppeling niet naar buiten kan wijzen.
 */
export function afdrukMap(wortel: string, waarde: string | undefined, project: string): string {
  const fase = waarde === undefined || waarde === "" ? "p1" : waarde;
  if (!FASEMAP.test(fase)) throw new Error(`HUB_E2E_SHOTS: alleen p1, p2, p3, … onder docs/screenshots (kreeg ${JSON.stringify(waarde)})`);
  if (!/^[a-z0-9-]+$/.test(project)) throw new Error(`ongeldige projectnaam voor afdrukken: ${JSON.stringify(project)}`);
  const echteWortel = realpathSync(wortel);
  for (const deel of [[fase], [fase, project]]) {
    const pad = path.join(wortel, ...deel);
    if (!existsSync(pad) && !isLink(pad)) continue;
    if (isLink(pad) || !lstatSync(pad).isDirectory() || realpathSync(pad) !== path.join(echteWortel, ...deel)) {
      throw new Error(`afdrukmap ${pad} is geen gewone map onder ${wortel}`);
    }
  }
  const doel = path.join(wortel, fase, project);
  mkdirSync(doel, { recursive: true });
  return doel;
}

/** Een bestaand afdrukbestand mag geen symbolische koppeling zijn (de browser zou erdoorheen schrijven). */
export function afdrukBestand(map: string, naam: string): string {
  if (!/^[A-Za-z0-9-]+$/.test(naam)) throw new Error(`ongeldige afdruknaam: ${JSON.stringify(naam)}`);
  const pad = path.join(map, `${naam}.jpg`);
  if (isLink(pad)) throw new Error(`afdrukbestand ${pad} is een symbolische koppeling`);
  return pad;
}

function isLink(pad: string): boolean {
  try {
    return lstatSync(pad).isSymbolicLink();
  } catch {
    return false;
  }
}
