import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = path.resolve(import.meta.dirname, "..", "..");
const bron = readFileSync(path.join(root, "..", "..", "design", "ontwerptaal", "ontwerptaal.css"), "utf8");
const kopie = readFileSync(path.join(root, "src", "app", "peil", "ontwerptaal.css"), "utf8");

// Pin- en driftregel (ONTWERPTAAL §14, Peil 1.1.1 E08): de kopie pint een versie + de sha256 van de bron bij die versie.
// Falen: de kopie is met de hand gewijzigd (sha past niet bij de eigen inhoud) of de bron heeft dezelfde versie met
// andere inhoud. Een nieuwere bronversie is alleen een waarschuwing: bijwerken = node scripts/peil-kopie.mjs + tests.
const versieVan = (t: string) => /Peil (\d+)\.(\d+)\.(\d+)/.exec(t)?.slice(1).map(Number) ?? [];
const vergelijk = (a: number[], b: number[]) => a.map((x, i) => x - (b[i] ?? 0)).find((d) => d !== 0) ?? 0;

describe("Peil-tokens (O-14: versie-gepinde kopie met herkomstkop + sha256)", () => {
  it("de kop pint versie en sha256; de inhoud is ongewijzigd en dezelfde bronversie is byte-gelijk", () => {
    const [kop1 = "", kop2 = "", ...rest] = kopie.split("\n");
    const inhoud = rest.join("\n");
    const pinSha = /sha256:([0-9a-f]{64})/.exec(kop1)?.[1];
    expect(pinSha, "herkomstkop zonder sha256").toBeTruthy();
    expect(createHash("sha256").update(inhoud).digest("hex"), "kopie met de hand gewijzigd").toBe(pinSha);
    expect(kop2).toContain("niet met de hand wijzigen");
    const pin = versieVan(kop1);
    const bronVersie = versieVan(bron);
    const verschil = vergelijk(bronVersie, pin);
    expect(verschil, "bron is ouder dan de gepinde kopie").toBeGreaterThanOrEqual(0);
    if (verschil === 0) expect(inhoud, "zelfde Peil-versie met andere inhoud in de bron").toBe(bron);
    else console.warn(`Peil ${bronVersie.join(".")} staat in design/ontwerptaal; de Hub-kopie pint ${pin.join(".")}. Bijwerken: node scripts/peil-kopie.mjs`);
  });

  it("globals.css importeert Tailwind en de Peil-kopie, zonder eigen kleurblokken of hex-kleuren", () => {
    const css = readFileSync(path.join(root, "src", "app", "globals.css"), "utf8");
    expect(css).toMatch(/@import "tailwindcss";\s*@import "\.\/peil\/ontwerptaal\.css";/);
    expect(css).not.toMatch(/prefers-color-scheme/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/var\(--muted\)(?!-)/);
  });
});
