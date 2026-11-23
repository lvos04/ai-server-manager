import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { afdrukBestand, afdrukMap } from "../../e2e/afdrukmap";

let basis: string;
let wortel: string;
let buiten: string;

beforeEach(() => {
  basis = mkdtempSync(path.join(process.env.TMPDIR ?? os.tmpdir(), "afdrukmap-"));
  wortel = path.join(basis, "docs", "screenshots");
  buiten = path.join(basis, "buiten");
  mkdirSync(wortel, { recursive: true });
  mkdirSync(buiten);
});
afterEach(() => rmSync(basis, { recursive: true, force: true }));

describe("afdrukMap (HUB_E2E_SHOTS)", () => {
  it("niet gezet of leeg kiest p1, nooit de werkmap van de web-UI", () => {
    expect(afdrukMap(wortel, undefined, "mobiel-360")).toBe(path.join(wortel, "p1", "mobiel-360"));
    expect(afdrukMap(wortel, "", "desktop-1440")).toBe(path.join(wortel, "p1", "desktop-1440"));
    expect(existsSync(path.join(wortel, "p1", "desktop-1440"))).toBe(true);
  });

  it("een fasemap zoals p3 is toegestaan", () => {
    expect(afdrukMap(wortel, "p3", "tablet-768")).toBe(path.join(wortel, "p3", "tablet-768"));
  });

  it.each([".", "..", "../p1", "/tmp/elders", "/var/tmp/buiten/p3", "apps/web", "p3/../../x", "P3", "p", "p3x", " p3"])(
    "weigert %j zonder iets aan te maken",
    (waarde) => {
      expect(() => afdrukMap(wortel, waarde, "mobiel-390")).toThrow(/HUB_E2E_SHOTS/);
      expect(readdirSync(wortel)).toEqual([]);
      expect(readdirSync(buiten)).toEqual([]);
    },
  );

  it("weigert een fasemap of projectmap die via een symbolische koppeling naar buiten wijst", () => {
    symlinkSync(buiten, path.join(wortel, "p3"));
    expect(() => afdrukMap(wortel, "p3", "mobiel-390")).toThrow(/geen gewone map/);
    mkdirSync(path.join(wortel, "p2"));
    symlinkSync(buiten, path.join(wortel, "p2", "mobiel-390"));
    expect(() => afdrukMap(wortel, "p2", "mobiel-390")).toThrow(/geen gewone map/);
    expect(readdirSync(buiten)).toEqual([]);
  });

  it("weigert een gewoon bestand op de plek van de fasemap", () => {
    writeFileSync(path.join(wortel, "p4"), "");
    expect(() => afdrukMap(wortel, "p4", "opzet")).toThrow(/geen gewone map/);
  });

  it("afdrukBestand weigert een symbolische koppeling en een naam met een pad", () => {
    const map = afdrukMap(wortel, "p3", "opzet");
    expect(afdrukBestand(map, "home-licht")).toBe(path.join(map, "home-licht.jpg"));
    symlinkSync(path.join(buiten, "x.jpg"), path.join(map, "home-donker.jpg"));
    expect(() => afdrukBestand(map, "home-donker")).toThrow(/symbolische koppeling/);
    expect(() => afdrukBestand(map, "../home")).toThrow(/ongeldige afdruknaam/);
  });
});
