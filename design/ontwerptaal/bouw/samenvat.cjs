// Compacte samenvatting per richting × pagina (alle breedtes en thema's)
const fs = require('fs'); const path = require('path'); const dir = path.join(__dirname, '..', 'controle', 'uit');
const rows = [];
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort()) {
  const j = JSON.parse(fs.readFileSync(path.join(dir, f)));
  const R = j.runs; const by = (fn) => R.map(fn);
  const minL = Math.min(...R.filter(r => r.theme === 'licht').map(r => r.minTekst));
  const minD = Math.min(...R.filter(r => r.theme === 'donker').map(r => r.minTekst));
  const tf = [...new Set(R.flatMap(r => r.tekstFout.filter(x => !x.dis).map(x => `${r.theme}: "${x.t}" ${x.r}:1 (${x.fg} op ${x.bg}, opacity ${x.op})`)))];
  const minFont = Math.min(...by(r => r.minFont));
  const klein = [...new Set(R.flatMap(r => r.kleinFont.map(k => `${k.fs}px "${k.t}"`)))];
  const over = R.filter(r => r.overloop > 0).map(r => `${r.theme} ${r.w}: ${r.overloop}px`);
  const doel = [...new Set(R.filter(r => r.w <= 390).flatMap(r => r.doelen.filter(d => !d.inline && !/^label/.test(d.el)).map(d => `${d.w}x${d.h} "${d.t}"`)))];
  const doel1440 = Math.max(...R.filter(r => r.w === 1440).map(r => r.doelen.filter(d => !d.inline).length));
  const st = [...new Set(R.flatMap(r => r.stippel.filter(s => s.buiten < 3 && s.bw > 0).map(s => `${r.theme} ${s.buiten}:1 "${s.t.slice(0, 30)}"`)))];
  const afk = [...new Set(R.flatMap(r => r.afgekapt.map(a => `${r.w}: "${a.t.slice(0, 40)}"`)))];
  const fr = R.filter(r => r.focus);
  const ringMin = Math.min(...fr.map(r => r.focus.ringMin));
  const bedekt = [...new Set(fr.filter(r => r.w === 390).flatMap(r => r.focus.bedekt.map(b => b.replace(/ top=.*/, ''))))];
  const zonder = [...new Set(fr.flatMap(r => r.focus.zonderRing))];
  const zwak = [...new Set(fr.flatMap(r => r.focus.zwak))];
  const velden = [...new Set(R.flatMap(r => r.velden.filter(v => Math.max(v.rand, v.vlak) < 3).map(v => `${r.theme} ${v.el} ${v.rand}`)))];
  const veldMin = Math.min(...R.flatMap(r => r.velden.map(v => Math.max(v.rand, v.vlak))).concat([99]));
  console.log(`\n## ${f.replace('.json', '')}\n  tekst min licht ${minL} / donker ${minD}; minFont ${minFont}px; tekstfouten: ${tf.length ? tf.join(' | ') : 'geen'}`);
  if (klein.length) console.log(`  <12px: ${klein.join(' | ')}`);
  console.log(`  overloop: ${over.join(', ') || 'geen'}; afgekapt: ${afk.join(' | ') || 'geen'}`);
  console.log(`  doelen<44 @≤390 (excl. inline/labels): ${doel.join(' | ') || 'geen'}; @1440: ${doel1440}`);
  console.log(`  veldrand min ${veldMin === 99 ? '-' : veldMin}:1 ${velden.join(' | ')}; stippelrand<3: ${st.join(' | ') || 'geen'}`);
  console.log(`  focus: ring min ${ringMin}:1, breedtes ${[...new Set(fr.flatMap(r => r.focus.breedtes))]}, eerste ${fr[0] && fr[0].focus.eerste}; zonder ring ${zonder.join(', ') || '-'}; zwak ${zwak.join(', ') || '-'}; bedekt@390 (scroll-padding ${fr[0] && fr[0].scrollPadding}): ${bedekt.join(' | ') || 'geen'}`);
  console.log(`  beweging bij reduce: ${j.bewegingBijReduce.join(', ') || 'geen'}`);
  const sx = R.map(r => r.structuur).filter(Boolean)[0] || {};
  const kap = [...new Set(R.flatMap(r => (r.structuur || {}).kapot || []))];
  console.log(`  structuur: h1 ${sx.h1}, main ${sx.main}, role=status ${sx.status}, sprongen ${[...new Set(R.flatMap(r => (r.structuur||{}).sprong||[]))].join(',') || 'geen'}, dubbele id ${[...new Set(R.flatMap(r => (r.structuur||{}).dubbel||[]))].join(',') || 'geen'}, kapotte aria-ref ${kap.join(',') || 'geen'}`);
  const ax = [...new Set(R.filter(r => r.axe).flatMap(r => r.axe.map(v => `${r.theme}/${r.w} ${v.id} (${v.impact}, ${v.n}×) ${v.voorbeeld[0]}`)))];
  console.log(`  axe: ${ax.length ? '\n    ' + ax.join('\n    ') : '0 overtredingen'}`);
}
