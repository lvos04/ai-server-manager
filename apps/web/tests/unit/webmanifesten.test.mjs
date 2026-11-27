import { randomBytes } from "node:crypto";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, expect, test } from "vitest";
import { verpakWeb } from "../../scripts/verpak-web.mjs";
import { schrijfWebmanifesten } from "../../server/webmanifesten.mjs";

let werk, pakket, bron, runtime;
const lees = (naam) => readFileSync(path.join(pakket, ".next", naam), "utf8");
const schrijf = (naam, tekst) => writeFileSync(path.join(pakket, ".next", naam), tekst);

beforeEach(() => {
  werk = mkdtempSync(path.join(tmpdir(), "hub-web-"));
  pakket = path.join(werk, "pakket");
  bron = path.join(werk, "src");
  runtime = path.join(werk, "runtime");
  mkdirSync(path.join(pakket, ".next/server"), { recursive: true });
  mkdirSync(bron);
  mkdirSync(runtime, { mode: 0o700 });
  const preview = Object.fromEntries(["previewModeId", "previewModeSigningKey", "previewModeEncryptionKey"]
    .map(veld => [veld, randomBytes(32).toString("hex")]));
  const acties = JSON.stringify({ node: {}, edge: {}, encryptionKey: randomBytes(32).toString("base64") });
  schrijf("server/preview-props.json", JSON.stringify(preview));
  schrijf("prerender-manifest.json", JSON.stringify({ version: 4, routes: { "/": {} }, preview }));
  schrijf("server/server-reference-manifest.json", acties);
  schrijf("server/server-reference-manifest.js", "self.__RSC_SERVER_MANIFEST=" + JSON.stringify(acties));
});
afterEach(() => rmSync(werk, { recursive: true, force: true }));

test("de actuele webbron gebruikt geen previewmodus of Server Actions", () => {
  const web = fileURLToPath(new URL("../../", import.meta.url));
  verpakWeb(pakket, web, runtime);
});

test("de image bevat geen buildsleutels en iedere installatie krijgt eigen stabiele manifesten", () => {
  const oud = JSON.parse(lees("server/preview-props.json"));
  verpakWeb(pakket, bron, runtime);
  expect(() => lees("prerender-manifest.json")).toThrow();
  const sleutel = randomBytes(32);
  const start = (key) => {
    schrijfWebmanifesten(path.join(pakket, ".next"), runtime, key);
    const manifest = JSON.parse(lees("prerender-manifest.json"));
    expect(manifest.routes).toEqual({ "/": {} });
    expect(JSON.parse(lees("server/preview-props.json"))).toEqual(manifest.preview);
    const acties = JSON.parse(lees("server/server-reference-manifest.json"));
    const js = lees("server/server-reference-manifest.js").split("=")[0];
    expect(js).toBe("self.__RSC_SERVER_MANIFEST");
    expect(JSON.parse(JSON.parse(lees("server/server-reference-manifest.js").slice(js.length + 1)))).toEqual(acties);
    expect(Buffer.from(acties.encryptionKey, "base64")).toHaveLength(32);
    expect(Object.keys(manifest.preview).sort()).toEqual(Object.keys(oud).sort());
    return [...Object.values(manifest.preview), acties.encryptionKey];
  };
  const eerste = start(sleutel);
  expect(new Set(eerste).size).toBe(4);
  expect(start(sleutel)).toEqual(eerste);
  for (const waarde of [...Object.values(oud), ...start(randomBytes(32))]) expect(eerste).not.toContain(waarde);
});

test.each(["node", "edge"])("de build weigert een geregistreerde Server Action voor %s", (soort) => {
  const acties = JSON.parse(lees("server/server-reference-manifest.json"));
  acties[soort].voorbeeld = {};
  schrijf("server/server-reference-manifest.json", JSON.stringify(acties));
  expect(() => verpakWeb(pakket, bron, runtime)).toThrow(/Server Action/);
});

test.each(["import { draftMode as concept } from 'next/headers';", "'use server';"])(
  "de build weigert nieuw gebruik in een webmodule", (code) => {
    writeFileSync(path.join(bron, "module.ts"), code);
    expect(() => verpakWeb(pakket, bron, runtime)).toThrow(/draftMode|Server Action/);
  },
);

test("de build weigert een resterende kopie buiten de bekende manifesten", () => {
  schrijf("extra.js", JSON.parse(lees("server/preview-props.json")).previewModeId);
  expect(() => verpakWeb(pakket, bron, runtime)).toThrow(/buildwaarde/);
});
