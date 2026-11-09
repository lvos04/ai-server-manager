// Vult de gegenereerde delen van ONTWERPTAAL.md (tokentabellen, contrast- en paletsamenvatting) uit tokens.mjs en
// contrast.json, tussen <!-- BEGIN:x --> en <!-- END:x -->. Gebruik: node bouw/docs.mjs
import fs from 'node:fs';
import { KLEUREN, ALIASSEN, MATEN } from './tokens.mjs';
const D = new URL('../', import.meta.url).pathname;
const C = JSON.parse(fs.readFileSync(D + 'contrast.json', 'utf8'));
const GROEP = { oppervlak: 'Oppervlakken', tekst: 'Tekst', rand: 'Randen', interactie: 'Merk en interactie', status: 'Gezondheid en info (gereserveerd)', versheid: 'Versheid', risico: 'Goedkeuring en risico R0–R3', as: 'Gate, validatie en diff', grafiek: 'Grafiek', domein: 'Domeinrollen (bestaande apps)' };
let t = '';
for (const [g, titel] of Object.entries(GROEP)) {
  t += `\n**${titel}**\n\n| Token (CSS / Tailwind) | Licht | Donker | Betekenis en gebruik |\n|---|---|---|---|\n`;
  for (const [k, l, d, gg, w] of KLEUREN) if (gg === g) t += `| \`--${k}\` | \`${l}\` | \`${d}\` | ${w} |\n`;
}
t += `\n**Aliassen** (shadcn-afgeleiden en Gepauzeerd)\n\n| Token | Verwijst naar | Betekenis |\n|---|---|---|\n` + ALIASSEN.map(([k, n, w]) => `| \`--${k}\` | \`--${n}\` | ${w} |`).join('\n') + '\n';
t += `\n**Maten, lagen en beweging** (gelijk in licht en donker)\n\n| Token | Waarde | Betekenis |\n|---|---|---|\n` + MATEN.map(([k, v, , w]) => `| \`--${k}\` | \`${v}\` | ${w} |`).join('\n') + '\n';
const s = C.samenvatting;
let c = `| | Licht | Donker |\n|---|---|---|\n| Gemeten paren | ${s.licht.paren} | ${s.donker.paren} |\n| Tekstparen ≥ 7:1 (AAA) | ${s.licht.aaa_tekstparen} | ${s.donker.aaa_tekstparen} |\n| Laagste AAA-tekstpaar | ${s.licht.laagste_aaa_tekst}:1 | ${s.donker.laagste_aaa_tekst}:1 |\n| UI- en icoonparen gehaald | ${s.licht.ui_en_icoon_paren} | ${s.donker.ui_en_icoon_paren} |\n| Laagste ΔE grafiek/domein ↔ status/risico (eis ≥ 15) | ${s.licht.laagste_dE_grafiek_status} | ${s.donker.laagste_dE_grafiek_status} |\n| Laagste ΔE status onderling (eis ≥ 10) | ${s.licht.laagste_dE_status_onderling} | ${s.donker.laagste_dE_status_onderling} |\n| Harde fouten | ${C.harde_fouten} | |\n`;
if (C.brede_matrix) { const b = C.brede_matrix; c += `| Brede matrix (review 1.1.0): paren per thema, harde fouten | ${b.paren_per_thema} · ${b.harde_fouten} | ${b.paren_per_thema} · ${b.harde_fouten} |\n| Brede matrix: laagste tekstpaar | ${b.laagste_tekst.licht[0]} | ${b.laagste_tekst.donker[0]} |\n`; }
const gp = C.grafiekpalet;
let p = '| Controle (dataviz-validator) | Licht (op `--card`) | Donker (op `--card`) |\n|---|---|---|\n';
const pick = (th, k, n) => (gp[th][k].checks.find((x) => x.includes(n)) || '').replace(/^(\w+) [^:]+: /, '$1 · ');
if (gp && gp.licht) for (const [lab, k, n] of [['Lichtheidsband', 'aangrenzend', 'Lightness'], ['Chromavloer', 'aangrenzend', 'Chroma'], ['CVD-scheiding (aangrenzend)', 'aangrenzend', 'CVD'], ['Normaal zicht (aangrenzend)', 'aangrenzend', 'Normal'], ['Contrast t.o.v. kaart', 'aangrenzend', 'Contrast'], ['Eerste 3, alle paren: CVD', 'eerste3_alle_paren', 'CVD'], ['Ordinale blauwe trap 300–700', 'ordinaal_blauw_300_700', 'Light-end']])
  p += `| ${lab} | ${pick('licht', k, n)} | ${pick('donker', k, n)} |\n`;
const DOC = new URL('../../../docs/platform-v2/ONTWERPTAAL.md', import.meta.url).pathname;
let doc = fs.readFileSync(DOC, 'utf8');
for (const [k, v] of [['tokens', t], ['contrast', c], ...(gp && gp.licht ? [['palet', p]] : [])]) doc = doc.replace(new RegExp(`(<!-- BEGIN:${k} -->)[\\s\\S]*?(<!-- END:${k} -->)`), `$1\n${v}\n$2`);
fs.writeFileSync(DOC, doc);
console.log('ONTWERPTAAL.md bijgewerkt');
