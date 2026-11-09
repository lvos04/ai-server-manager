import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = path.resolve(import.meta.dirname, "..", "..");
const bron = readFileSync(path.join(root, "..", "..", "design", "ontwerptaal", "ontwerptaal.css"), "utf8");
const kopie = readFileSync(path.join(root, "src", "app", "peil", "ontwerptaal.css"), "utf8");

describe("Peil-tokens (O-14: versie-gepinde kopie met herkomstkop + sha256)", () => {
  it("de kop noemt de sha256 van de bron in design/ontwerptaal en de rest is er een exacte kopie van", () => {
    const sha = createHash("sha256").update(bron).digest("hex");
    const [kop1, kop2, ...rest] = kopie.split("\n");
    expect(kop1).toContain(`sha256:${sha}`);
    expect(kop1).toContain("Peil 1.1.0");
    expect(kop2).toContain("niet met de hand wijzigen");
    expect(rest.join("\n")).toBe(bron);
  });

  it("globals.css importeert Tailwind en de Peil-kopie, zonder eigen kleurblokken of hex-kleuren", () => {
    const css = readFileSync(path.join(root, "src", "app", "globals.css"), "utf8");
    expect(css).toMatch(/@import "tailwindcss";\s*@import "\.\/peil\/ontwerptaal\.css";/);
    expect(css).not.toMatch(/prefers-color-scheme/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/var\(--muted\)(?!-)/);
  });
});
