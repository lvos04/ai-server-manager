// Brede contrastmatrix (toegevoegd bij de ontwerpreview, Peil 1.1.0). Leest de GEGENEREERDE ontwerptaal.css (wat bouwers importeren),
// lost var()-aliassen op en rekent een eigen, ruimere parenmatrix door met wcag-contrast + culori.
// Gebruik: node bouw/contrast-breed.mjs  (na contrast.mjs; schrijft "brede_matrix" in contrast.json en stopt bij een harde fout)
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { hex: wcag } = require('wcag-contrast');
const culori = require('culori');
const D = new URL('../', import.meta.url).pathname;
const css = fs.readFileSync(D + '/ontwerptaal.css', 'utf8');
function blok(sel) {
  const i = css.indexOf(sel); const s = css.indexOf('{', i); const e = css.indexOf('\n}', s);
  const o = {}; for (const m of css.slice(s + 1, e).matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) o[m[1]] = m[2].trim(); return o;
}
const licht = blok(':root {'), donkerRaw = blok('.dark,\n[data-theme="dark"] {');
const donker = { ...licht, ...donkerRaw };
const res = (t, n, d = 0) => { let v = t[n]; if (v === undefined) throw new Error('onbekend token ' + n); const m = v.match(/^var\(--([a-z0-9-]+)\)$/); return m ? (d > 10 ? null : res(t, m[1], d + 1)) : v; };
const hex = (t, n) => { const v = res(t, n); if (!/^#[0-9a-f]{6}$/i.test(v)) throw new Error(n + ' geen hex: ' + v); return v.toLowerCase(); };
// consistentie: tokens.json moet dezelfde waarden hebben
const tj = JSON.parse(fs.readFileSync(D + '/tokens.json', 'utf8'));
const tjv = {}; (function walk(o, p) { for (const [k, v] of Object.entries(o)) { if (v && typeof v === 'object' && '$value' in v) { tjv[k] = { l: v.$value, d: v.$extensions?.['nl.peil']?.modes?.donker ?? v.$value }; } else if (v && typeof v === 'object' && !k.startsWith('$')) walk(v, p + '.' + k); } })(tj, '');
const drift = [];
for (const [k, v] of Object.entries(tjv)) { if (typeof v.l !== 'string' || !v.l.startsWith('#')) continue; if (licht[k] && licht[k].startsWith('#') && licht[k].toLowerCase() !== v.l.toLowerCase()) drift.push(`licht ${k}: css ${licht[k]} json ${v.l}`); if (donker[k] && donker[k].startsWith('#') && typeof v.d === 'string' && v.d.startsWith('#') && donker[k].toLowerCase() !== v.d.toLowerCase()) drift.push(`donker ${k}: css ${donker[k]} json ${v.d}`); }

const NEUTRAAL = ['background', 'card', 'popover', 'muted', 'secondary', 'accent', 'sidebar', 'unknown-bg', 'stale-bg', 'risk-0-bg', 'risk-1-bg', 'gate-bg', 'validation-bg', 'diff-old-bg'];
const TINT = ['healthy-bg', 'degraded-bg', 'down-bg', 'info-bg', 'approval-bg', 'risk-2-bg', 'risk-3-bg', 'diff-new-bg', 'domain-heat-bg', 'domain-cool-bg', 'domain-boiler-bg', 'domain-light-on-bg'];
const BASIS = ['background', 'card', 'popover', 'muted'];
const P = []; // [voorgrond, achtergrond, soort, eis, toelichting]
const add = (f, b, soort, eis, why) => P.push([f, b, soort, eis, why]);
for (const b of [...NEUTRAAL, ...TINT]) { add('foreground', b, 'tekst', 4.5, 'tekstniveau 1'); add('muted-foreground', b, 'tekst', 4.5, 'tekstniveau 2 / meta'); }
for (const b of NEUTRAAL) { add('link', b, 'tekst', 4.5, 'link'); add('primary', b, 'tekst', 4.5, 'primary als tekst (ghost-knop, actief nav-item)'); add('chart-label', b, 'tekst', 4.5, 'grafieklabel'); add('disabled-foreground', b, 'info', 0, 'uitgeschakeld (WCAG-vrijgesteld)'); }
for (const s of ['healthy', 'degraded', 'down', 'unknown', 'info', 'approval']) {
  for (const b of [...BASIS, s + '-bg']) add(s + '-ink', b, 'tekst', 4.5, s + ' tekst');
  for (const b of [...BASIS, s + '-bg']) add(s, b, 'ui', 3, s + ' icoon/rand');
  for (const b of [...BASIS, s + '-bg']) add(s, b, 'tekst-als-icoontoken', 4.5, s + ' (token ook als tekst gebruikt via aliaslaag --mg-' + ({ healthy: 'success', degraded: 'warning', down: 'danger', unknown: '', info: 'info', approval: '' }[s] || '?') + ')');
}
for (const b of ['stale-bg', 'stale-hatch', ...BASIS]) add('stale-ink', b, 'tekst', 4.5, 'laatst bekende waarde (gedempt)');
for (const b of ['stale-bg', ...BASIS]) add('stale', b, 'ui', 3, 'stippelrand verouderd');
for (let n = 0; n <= 3; n++) { add(`risk-${n}-ink`, `risk-${n}-bg`, 'tekst', 4.5, `R${n} woorddeel`); add(`risk-${n}-on-solid`, `risk-${n}-solid`, 'tekst', 4.5, `R${n} codeblok`); for (const b of ['card', 'background', 'popover', `risk-${n}-bg`]) add(`risk-${n}`, b, 'ui', 3, `R${n} rand/treden`); }
for (const [a, b] of [['gate-ink', 'gate-bg'], ['validation-ink', 'validation-bg'], ['diff-old-ink', 'diff-old-bg'], ['diff-new-ink', 'diff-new-bg'], ['primary-foreground', 'primary'], ['primary-foreground', 'primary-hover'], ['destructive-foreground', 'destructive'], ['destructive-foreground', 'destructive-hover'], ['domain-heat-ink', 'domain-heat-bg'], ['domain-cool-ink', 'domain-cool-bg'], ['domain-boiler-ink', 'domain-boiler-bg'], ['domain-light-on-ink', 'domain-light-on-bg'], ['domain-heat-ink', 'domain-heat-soft'], ['domain-cool-ink', 'domain-cool-soft'], ['destructive', 'card'], ['destructive', 'background'], ['destructive', 'down-bg']]) add(a, b, 'tekst', 4.5, 'tekst op eigen vlak');
for (const s of ['gate', 'validation']) for (const b of [...BASIS, s + '-bg']) add(s, b, 'ui', 3, s + ' rand/icoon');
for (const t of ['border-strong', 'input', 'ring']) for (const b of [...NEUTRAAL, ...TINT]) add(t, b, 'ui', 3, t);
add('ring', 'ring-halo', 'ui', 9, 'C40 tweekleurige ring: onderling >= 9:1');
add('ring-halo', 'primary', 'ui', 3, 'halo rond primaire knop');
for (const c of ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'chart-limit']) add(c, 'card', 'ui', 3, 'grafiekmarkering op card');
for (const c of ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5']) add(c, 'popover', 'ui', 3, 'grafiekmarkering in tooltip/popover');
add('chart-other', 'card', 'info', 0, 'Overig: altijd arcering + label');
add('chart-1', 'chart-meter-track', 'ui', 3, 'meter vulling/spoor');
add('degraded', 'degraded-bg', 'ui', 3, 'meter boven drempel');
add('chart-axis', 'card', 'info', 0, 'as (haarlijn, labels dragen de info)');
for (const c of ['domain-heat', 'domain-cool', 'domain-boiler', 'domain-light-on']) { add(c, 'card', 'ui', 3, 'domeinicoon op card'); add(c, c + '-bg', 'info', 0, 'domeinkleur op eigen vlak: NIET gebruiken — icoon op het vlak krijgt de -ink-kleur (ONTWERPTAAL §4.1 regel 11)'); add(c, 'card', 'tekst-als-icoontoken', 4.5, 'domeinkleur als TEKST (niet toegestaan)'); }

const rows = { licht: [], donker: [] };
for (const [naam, t] of [['licht', licht], ['donker', donker]]) for (const [f, b, soort, eis, why] of P) {
  const fh = hex(t, f), bh = hex(t, b); const r = +wcag(fh, bh).toFixed(2);
  rows[naam].push({ voorgrond: f, achtergrond: b, kleuren: `${fh} op ${bh}`, ratio: r, soort, eis, oordeel: eis === 0 ? 'info' : r >= eis ? 'voldoet' : 'VOLDOET NIET', gebruik: why });
}
// ΔE status ↔ grafiek
const ok = culori.converter('oklab');
const dE = (a, b) => { const x = ok(a), y = ok(b); return Math.hypot(x.l - y.l, x.a - y.a, x.b - y.b) * 100; };
const STAT = ['healthy', 'degraded', 'down', 'unknown', 'info', 'approval', 'risk-1', 'risk-3', 'gate'];
const GRAF = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'domain-heat', 'domain-cool', 'domain-boiler', 'domain-light-on'];
const sep = {};
for (const [naam, t] of [['licht', licht], ['donker', donker]]) { let min = [99]; for (const s of STAT) for (const g of GRAF) { const d = dE(hex(t, s), hex(t, g)); if (d < min[0]) min = [d, s, g]; } sep[naam] = { min_dE: +min[0].toFixed(1), paar: min.slice(1) }; }
// hue van chart-3 t.o.v. healthy
const lch = culori.converter('oklch');
const hue = {}; for (const [naam, t] of [['licht', licht], ['donker', donker]]) hue[naam] = { healthy: Math.round(lch(hex(t, 'healthy')).h), 'chart-3': Math.round(lch(hex(t, 'chart-3')).h), 'domain-boiler-bg': Math.round(lch(hex(t, 'domain-boiler-bg')).h), 'healthy-bg': Math.round(lch(hex(t, 'healthy-bg')).h), 'dE_boilerbg_healthybg': +dE(hex(t, 'domain-boiler-bg'), hex(t, 'healthy-bg')).toFixed(1) };

const fails = Object.fromEntries(Object.entries(rows).map(([k, v]) => [k, v.filter((r) => r.oordeel === 'VOLDOET NIET' && r.soort !== 'tekst-als-icoontoken')]));
const icoonAlsTekst = Object.fromEntries(Object.entries(rows).map(([k, v]) => [k, v.filter((r) => r.soort === 'tekst-als-icoontoken' && r.oordeel === 'VOLDOET NIET').map((r) => `${r.voorgrond} op ${r.achtergrond} ${r.ratio}`)]));
const minTekst = Object.fromEntries(Object.entries(rows).map(([k, v]) => { const t = v.filter((r) => r.soort === 'tekst').sort((a, b) => a.ratio - b.ratio); return [k, t.slice(0, 6).map((r) => `${r.voorgrond} op ${r.achtergrond} ${r.ratio}`)]; }));
// vergelijk met contrast.json
const cj = JSON.parse(fs.readFileSync(D + '/contrast.json', 'utf8'));
const verschil = [];
for (const th of ['licht', 'donker']) for (const r of cj.thema[th]) { const t = th === 'licht' ? licht : donker; try { const rr = +wcag(hex(t, r.voorgrond), hex(t, r.achtergrond)).toFixed(2); if (Math.abs(rr - r.ratio) > 0.011) verschil.push(`${th} ${r.voorgrond}/${r.achtergrond}: json ${r.ratio} herberekend ${rr}`); } catch (e) { verschil.push(`${th} ${r.voorgrond}/${r.achtergrond}: ${e.message}`); } }
const out = { paren_per_thema: P.length, tokens_json_drift: drift, contrast_json_afwijkingen: verschil, harde_fouten: fails, icoontoken_als_tekst_onder_4_5: icoonAlsTekst, laagste_tekst: minTekst, scheiding: sep, tint: hue, rows };
const nFout = Object.values(fails).flat().length + drift.length + verschil.length;
cj.brede_matrix = { methode: 'gegenereerde ontwerptaal.css (var() opgelost) · wcag-contrast · ΔE OKLab×100 (culori)', paren_per_thema: P.length, harde_fouten: nFout, tokens_json_drift: drift, contrast_json_afwijkingen: verschil, foutlijst: fails, icoontoken_als_tekst_onder_4_5: icoonAlsTekst, laagste_tekst: minTekst, scheiding: sep, tint_boiler_vs_gezond: hue, paren: rows };
fs.writeFileSync(D + '/contrast.json', JSON.stringify(cj, null, 2) + '\n');
console.log('brede matrix:', P.length, 'paren per thema · harde fouten', nFout, '· laagste tekst', minTekst.licht[0], '/', minTekst.donker[0]);
if (nFout) { console.error(JSON.stringify({ fails, drift, verschil }, null, 1)); process.exit(1); }
