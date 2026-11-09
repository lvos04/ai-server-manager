// Herberekent alle contrastparen, de ΔE-scheiding tussen grafiek/domein en status/risico, en draait de
// dataviz-validator op het grafiekpalet. Schrijft ../contrast.json. Exit 1 bij een harde fout.
// Gebruik: node bouw/contrast.mjs   (DATAVIZ_VALIDATOR=<pad> om de validator elders te vinden)
import { createRequire } from 'node:module';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { KLEUREN, META } from './tokens.mjs';

const require = createRequire(import.meta.url);
const { hex: wcag } = require('wcag-contrast');
const culori = require('culori');
const toLab = culori.converter('oklab');
const toLch = culori.converter('oklch');
const D = new URL('../', import.meta.url).pathname;
const T = { licht: Object.fromEntries(KLEUREN.map((r) => [r[0], r[1]])), donker: Object.fromEntries(KLEUREN.map((r) => [r[0], r[2]])) };
const dE = (a, b) => { const x = toLab(a), y = toLab(b); return 100 * Math.hypot(x.l - y.l, x.a - y.a, x.b - y.b); };

const EIS = { AAA: 7, AA: 4.5, 'icoon': 4.5, ui: 3, info: 0 };
const P = [];
const p = (v, a, eis, wat) => P.push([v, a, eis, wat]);
const VLAKKEN = ['background', 'card', 'popover', 'muted', 'secondary', 'accent', 'sidebar'];
for (const o of VLAKKEN) {
  p('foreground', o, 'AAA', 'tekstniveau 1');
  p('muted-foreground', o, 'AAA', 'tekstniveau 2 (meta, bron, tijd)');
  p('link', o, 'AAA', 'link');
}
for (const o of ['background', 'card', 'muted', 'popover']) {
  p('disabled-foreground', o, 'AA', 'uitgeschakelde tekst (geen WCAG-eis; toch leesbaar gehouden)');
  p('border-strong', o, 'ui', 'informatieve rand / stippelrand onbekend');
  p('input', o, 'ui', 'veldrand');
  p('ring', o, 'ui', 'focusring');
  p('border', o, 'info', 'decoratieve rand (geen eis)');
}
p('ring', 'ring-halo', 'ui', 'tweekleurige focus: ring t.o.v. halo (C40)');
p('primary-foreground', 'primary', 'AAA', 'tekst primaire knop');
p('primary-foreground', 'primary-hover', 'AAA', 'tekst primaire knop (hover)');
p('primary', 'card', 'ui', 'primaire knop t.o.v. kaart');
p('primary', 'background', 'ui', 'primaire knop t.o.v. pagina');
p('primary', 'accent', 'ui', 'actief-markering op hovervlak');
p('destructive-foreground', 'destructive', 'AAA', 'tekst gevaarknop / Kritiek');
p('destructive-foreground', 'destructive-hover', 'AAA', 'tekst gevaarknop (hover)');
p('destructive', 'card', 'ui', 'gevaarknop t.o.v. kaart');
p('background', 'foreground', 'AAA', 'omgekeerde tekst (teller, gevulde stap)');
for (const s of ['healthy', 'degraded', 'down', 'unknown', 'info', 'approval', 'gate', 'validation']) {
  p(`${s}-ink`, `${s}-bg`, 'AAA', `${s}: tekst op vlak`);
  p(`${s}-ink`, 'card', 'AAA', `${s}: tekst op kaart`);
  p(s, `${s}-bg`, 'icoon', `${s}: icoon/rand op eigen vlak`);
  p(s, 'card', 'icoon', `${s}: icoon/rand op kaart`);
  p(s, 'background', 'ui', `${s}: icoon/rand op pagina`);
  p(`${s}-bg`, 'card', 'info', `${s}: vlak t.o.v. kaart (rand draagt de grens)`);
}
p('stale', 'stale-bg', 'icoon', 'verouderd: icoon/stippelrand op vlak');
p('stale', 'card', 'icoon', 'verouderd: icoon/stippelrand op kaart');
p('stale-ink', 'stale-bg', 'AA', 'laatst bekende waarde (bewust gedempt, doel ≈ 6:1)');
p('stale-ink', 'stale-hatch', 'AA', 'laatst bekende waarde op donkerste arceerpixel');
p('foreground', 'stale-bg', 'AAA', 'label "Laatst bekend" in het waardevak');
p('muted-foreground', 'stale-bg', 'AAA', 'meta in het waardevak');
p('foreground', 'stale-hatch', 'AA', 'label op arceerpixel');
for (const r of [0, 1, 2, 3]) {
  p(`risk-${r}-ink`, `risk-${r}-bg`, 'AAA', `R${r}: tekst woorddeel`);
  p(`risk-${r}-on-solid`, `risk-${r}-solid`, 'AAA', `R${r}: tekst codeblok`);
  p(`risk-${r}`, 'card', 'ui', `R${r}: tagrand t.o.v. kaart`);
  p(`risk-${r}`, `risk-${r}-bg`, 'ui', `R${r}: tagrand/glyph op woorddeel`);
  p(`risk-${r}-solid`, 'card', r >= 1 ? 'ui' : 'info', `R${r}: codeblok t.o.v. kaart${r === 0 ? ' (R0: de tagrand draagt de vorm)' : ''}`);
}
p('diff-old-ink', 'diff-old-bg', 'AAA', 'diff: was (doorgestreept)');
p('diff-new-ink', 'diff-new-bg', 'AAA', 'diff: wordt (vet)');
for (let i = 1; i <= 5; i++) p(`chart-${i}`, 'card', 'ui', `grafiekreeks ${i} t.o.v. kaart`);
p('chart-other', 'card', 'ui', 'Overig (met arcering)');
p('chart-label', 'card', 'AAA', 'as-, legenda- en labeltekst');
p('chart-limit', 'card', 'ui', 'grenslijn');
p('chart-1', 'chart-meter-track', 'ui', 'meter: vulling t.o.v. spoor');
p('degraded', 'degraded-bg', 'ui', 'meter boven drempel: vulling t.o.v. spoor');
p('chart-axis', 'card', 'info', 'as (haarlijn)');
p('chart-grid', 'card', 'info', 'raster (haarlijn, recessief)');
p('chart-gap', 'card', 'info', 'arcering gat (draagt label "Geen meting")');
for (const d of ['heat', 'cool', 'boiler', 'light-on']) {
  p(`domain-${d}-ink`, `domain-${d}-bg`, 'AAA', `domein ${d}: tekst op vlak`);
  p(`domain-${d}`, 'card', 'ui', `domein ${d}: icoon/lijn op kaart`);
  p(`domain-${d}`, `domain-${d}-bg`, 'info', `domein ${d}: icoon op eigen vlak (icoon heeft ook tekst ernaast)`);
}
p('domain-integrity', 'card', 'ui', 'integriteitsslot');

