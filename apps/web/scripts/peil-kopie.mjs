// Versie-gepinde kopie van de Peil-tokens (O-14): design/ontwerptaal/ontwerptaal.css → src/app/peil/ontwerptaal.css
// met een herkomstkop (versie + sha256 van de bron). Gebruik: node scripts/peil-kopie.mjs [--check]
// De unittest tests/unit/peil-tokens.test.ts faalt bij drift; de bron van waarheid is design/ontwerptaal/ in deze repo.
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const here = path.dirname(new URL(import.meta.url).pathname);
const bron = path.resolve(here, "..", "..", "..", "design", "ontwerptaal", "ontwerptaal.css");
const doel = path.resolve(here, "..", "src", "app", "peil", "ontwerptaal.css");

export function kopie(tekst) {
  const sha = createHash("sha256").update(tekst).digest("hex");
  const versie = /Peil (\d+\.\d+\.\d+)/.exec(tekst)?.[1] ?? "onbekend";
  const kop =
    `/* Herkomst: ai-server-manager/design/ontwerptaal/ontwerptaal.css · Peil ${versie} · sha256:${sha}\n` +
    `   Kopie (O-14): niet met de hand wijzigen; opnieuw maken met node scripts/peil-kopie.mjs. */\n`;
  return kop + tekst;
}

const tekst = readFileSync(bron, "utf8");
const verwacht = kopie(tekst);
if (process.argv.includes("--check")) {
  const huidig = readFileSync(doel, "utf8");
  if (huidig !== verwacht) {
    console.error("Peil-kopie wijkt af van design/ontwerptaal/ontwerptaal.css; draai node scripts/peil-kopie.mjs");
    process.exit(1);
  }
  console.log("Peil-kopie actueel.");
} else {
  writeFileSync(doel, verwacht);
  console.log(`Geschreven: ${path.relative(process.cwd(), doel)}`);
}
