// Samenvatting van de Peil-review (review/uit/metingen-*.json) per scherm, over alle breedtes en thema's.
// Gebruik: node review/samenvat.mjs [--json uit.json] [--streng]   → tekst op stdout; met --json ook een compacte JSON;
// met --streng exit 1 bij harde bevindingen of meetfouten (voor CI en `make web-review`).
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const dir = path.join(import.meta.dirname, "uit");
const runs = readdirSync(dir)
  .filter((f) => /^metingen-.*\.json$/.test(f))
  .flatMap((f) => JSON.parse(readFileSync(path.join(dir, f), "utf8")));

// Peil-woordenlijst (ONTWERPTAAL §11): woorden die niet (meer) mogen in zichtbare tekst. Technische waarden in
// code/mono vallen buiten de controle. Elke treffer wordt handmatig beoordeeld (sommige zijn citaat of eigennaam).
const VERBODEN = [
  [/\bIn orde\b/i, "In orde → Gezond"],
  [/\bActueel\b/, "Actueel (versheid is nooit een badge)"],
  [/\bVerminderd\b|\bVerstoord\b/i, "→ Beperkt"],
  [/^Offline$|\bProbleem\b(?!en)/, "Offline/Probleem als status → Storing"],
  [/\bLaden…?$/, "Laden… als status → Onbekend + reden"],
  [/^(Klaar|Gelukt!?|OK|Ok|Doorgaan)$/, "knoppen/uitkomst: werkwoord + object; 'Uitgevoerd en gecontroleerd'"],
  [/Weet je het zeker/i, "geen 'Weet je het zeker?'"],
  [/\bsnooze|\bsnoozen\b/i, "→ uitstellen / uitgesteld tot"],
  [/\bsafe mode\b/i, "→ veilige modus"],
  [/\bblast radius\b/i, "→ reikwijdte"],
  [/\brunbooks?\b/i, "→ stappenplan"],
  [/\bhealth ?checks?\b/i, "→ gezondheidscontrole"],
  [/\ballowlist\b/i, "→ lijst met toegestane acties"],
  [/\bfingerprint\b/i, "→ vingerafdruk"],
  [/Automatisch veilig/i, "→ R1 · Omkeerbaar"],
  [/Ctrl\s*\+?\s*C\b/i, "geen Ctrl+C (werkt niet op Android)"],
  [/!(\s|$)/, "geen uitroeptekens"],
  [/\b(Loading|Error|Submit|Cancel|Save|Settings|Healthy|Degraded|Unknown|Stale)\b/, "Engelse UI-tekst"],
  [/\b\d{1,3}\s?%\s*(zeker|zekerheid)/i, "zekerheid nooit als percentage"],
  [/\bAI Server Manager\b/, "productnaam is TrueNAS Home Platform"],
];