const res = { naam: META.naam, versie: META.versie, gegenereerd: new Date().toISOString(),
  methode: 'WCAG 2.x relatieve luminantie (npm wcag-contrast); ΔE = Euclidische afstand in OKLab ×100 (culori); paletcontrole: dataviz-skill validate_palette.js (Machado 2009 CVD).',
  eisen: { AAA: '7:1 (beide tekstniveaus en alle statustekst)', AA: '4,5:1', icoon: '4,5:1 (statusicoon/-rand: strenger dan 3:1 zodat de aliaslaag direct AA is)', ui: '3:1 niet-tekst (WCAG 1.4.11)', info: 'alleen gerapporteerd' },
  thema: {}, scheiding: {}, grafiekpalet: {}, samenvatting: {} };
let fouten = 0;
const foutLijst = [];
for (const [th, t] of Object.entries(T)) {
  res.thema[th] = P.map(([v, a, eis, wat]) => {
    const r = Math.round(wcag(t[v], t[a]) * 100) / 100;
    const okk = r >= EIS[eis];
    if (!okk && eis !== 'info') { fouten++; foutLijst.push(`${th}: ${v} op ${a} = ${r} (eis ${eis})`); }
    return { voorgrond: v, achtergrond: a, kleuren: `${t[v]} op ${t[a]}`, ratio: r, eis, eisRatio: EIS[eis], oordeel: eis === 'info' ? 'info' : okk ? 'voldoet' : 'VOLDOET NIET', gebruik: wat };
  });
}

