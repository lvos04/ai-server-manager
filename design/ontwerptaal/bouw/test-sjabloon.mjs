// Tests voor het statuspagina-sjabloon en de referentie-renderers (Peil 1.1.1). Gebruik: node bouw/test-sjabloon.mjs
// (na genereer.mjs). Draait ook in alles.mjs. Vereist python3 voor de vergelijking met bouw/sjabloon.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { render, lees } from './sjabloon.mjs';
import { DATA } from './pagina-statuspagina.mjs';

const D = new URL('../', import.meta.url).pathname;
const TPL = fs.readFileSync(D + 'statuspagina.html', 'utf8');
const CSS = fs.readFileSync(D + 'statuspagina.css', 'utf8');
const TONEN = ['gezond', 'beperkt', 'storing', 'onbekend', 'verouderd', 'niet-beschikbaar', 'nog-niet', 'niet-gekoppeld', 'gate', 'beleid', 'feit'];

// De renderer van 1.1.0 (letterlijk), alleen om te bewijzen dat de uitvoer voor gewone gegevens gelijk blijft.
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
function renderOud(tpl, data) {
  const blokken = (t, d) => t
    .replace(/<!--ELK:(\w+)-->([\s\S]*?)<!--\/ELK:\1-->/g, (_, k, inh) => (d[k] || []).map((item) => blokken(inh, { ...d, ...item })).join(''))
    .replace(/<!--ALS:(\w+)-->([\s\S]*?)<!--\/ALS:\1-->/g, (_, k, inh) => (d[k] ? blokken(inh, d) : ''))
    .replace(/<!--NIET:(\w+)-->([\s\S]*?)<!--\/NIET:\1-->/g, (_, k, inh) => (d[k] ? '' : blokken(inh, d)))
    .replace(/\{\{(\w+)\}\}/g, (_, k) => esc(d[k]));
  return blokken(tpl, data);
}

const python = (data) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'peil-sjabloon-'));
  try {
    fs.writeFileSync(path.join(dir, 'gegevens.json'), JSON.stringify(data));
    return execFileSync('python3', ['-I', path.join(D, 'bouw', 'sjabloon.py'), D + 'statuspagina.html', path.join(dir, 'gegevens.json')], { encoding: 'utf8', maxBuffer: 4e6 });
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
};

test('één doorgang: uitvoer gelijk aan 1.1.0 voor de prototypes (geen waarde met accolades)', () => {
  for (const [naam, data] of Object.entries(DATA)) assert.equal(render(TPL, data), renderOud(TPL, data), naam);
});

test('E07: een waarde met {{x}} wordt nooit opnieuw ingevuld (1.1.0 toonde de CSRF-waarde)', () => {
  const data = { ...DATA['statuspagina'], checks: [{ naam: '{{csrf_token}}', toon: 'gezond', label: 'Gezond', tijd: '11:56', iso: '' }] };
  const nieuw = render(TPL, data), oud = renderOud(TPL, data);
  assert.ok(nieuw.includes('<span class="naam">{{csrf_token}}<span class="sr">'), 'letterlijk');
  assert.ok(oud.includes('<span class="naam">voorbeeld-csrf<span class="sr">'), 'bewijs dat 1.1.0 dit fout deed');
});

test('JS- en Python-renderer geven byte-gelijke uitvoer', () => {
  const extra = { ...DATA['statuspagina'], checks: [{ naam: '{{csrf_token}} & <b>"\'', toon: 'onbekend', label: 'Onbekend', tijd: '', iso: '' }], leeg: [] };
  for (const [naam, data] of [...Object.entries(DATA), ['accolades en tekens', extra]]) assert.equal(python(data), render(TPL, data), naam);
});

test('sjabloonfouten worden gemeld, niet stil overgeslagen', () => {
  assert.throws(() => lees('<!--ALS:a-->x'), /niet gesloten/);
  assert.throws(() => lees('<!--ALS:a--><!--NIET:b--><!--/ALS:a--><!--/NIET:b-->'), /onverwachte sluiting/);
  assert.equal(render('<!--ALS:a--><!--ALS:a-->x<!--/ALS:a--><!--/ALS:a-->', { a: 1 }), 'x', 'geneste blokken met dezelfde naam');
  assert.equal(render('<!--ALS:l-->vol<!--/ALS:l--><!--NIET:l-->leeg<!--/NIET:l-->', { l: [] }), 'leeg', 'lege lijst = onwaar');
});

test('elke toon heeft een pilklasse en een symbool met dezelfde naam', () => {
  for (const t of TONEN) {
    assert.ok(CSS.includes(`.pil-${t}`), `.pil-${t} ontbreekt in statuspagina.css`);
    assert.ok(TPL.includes(`<symbol id="i-${t}"`), `symbool i-${t} ontbreekt`);
  }
  const gebruikt = new Set(Object.values(DATA).flatMap((d) => [...(d.checks || []), ...(d.dienst_blok || [])].map((r) => r.toon)));
  for (const t of gebruikt) assert.ok(TONEN.includes(t), `onbekende toon ${t}`);
  assert.ok(!/\{\{icoon_/.test(TPL), 'icoonplek niet ingevuld door genereer.mjs');
});

test('formulieren: novalidate, (verplicht) en geen formulier bij onleesbaar of koppelen bezig', () => {
  assert.equal((TPL.match(/<form /g) || []).length, (TPL.match(/<form [^>]*novalidate>/g) || []).length);
  const leesbaar = render(TPL, DATA['statuspagina']);
  assert.equal((leesbaar.match(/\(verplicht\)/g) || []).length, 3);
  for (const k of ['statuspagina-onleesbaar', 'statuspagina-bezig']) {
    const h = render(TPL, DATA[k]);
    assert.ok(!h.includes('<form'), `${k}: geen formulier`);
    assert.ok(!h.includes('role="alert"'), `${k}: geen alert bij een bestaande toestand`);
  }
  assert.ok(render(TPL, DATA['statuspagina-bezig']).includes('Koppelen bezig'));
  assert.ok(render(TPL, DATA['statuspagina-onleesbaar']).includes('Onleesbaar'));
});

test('meldingsrol: alleen alert of status, en zonder rol ook geen aria-labelledby', () => {
  const zonder = render(TPL, DATA['statuspagina-onleesbaar']);
  assert.match(zonder, /<div class="melding melding-fout" style=/);
  assert.match(render(TPL, DATA['statuspagina']), /role="alert" aria-labelledby="melding-titel"/);
  assert.match(render(TPL, DATA['statuspagina-gekoppeld']), /role="status" aria-labelledby="melding-titel"/);
});

test('grootte: statuspagina.css < 15 KB (doel < 8 KB), sjabloon met inline CSS < 30 KB', () => {
  const css = Buffer.byteLength(CSS), tpl = Buffer.byteLength(TPL);
  assert.ok(css < 15000, `statuspagina.css ${css} B`);
  assert.ok(tpl < 30000, `statuspagina.html ${tpl} B`);
  console.log(`# statuspagina.css ${css} B, statuspagina.html ${tpl} B`);
});