const by = new Map();
for (const r of runs) {
  if (!by.has(r.scherm)) by.set(r.scherm, []);
  by.get(r.scherm).push(r);
}
const uniek = (a) => [...new Set(a)];
const totaal = { schermen: 0, metingen: 0, harde: 0, axe: 0 };
const compact = {};
const out = [];
for (const [scherm, R0] of [...by.entries()].sort()) {
  const R = R0.filter((r) => !r.fout && !r.overgeslagen);
  const fouten = R0.filter((r) => r.fout).map((r) => `${r.breedte}: ${r.fout}`);
  const over = R0.filter((r) => r.overgeslagen).map((r) => r.overgeslagen);
  totaal.schermen++;
  totaal.metingen += R.length;
  const harde = [];
  const zacht = [];
  const ax = uniek(R.flatMap((r) => (r.axe ?? []).map((v) => `${v.id} (${v.impact}) @${r.breedte}/${r.thema}: ${v.voorbeeld[0]}`)));
  if (ax.length) harde.push(...ax.map((a) => `axe ${a}`));
  totaal.axe += R.reduce((n, r) => n + (r.axe ?? []).length, 0);
  const ol = R.filter((r) => r.overloop > 0).map((r) => `${r.breedte}/${r.thema} ${r.overloop}px [${(r.breed ?? []).slice(0, 2).join("; ")}]`);
  if (ol.length) harde.push(`overloop: ${ol.join(" | ")}`);
  const tf = uniek(R.flatMap((r) => (r.tekstFout ?? []).filter((x) => !x.dis).map((x) => `${r.thema}: "${x.t}" ${Math.min(x.r, x.rAlt)}:1 (${x.fg} op ${x.bg}, eis ${x.eis})`)));
  if (tf.length) harde.push(`tekstcontrast: ${tf.slice(0, 6).join(" | ")}`);
  const tfDis = uniek(R.flatMap((r) => (r.tekstFout ?? []).filter((x) => x.dis).map((x) => `${r.thema}: "${x.t}" ${x.r}:1`)));
  if (tfDis.length) zacht.push(`uitgeschakeld < 4,5:1 (WCAG-uitzondering): ${tfDis.slice(0, 3).join(" | ")}`);
  const U = R.filter((r) => r.uitgeklapt);
  const tfU = uniek(U.flatMap((r) => r.uitgeklapt.tekstFout.filter((x) => !x.dis).map((x) => `${r.thema}: "${x.t}" ${Math.min(x.r, x.rAlt)}:1 (${x.fg} op ${x.bg})`)));
  if (tfU.length) harde.push(`tekstcontrast (uitgeklapt): ${tfU.slice(0, 6).join(" | ")}`);
  const olU = U.filter((r) => r.uitgeklapt.overloop > 0).map((r) => `${r.breedte}/${r.thema} ${r.uitgeklapt.overloop}px`);
  if (olU.length) harde.push(`overloop (uitgeklapt): ${uniek(olU).join(" | ")}`);
  const doelU = uniek(U.flatMap((r) => r.uitgeklapt.doelen.filter((d) => !d.inline).map((d) => `${r.breedte}: ${d.w}×${d.h} "${d.t}" ${d.el}`)));
  if (doelU.length) harde.push(`doel < 44 px (uitgeklapt): ${doelU.slice(0, 6).join(" | ")}`);
  const kleinU = uniek(U.flatMap((r) => (r.uitgeklapt.kleinFont ?? []).map((k) => `${k.fs}px "${k.t}"`)));
  if (kleinU.length) harde.push(`tekst < 14 px (uitgeklapt): ${kleinU.slice(0, 5).join(" | ")}`);
  const afkU = uniek(U.flatMap((r) => (r.uitgeklapt.afgekapt ?? []).map((a) => `${r.breedte}: "${a.t.slice(0, 40)}"`)));
  if (afkU.length) harde.push(`afgekapt (uitgeklapt): ${afkU.join(" | ")}`);
  const klein = uniek(R.flatMap((r) => (r.kleinFont ?? []).map((k) => `${k.fs}px "${k.t}" ${k.el}`)));
  if (klein.length) harde.push(`tekst < 14 px: ${klein.slice(0, 5).join(" | ")}`);
  const doel = uniek(R.flatMap((r) => (r.doelen ?? []).filter((d) => !d.inline).map((d) => `${r.breedte}: ${d.w}×${d.h} "${d.t}" ${d.el}`)));
  if (doel.length) harde.push(`doel < 44 px: ${doel.slice(0, 6).join(" | ")}`);
  const veld = uniek(R.flatMap((r) => (r.velden ?? []).filter((v) => Math.max(v.rand, v.vlak) < 3).map((v) => `${r.thema} ${v.el} ${v.rand}:1`)));
  if (veld.length) harde.push(`veldrand < 3:1: ${veld.join(" | ")}`);
  const st = uniek(R.flatMap((r) => (r.stippel ?? []).filter((s) => s.buiten < 3 && s.bw > 0).map((s) => `${r.thema} ${s.buiten}:1 "${s.t.slice(0, 30)}"`)));
  if (st.length) harde.push(`stippelrand < 3:1: ${st.join(" | ")}`);
  const afk = uniek(R.flatMap((r) => (r.afgekapt ?? []).map((a) => `${r.breedte}: "${a.t.slice(0, 40)}"`)));
  if (afk.length) harde.push(`afgekapt met ellips: ${afk.join(" | ")}`);
  const ov = uniek(R.flatMap((r) => (r.overlap ?? []).map((o) => `${r.breedte}: ${o}`)));
  if (ov.length) harde.push(`tekstoverlap: ${ov.slice(0, 4).join(" | ")}`);
  const knip = uniek(R.flatMap((r) => (r.knip ?? []).map((a) => `${r.breedte}: ${a.el} "${a.t.slice(0, 30)}" ${a.sw}>${a.cw}`)));
  if (knip.length) zacht.push(`inhoud breder dan kader (overflow hidden): ${knip.slice(0, 4).join(" | ")}`);
  const fr = R.filter((r) => r.focus);
  const zonder = uniek(fr.flatMap((r) => r.focus.zonderRing));
  const zwak = uniek(fr.flatMap((r) => r.focus.zwak));
  const bedekt = uniek(fr.flatMap((r) => r.focus.bedekt.map((b) => `${r.breedte}/${r.thema} ${b}`)));
  const deels = uniek(fr.flatMap((r) => (r.focus.deelsBedekt ?? []).map((b) => `${r.breedte} ${b}`)));
  const geknipt = uniek(fr.flatMap((r) => (r.focus.geknipt ?? []).map((b) => `${r.breedte} ${b}`)));
  if (zonder.length) harde.push(`focus zonder ring: ${zonder.join(" | ")}`);
  if (zwak.length) harde.push(`focusring < 3:1: ${zwak.join(" | ")}`);
  if (bedekt.length) harde.push(`focus bedekt: ${bedekt.join(" | ")}`);
  if (deels.length) zacht.push(`focus deels bedekt: ${deels.slice(0, 4).join(" | ")}`);
  if (geknipt.length) zacht.push(`focusring afgesneden door scrollkader: ${geknipt.slice(0, 4).join(" | ")}`);
  const s0 = R.map((r) => r.structuur).filter(Boolean);
  const h1 = uniek(s0.map((s) => s.h1));
  if (h1.some((n) => n !== 1) && !scherm.startsWith("executor-statuspagina")) harde.push(`aantal h1: ${h1.join(",")}`);
  const sprong = uniek(s0.flatMap((s) => s.sprong));
  if (sprong.length) harde.push(`kopsprong: ${sprong.join(",")}`);
  const dub = uniek(s0.flatMap((s) => s.dubbel));
  if (dub.length) harde.push(`dubbele id: ${dub.join(",")}`);
  const kap = uniek(s0.flatMap((s) => s.kapot));
  if (kap.length) harde.push(`kapotte aria-verwijzing: ${kap.join(",")}`);
  // Peil-semantiek
  const groen = uniek(R.flatMap((r) => (r.semantiek?.groen ?? []).map((g) => g.t)));
  const groenFout = groen.filter((t) => /onbekend|verouderd|laatst bekend|niet gemeten|geen meting|niet beschikbaar/i.test(t));
  const groenAnders = groen.filter((t) => !/gezond/i.test(t) && !groenFout.includes(t));
  if (groenFout.length) harde.push(`onbekend/verouderd in groen: ${groenFout.join(" | ")}`);
  if (groenAnders.length) zacht.push(`groen zonder 'Gezond' (handmatig beoordelen): ${groenAnders.slice(0, 5).join(" | ")}`);
  const kleur = uniek(R.flatMap((r) => (r.semantiek?.kleurAlleen ?? []).map((k) => `${k.soort} ${k.el}`)));
  if (kleur.length) harde.push(`status alleen kleur: ${kleur.join(" | ")}`);
  const zi = uniek(R.flatMap((r) => (r.semantiek?.zonderIcoon ?? []).map((k) => `${k.soort} "${k.t}"`)));
  if (zi.length) zacht.push(`statusvorm zonder icoon: ${zi.slice(0, 4).join(" | ")}`);
  const beweging = uniek(R.flatMap((r) => r.beweging ?? []));
  if (beweging.length) zacht.push(`beweging bij reduced motion: ${beweging.slice(0, 3).join(" | ")}`);
  // Microcopy
  const tekst = uniek(R.flatMap((r) => r.woorden?.teksten ?? []));
  const knoppen = uniek(R.flatMap((r) => r.woorden?.knoppen ?? []));
  const woord = [];
  for (const t of [...tekst, ...knoppen]) for (const [re, uitleg] of VERBODEN) if (re.test(t)) woord.push(`"${t.slice(0, 70)}" (${uitleg})`);
  if (woord.length) zacht.push(`woordenlijst: ${uniek(woord).slice(0, 8).join(" | ")}`);
  const titels = uniek(R.map((r) => r.woorden?.titel).filter(Boolean));
  const tekstMin = Math.min(...R.map((r) => r.tekstMin ?? 99));
  const onder7 = Math.max(0, ...R.map((r) => r.tekstOnder7 ?? 0));
  const ringMin = Math.min(99, ...fr.map((r) => r.focus.ringMin));
  totaal.harde += harde.length;
  compact[scherm] = { metingen: R.length, harde, zacht, fouten, overgeslagen: over, tekstMin, onder7, ringMin, titels, h1: uniek(s0.flatMap((s) => s.h1Tekst ?? [])) };
  out.push(`\n## ${scherm}  (${R.length} metingen; tekst min ${tekstMin}:1, max ${onder7} tekstparen < 7:1; focusring min ${ringMin === 99 ? "-" : ringMin + ":1"}; titel ${titels.join(" / ") || "-"})`);
  for (const f of fouten) out.push(`  FOUT ${f}`);
  for (const o of uniek(over)) out.push(`  overgeslagen: ${o}`);
  for (const h of harde) out.push(`  ✗ ${h}`);
  for (const z of zacht) out.push(`  · ${z}`);
  if (!harde.length && !zacht.length && !fouten.length) out.push("  geen bevindingen");
}
out.unshift(`Peil-review: ${totaal.schermen} schermen/toestanden, ${totaal.metingen} metingen (breedte × thema), harde bevindingen ${totaal.harde}, axe-overtredingen ${totaal.axe}`);
console.log(out.join("\n"));
const i = process.argv.indexOf("--json");
if (i > 0) writeFileSync(process.argv[i + 1], JSON.stringify({ totaal, schermen: compact }, null, 1));
const fouten = Object.values(compact).reduce((n, c) => n + c.fouten.length, 0);
if (process.argv.includes("--streng") && (totaal.harde > 0 || fouten > 0 || totaal.metingen === 0)) {
  console.error(`\nPeil-review NIET in orde: ${totaal.harde} harde bevindingen, ${fouten} meetfouten, ${totaal.metingen} metingen.`);
  process.exit(1);
}