// ΔE-scheiding: grafiek-/domeinkleur ↔ status/risico/goedkeuring/gate >= 15 (harde controle)
const REEKS = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'domain-heat', 'domain-cool', 'domain-boiler', 'domain-light-on', 'domain-lane-gpu', 'domain-lane-cpu'];
const STAT = ['healthy', 'degraded', 'down', 'unknown', 'info', 'approval', 'risk-1', 'risk-3', 'gate'];
for (const [th, t] of Object.entries(T)) {
  const rijen = [];
  for (const a of REEKS) for (const b of STAT) {
    const d = Math.round(dE(t[a], t[b]) * 10) / 10;
    rijen.push({ reeks: a, status: b, kleuren: `${t[a]} ↔ ${t[b]}`, dE: d, oordeel: d >= 15 ? 'voldoet' : 'VOLDOET NIET' });
    if (d < 15) { fouten++; foutLijst.push(`${th}: ΔE ${a} ↔ ${b} = ${d}`); }
  }
  // status onderling
  const S = ['healthy', 'degraded', 'down', 'unknown', 'approval'];
  for (let i = 0; i < S.length; i++) for (let j = i + 1; j < S.length; j++) {
    const d = Math.round(dE(t[S[i]], t[S[j]]) * 10) / 10;
    rijen.push({ reeks: S[i], status: S[j], soort: 'status onderling (eis >= 10; icoon + woord + vorm dragen het verschil)', kleuren: `${t[S[i]]} ↔ ${t[S[j]]}`, dE: d, oordeel: d >= 10 ? 'voldoet' : 'VOLDOET NIET' });
    if (d < 10) { fouten++; foutLijst.push(`${th}: ΔE status ${S[i]} ↔ ${S[j]} = ${d}`); }
  }
  const band = th === 'licht' ? 'L <= 0,50' : 'L >= 0,74';
  const lband = STAT.map((s) => ({ token: s, L: +toLch(t[s]).l.toFixed(3) }));
  res.scheiding[th] = { regel: `grafiek/domein ↔ status/risico/goedkeuring/gate: ΔE (OKLab×100) >= 15; status onderling >= 10; statuskleuren buiten de grafiekband (${band})`, laagste_grafiek_status: Math.min(...rijen.filter((r) => !r.soort).map((r) => r.dE)), laagste_status_onderling: Math.min(...rijen.filter((r) => r.soort).map((r) => r.dE)), lichtheid_status: lband, paren: rijen };
}

