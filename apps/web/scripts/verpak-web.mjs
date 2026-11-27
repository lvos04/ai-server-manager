// Alleen in de bouwfase. Kopieer uitsluitend de gecontroleerde /out naar de uiteindelijke image.
import { readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";
import ts from "typescript";
import { manifesten, runtimeMap, sjabloon } from "../server/webmanifesten.mjs";

function* bestanden(map, overslaan = []) {
  for (const item of readdirSync(map, { withFileTypes: true })) {
    const bestand = path.join(map, item.name);
    if (item.isDirectory() && !overslaan.includes(item.name)) yield* bestanden(bestand, overslaan);
    else if (item.isFile()) yield bestand;
  }
}

function controleerWebbron(map) {
  for (const bestand of bestanden(map, ["node_modules", ".next", "e2e", "review", "tests", "test-results"])) {
    if (!/\.[cm]?[jt]sx?$/.test(bestand) || path.resolve(bestand) === fileURLToPath(import.meta.url)) continue;
    const bron = ts.createSourceFile(bestand, readFileSync(bestand, "utf8"), ts.ScriptTarget.Latest);
    function bezoek(knoop) {
      if ((ts.isIdentifier(knoop) || ts.isStringLiteralLike(knoop)) && knoop.text === "draftMode") {
        throw new Error("Hub-web gebruikt draftMode");
      }
      if (ts.isExpressionStatement(knoop) && knoop.expression.text === "use server") {
        throw new Error("Hub-web gebruikt een Server Action");
      }
      ts.forEachChild(knoop, bezoek);
    }
    bezoek(bron);
  }
}

export function verpakWeb(pakket, bron, runtime = runtimeMap) {
  controleerWebbron(bron);
  const nextMap = path.join(pakket, ".next");
  const lees = (naam) => readFileSync(path.join(nextMap, naam), "utf8");
  const [routes, preview, acties, js] = manifesten.map(lees);
  const prerender = JSON.parse(routes);
  const actieManifest = JSON.parse(acties);
  if (Object.keys(actieManifest.node).length || Object.keys(actieManifest.edge).length) {
    throw new Error("Het productie-manifest bevat een Server Action");
  }
  const prefix = "self.__RSC_SERVER_MANIFEST=";
  if (!js.startsWith(prefix) || !isDeepStrictEqual(JSON.parse(JSON.parse(js.slice(prefix.length))), actieManifest)
      || !isDeepStrictEqual(prerender.preview, JSON.parse(preview))) {
    throw new Error("Onverwachte indeling van de Next.js-manifesten");
  }
  const waarden = [prerender.preview.previewModeId, prerender.preview.previewModeSigningKey,
    prerender.preview.previewModeEncryptionKey, actieManifest.encryptionKey];
  if (waarden.some(waarde => typeof waarde !== "string" || waarde.length < 16)) {
    throw new Error("Onverwachte indeling van de Next.js-buildwaarden");
  }
  delete prerender.preview;
  writeFileSync(path.join(nextMap, sjabloon), JSON.stringify(prerender));
  for (const naam of manifesten) {
    const bestand = path.join(nextMap, naam);
    rmSync(bestand);
    symlinkSync(path.join(runtime, path.basename(naam)), bestand);
  }
  for (const bestand of bestanden(pakket)) {
    const inhoud = readFileSync(bestand);
    if (waarden.some(waarde => inhoud.includes(waarde))) throw new Error("Een buildwaarde staat nog in het webpakket");
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  verpakWeb(process.argv[2], process.cwd());
}
