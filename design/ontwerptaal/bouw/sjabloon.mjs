// Minimale renderer voor het statuspagina-sjabloon (referentie; een Python-dienst doet hetzelfde in ± 30 regels).
// {{x}} = tekst (HTML-escaped) · <!--ALS:x-->…<!--/ALS:x--> · <!--NIET:x-->…<!--/NIET:x--> · <!--ELK:l-->…<!--/ELK:l-->
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
export function render(tpl, data) {
  const blokken = (t, d) => t
    .replace(/<!--ELK:(\w+)-->([\s\S]*?)<!--\/ELK:\1-->/g, (_, k, inh) => (d[k] || []).map((item) => blokken(inh, { ...d, ...item })).join(''))
    .replace(/<!--ALS:(\w+)-->([\s\S]*?)<!--\/ALS:\1-->/g, (_, k, inh) => (d[k] ? blokken(inh, d) : ''))
    .replace(/<!--NIET:(\w+)-->([\s\S]*?)<!--\/NIET:\1-->/g, (_, k, inh) => (d[k] ? '' : blokken(inh, d)))
    .replace(/\{\{(\w+)\}\}/g, (_, k) => esc(d[k]));
  return blokken(tpl, data);
}
