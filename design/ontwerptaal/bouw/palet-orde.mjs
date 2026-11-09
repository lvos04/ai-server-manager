// Bewijs voor de volgorde van het grafiekpalet: rekent alle 24 volgordes (blauw eerst) van de 5 toegestane tinten door
// met de dataviz-validator in licht en donker, en meet de ΔE tot de status-/goedkeuringskleuren.
// Gebruik: node bouw/palet-orde.mjs   (DATAVIZ_VALIDATOR=<pad> als de skill elders staat)
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { KLEUREN } from './tokens.mjs';
const VAL = process.env.DATAVIZ_VALIDATOR || '';
const { validate } = await import(pathToFileURL(VAL).href);
const T = { licht: Object.fromEntries(KLEUREN.map((r) => [r[0], r[1]])), donker: Object.fromEntries(KLEUREN.map((r) => [r[0], r[2]])) };
const tint = { blauw: 'chart-1', oranje: 'chart-2', aqua: 'chart-3', geel: 'chart-4', magenta: 'chart-5' };
const perm = (a) => (a.length <= 1 ? [a] : a.flatMap((x, k) => perm([...a.slice(0, k), ...a.slice(k + 1)]).map((p) => [x, ...p])));
const num = (v, n) => +(v.report.find((r) => r[0] === n)[2].match(/ΔE ([\d.]+)/) || [0, 99])[1];
const rijen = [];
for (const p of perm(Object.keys(tint)).filter((p) => p[0] === 'blauw')) {
  const r = { volgorde: p.join(' · ') };
  for (const [th, mode] of [['licht', 'light'], ['donker', 'dark']]) {
    const pal = p.map((k) => T[th][tint[k]]);
    const v = validate(pal, { mode, surface: T[th].card }), a3 = validate(pal.slice(0, 3), { mode, surface: T[th].card, pairs: 'all' });
    Object.assign(r, { [`${th}_ok`]: v.ok && a3.ok, [`${th}_cvd`]: num(v, 'CVD separation'), [`${th}_normaal`]: num(v, 'Normal-vision floor'), [`${th}_eerste3_cvd`]: num(a3, 'CVD separation') });
  }
  rijen.push(r);
}
rijen.sort((a, b) => (b.licht_ok && b.donker_ok) - (a.licht_ok && a.donker_ok) || Math.min(b.licht_cvd, b.donker_cvd) - Math.min(a.licht_cvd, a.donker_cvd));
console.table(rijen);
