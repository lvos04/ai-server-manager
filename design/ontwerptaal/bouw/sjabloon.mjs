// Referentie-renderer voor het statuspagina-sjabloon (Peil 1.1.1). Een Python-dienst doet hetzelfde: bouw/sjabloon.py.
// {{x}} = tekst (HTML-escaped) · <!--ALS:x-->…<!--/ALS:x--> · <!--NIET:x-->…<!--/NIET:x--> · <!--ELK:l-->…<!--/ELK:l-->
//
// 1.1.1 (E07): ÉÉN doorgang. Het sjabloon wordt eerst in een boom gelezen (blokken mogen genest zijn, ook met dezelfde
// naam); daarna wordt de boom met de gegevens uitgeschreven. Een ingevulde waarde wordt nooit opnieuw als sjabloon
// gelezen: een bronnaam "{{csrf_token}}" blijft letterlijk die tekst (1.1.0 vulde na de blokken nog eens over de hele
// uitvoer in en toonde dan de CSRF-waarde). Een sjabloon met een niet-gesloten of verkeerd genest blok geeft een fout.
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const TOKEN = /<!--(\/?)(ELK|ALS|NIET):(\w+)-->|\{\{(\w+)\}\}/g;
// Waar = niet leeg: false, null, undefined, '', 0 en een lege lijst zijn onwaar (gelijk in sjabloon.py).
const waar = (v) => (Array.isArray(v) ? v.length > 0 : Boolean(v));

export function lees(tpl) {
  const wortel = { kids: [] }; const stapel = [wortel]; let pos = 0; let m;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(tpl))) {
    const top = stapel[stapel.length - 1];
    if (m.index > pos) top.kids.push(tpl.slice(pos, m.index));
    pos = TOKEN.lastIndex;
    if (m[4]) top.kids.push({ plek: m[4] });
    else if (!m[1]) { const blok = { soort: m[2], naam: m[3], kids: [] }; top.kids.push(blok); stapel.push(blok); }
    else {
      if (stapel.length === 1 || top.soort !== m[2] || top.naam !== m[3]) throw new Error(`sjabloon: onverwachte sluiting ${m[0]}`);
      stapel.pop();
    }
  }
  if (stapel.length !== 1) throw new Error(`sjabloon: blok niet gesloten: ${stapel[stapel.length - 1].soort}:${stapel[stapel.length - 1].naam}`);
  if (pos < tpl.length) wortel.kids.push(tpl.slice(pos));
  return wortel.kids;
}

function schrijf(knopen, d) {
  let uit = '';
  for (const k of knopen) {
    if (typeof k === 'string') uit += k;
    else if (k.plek) uit += esc(d[k.plek]);
    else if (k.soort === 'ELK') uit += (d[k.naam] || []).map((item) => schrijf(k.kids, { ...d, ...item })).join('');
    else if (k.soort === 'ALS') { if (waar(d[k.naam])) uit += schrijf(k.kids, d); }
    else if (!waar(d[k.naam])) uit += schrijf(k.kids, d);   // NIET
  }
  return uit;
}

export function render(tpl, data) {
  return schrijf(lees(tpl), data);
}