// Dataviz-validator
const VAL = process.env.DATAVIZ_VALIDATOR || '';
if (fs.existsSync(VAL)) {
  const { validate, validateOrdinal } = await import(pathToFileURL(VAL).href);
  const fmt = (v) => ({ ok: v.ok, checks: v.report.map(([n, s, d]) => `${s === true || s === 'pass' ? 'PASS' : s === 'floor' || s === 'relief' ? 'WARN' : 'FAIL'} ${n}: ${d}`) });
  for (const [th, t] of Object.entries(T)) {
    const mode = th === 'licht' ? 'light' : 'dark';
    const pal = [1, 2, 3, 4, 5].map((i) => t[`chart-${i}`]);
    const seq = ['chart-seq-300', 'chart-seq-400', 'chart-seq-500', 'chart-seq-600', 'chart-seq-700'].map((k) => t[k]);
    const r = {
      palet: pal.join(','), oppervlak: t.card,
      aangrenzend: fmt(validate(pal, { mode, surface: t.card })),
      eerste3_alle_paren: fmt(validate(pal.slice(0, 3), { mode, surface: t.card, pairs: 'all' })),
      ordinaal_blauw_300_700: fmt(validateOrdinal(th === 'licht' ? seq : seq.slice().reverse().reverse(), { mode, surface: t.card })),
    };
    const div = ['chart-div-neg-3', 'chart-div-neg-2', 'chart-div-neg-1', 'chart-div-mid', 'chart-div-pos-1', 'chart-div-pos-2', 'chart-div-pos-3'].map((k) => +toLch(t[k]).l.toFixed(3));
    r.divergerend_L = div;
    r.divergerend_symmetrisch = Math.abs(div[0] - div[6]) < 0.03 && Math.abs(div[1] - div[5]) < 0.03 && Math.abs(div[2] - div[4]) < 0.03;
    for (const k of ['aangrenzend', 'eerste3_alle_paren']) if (!r[k].ok) { fouten++; foutLijst.push(`${th}: validator ${k} FAIL`); }
    if (r[`aangrenzend`].checks.some((c) => c.startsWith('WARN CVD'))) foutLijst.push(`${th}: CVD in de WARN-band (6–8)`);
    if (!r.divergerend_symmetrisch) { fouten++; foutLijst.push(`${th}: divergerende trap niet symmetrisch`); }
    res.grafiekpalet[th] = r;
  }
  res.grafiekpalet.methode = 'Kleuren: dataviz-referentietinten zonder groen/rood (status) en violet (goedkeuring). Licht: aqua/geel/magenta op dezelfde OKLCH-tint en -chroma tot de hoogste L met >= 3:1 op card (snap-to-passing). Volgorde: alle 24 volgordes met blauw eerst doorgerekend; gekozen = hoogste minimale CVD-ΔE die in beide thema\'s alle checks haalt.';
} else {
  // Zonder validator (bv. in CI): de laatst gemeten paletcontrole behouden, nooit stil weggooien.
  try { const vorig = JSON.parse(fs.readFileSync(D + 'contrast.json', 'utf8')).grafiekpalet;
    if (vorig && vorig.licht) { res.grafiekpalet = vorig; res.grafiekpalet.overgenomen = 'validator niet gevonden: paletcontrole overgenomen uit de vorige meting'; }
    else res.grafiekpalet.overgeslagen = 'validator niet gevonden'; } catch { res.grafiekpalet.overgeslagen = 'validator niet gevonden'; }
  console.warn('LET OP: DATAVIZ_VALIDATOR niet gezet; paletcontrole niet opnieuw gemeten.');
  console.warn('LET OP: dataviz-validator niet gevonden; paletcontrole overgeslagen');
}

for (const [th, rijen] of Object.entries(res.thema)) {
  const tekst = rijen.filter((r) => r.eis === 'AAA');
  res.samenvatting[th] = {
    paren: rijen.length,
    aaa_tekstparen: `${tekst.filter((r) => r.ratio >= 7).length} van ${tekst.length}`,
    laagste_aaa_tekst: Math.min(...tekst.map((r) => r.ratio)),
    ui_en_icoon_paren: `${rijen.filter((r) => ['ui', 'icoon'].includes(r.eis) && r.ratio >= r.eisRatio).length} van ${rijen.filter((r) => ['ui', 'icoon'].includes(r.eis)).length}`,
    laagste_dE_grafiek_status: res.scheiding[th].laagste_grafiek_status,
    laagste_dE_status_onderling: res.scheiding[th].laagste_status_onderling,
  };
}
res.harde_fouten = fouten;
res.foutlijst = foutLijst;
fs.writeFileSync(D + 'contrast.json', JSON.stringify(res, null, 2) + '\n');
console.log(JSON.stringify(res.samenvatting, null, 1));
for (const th of ['licht', 'donker']) if (res.grafiekpalet[th]) { console.log(th, res.grafiekpalet[th].palet); for (const k of ['aangrenzend', 'eerste3_alle_paren', 'ordinaal_blauw_300_700']) console.log('  ', k, res.grafiekpalet[th][k].checks.join(' | ')); console.log('   div L', res.grafiekpalet[th].divergerend_L.join(' ')); }
console.log('harde fouten:', fouten); for (const f of foutLijst) console.log('  -', f);
process.exit(fouten ? 1 : 0);
