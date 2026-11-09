// Peil — HTML-bouwstenen voor de statische prototypes. Elke functie komt overeen met een component in COMPONENTEN.md.
import fs from 'node:fs';
const ICONEN = JSON.parse(fs.readFileSync(new URL('./iconen.json', import.meta.url), 'utf8'));
export const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export const nb = (s) => String(s).replace(/ /g, '&nbsp;'); // vaste spatie tussen getal en eenheid

export const i = (naam, cls = 'size-5') => {
  if (!ICONEN[naam]) throw new Error('onbekend icoon ' + naam);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="${cls}" aria-hidden="true" focusable="false">${ICONEN[naam]}</svg>`;
};

// ── Vaste iconen per betekenis (ONTWERPTAAL.md §6) ────────────────────────────────────────────────────────────────
export const STATUS = {
  gezond: ['circle-check', 'Gezond'],
  beperkt: ['triangle-alert', 'Beperkt'],
  storing: ['octagon-x', 'Storing'],
  onbekend: ['circle-help', 'Onbekend'],
  verouderd: ['clock-alert', 'Verouderd'],
  gepauzeerd: ['circle-pause', 'Gepauzeerd'],
  nietgekoppeld: ['link-2-off', 'Niet gekoppeld'],
  nogniet: ['hourglass', 'Nog niet beschikbaar'],
  nietbeschikbaar: ['circle-slash', 'Niet beschikbaar'], // capability_unavailable (review 1.1.0: was circle-help)
};
export const status = (soort, label, extra = '') => {
  const [ic, std] = STATUS[soort];
  return `<span class="status status-${soort} ${extra}" data-status="${soort}">${i(ic)}<span>${label || std}</span></span>`;
};

// Treden-glyph: 4 staafjes gevuld t/m het niveau (R0 = 1 staaf … R3 = 4). Vorm draagt het niveau zonder kleur.
export const treden = (n) => {
  const h = [5, 8, 11, 14];
  return `<svg viewBox="0 0 19 16" class="h-4 w-[1.2rem]" aria-hidden="true" focusable="false">${h.map((hh, k) => k <= n
    ? `<rect x="${k * 5}" y="${16 - hh}" width="4" height="${hh}" rx="0.5" fill="currentColor"/>`
    : `<rect x="${k * 5 + 0.75}" y="${16 - hh + 0.75}" width="2.5" height="${hh - 1.5}" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.5"/>`).join('')}</svg>`;
};
export const RISICO = ['Alleen lezen', 'Omkeerbaar', 'Goedkeuring nodig', 'Destructief — extra bevestiging'];
export const risico = (n, woord) => `<span class="risico risico-${n}" data-risico="R${n}"><span class="risico-code">${treden(n)}R${n}</span><span class="risico-woord"><span class="sr-only">&nbsp;·&nbsp;</span>${woord || RISICO[n]}</span></span>`;

const ERNST = { kritiek: 'Kritiek', hoog: 'Hoog', middel: 'Middel', laag: 'Laag', info: 'Info' };
export const ernst = (s) => `<span class="ernst ernst-${s}" data-as="ernst"><span class="sr-only">Ernst: </span>${ERNST[s]}</span>`;

const ZEKER = { zeker: [3, 'Zeker'], waarschijnlijk: [2, 'Waarschijnlijk'], onzeker: [1, 'Onzeker'], weetniet: [0, 'Ik weet het niet'] };
export const zekerheid = (s) => {
  const [n, w] = ZEKER[s];
  return `<span class="zekerheid" data-as="zekerheid"><span class="flex gap-1" aria-hidden="true">${[0, 1, 2].map((k) => `<span class="stip ${k < n ? 'stip-vol' : ''}"></span>`).join('')}</span><span><span class="sr-only">Zekerheid: </span>${w}</span></span>`;
};
export const validatie = (t) => `<span class="validatie" data-as="validatie">${i('flask-conical')}<span><span class="sr-only">Validatie: </span>${t}</span></span>`;
// De waarde zelf draagt "≈" bij geschat (T-03); het label is altijd "· <kwaliteit>".
export const kwaliteit = (t) => `<span class="kwaliteit">· ${t}</span>`;
export const voorbeeld = (t = 'Voorbeeld') => `<span class="voorbeeld">${t}</span>`;

// ── Versheid (C-06) ─────────────────────────────────────────────────────────────────────────────────────────────────
// bron, tijd (HH:MM), relatief, iso; optioneel poging (laatste poging zonder antwoord)
export const meta = ({ bron, tijd, rel, iso = '2026-11-09T11:56:00+01:00', poging, extra = [] }) => `
<dl class="meta">
  <dt>Bron</dt><dd>${bron}</dd>
  <dt>Bijgewerkt</dt><dd><time datetime="${iso}">${tijd}</time>${rel ? ` (${rel})` : ''}</dd>
  ${poging ? `<dt>Geprobeerd</dt><dd><time datetime="2026-11-09T11:56:00+01:00">${poging}</time></dd>` : ''}
  ${extra.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('')}
</dl>`;

// ── Knop / link ─────────────────────────────────────────────────────────────────────────────────────────────────────
export const knop = (label, { soort = 'secundair', ic, href, extra = '', attrs = '', na } = {}) => {
  const inh = `${ic ? i(ic) : ''}<span>${label}</span>${na ? i(na) : ''}`;
  return href ? `<a href="${href}" class="knop knop-${soort} ${extra}" ${attrs}>${inh}</a>` : `<button type="button" class="knop knop-${soort} ${extra}" ${attrs}>${inh}</button>`;
};
export const vervolg = (label, href = '#') => `<a href="${href}" class="knop knop-secundair knop-blok mt-auto"><span>${label}</span>${i('chevron-right')}</a>`;
export const deeplink = (app, href = '#') => `<a href="${href}" class="knop knop-secundair" target="_blank" rel="noopener">${i('square-arrow-out-up-right')}<span>Openen in ${app}</span><span class="sr-only"> (opent in een nieuw tabblad)</span></a>`;

// ── Kopieerveld (C-15) ──────────────────────────────────────────────────────────────────────────────────────────────
let kid = 0;
export const kopieer = (label, waarde, { klein } = {}) => {
  const id = 'kopieer-' + ++kid;
  return `<div class="flex flex-col gap-1">
  <span class="text-sm font-semibold" id="${id}-l">${label}</span>
  <div class="flex flex-wrap items-stretch gap-2">
    <code class="code-veld flex-1 basis-56" id="${id}" aria-labelledby="${id}-l">${waarde}</code>
    <button type="button" class="knop knop-secundair ${klein ? 'knop-klein' : ''}" data-kopieer="${id}">${i('copy')}<span>Kopiëren</span><span class="sr-only"> ${label}</span></button>
  </div>
  <p class="text-sm text-muted-foreground" aria-live="polite" data-kopieer-melding="${id}"></p>
</div>`;
};

// ── Foutpaneel (C-14) ───────────────────────────────────────────────────────────────────────────────────────────────
export const foutpaneel = ({ titel, waarom, doen, code, trace, kop = 'h3', opnieuw = true }) => `
<div class="melding melding-fout flex-col sm:flex-row" data-testid="error-panel">
  ${i('octagon-x')}
  <div class="flex min-w-0 flex-1 flex-col gap-3">
    <${kop} class="text-base font-bold">${titel}</${kop}>
    <p>${waarom} ${doen}</p>
    <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm"><dt class="font-semibold">Code</dt><dd><code class="code-inline text-foreground">${code}</code></dd></dl>
    ${kopieer('Trace-ID', trace)}
    ${opnieuw ? `<div class="flex flex-wrap gap-2">${knop('Opnieuw proberen', { ic: 'refresh-cw' })}<details class="w-full"><summary class="inline-flex min-h-touch cursor-pointer items-center gap-2 font-semibold">${i('chevron-down', 'size-5 klap-icoon')}Technische details</summary><pre class="mt-2 overflow-x-auto rounded-md bg-card p-3 text-sm text-foreground">HTTP 504 · GET /api/v1/apps/voorbeeld-app/logs?voor=10:02</pre></details></div>` : ''}
  </div>
</div>`;

// ── Melding / gate / nog niet beschikbaar ──────────────────────────────────────────────────────────────────────────
export const melding = (soort, ic, inhoud, { rol = '', actie = '' } = {}) => `
<div class="melding melding-${soort} flex-col sm:flex-row sm:items-start" ${rol ? `role="${rol}"` : ''} data-as="${soort}">
  ${i(ic)}
  <div class="min-w-0 flex-1">${inhoud}</div>
  ${actie ? `<div class="shrink-0">${actie}</div>` : ''}
</div>`;
export const gate = (titel, nodig, actie) => melding('gate', 'lock', `<p class="font-bold">${titel}</p><p class="mt-1">Nodig: ${nodig}</p><p class="mt-1 text-sm">Dit is geen storing; er wacht een voorwaarde. Doorgaan zonder kan niet.</p>`, { actie });

// ── App-schil (C-01) ────────────────────────────────────────────────────────────────────────────────────────────────
const ZIJ = [['home', 'Home', 'house', 'home.html'], ['server', 'Server', 'server', 'appdetail-metrieken.html'], ['media', 'Media', 'clapperboard', '#'],
  ['huis', 'Huis', 'sofa', 'huis.html'], ['netwerk', 'Netwerk', 'network', '#'], ['automatisering', 'Automatisering', 'workflow', '#'],
  ['backups', 'Backups', 'database-backup', '#'], ['kosten', 'Kosten', 'wallet', '#'], ['instellingen', 'Instellingen', 'settings', 'wizardstap.html']];
const ONDER = [['home', 'Home', 'house', 'home.html'], ['apps', 'Apps', 'layout-grid', 'appdetail.html'], ['problemen', 'Problemen', 'inbox', 'problemen.html', 3],
  ['ai', 'AI', 'bot', '#'], ['meer', 'Meer', 'menu', '#', 1]];
// Review 1.1.0: de violette goedkeuringsteller staat mobiel op "Meer" (eerste item in de Meer-sheet: Goedkeuringen), niet op
// "AI" — goedkeuringen komen ook van gebruikers en flows. Op de goedkeuringspagina is "Meer" het huidige item.

export function shell({ pagina, titel, inhoud, live = 'aan', banner = '', kind = false, zijHuidig }) {
  const zij = ZIJ.map(([k, l, ic, href]) => {
    const huidig = (zijHuidig || pagina) === k;
    const ouder = huidig && pagina === 'apps';
    return `<li><a href="${href}" class="zij-item${ouder ? ' zij-ouder' : ''}"${huidig && !ouder ? ' aria-current="page"' : ''}>${i(ic)}${l}</a>${k === 'server' && pagina === 'apps' ? `<ul class="mt-1 ml-6 border-l-2 border-border pl-2"><li><a href="appdetail.html" class="zij-item" aria-current="page">${i('layout-grid')}Apps</a></li></ul>` : ''}</li>`;
  }).join('');
  const onder = ONDER.map(([k, l, ic, href, n]) => `<a href="${href}" class="onder-item"${k === pagina || (k === 'meer' && pagina === 'goedkeuringen') ? ' aria-current="page"' : ''}><span class="relative">${i(ic)}${n ? `<span class="teller ${k === 'meer' ? 'teller-goedkeuring' : ''} absolute -top-2 -right-4" aria-hidden="true">${n}</span>` : ''}</span>${l}${n ? `<span class="sr-only">, ${n} ${k === 'meer' ? 'goedkeuring wacht' : 'open'}</span>` : ''}</a>`).join('');
  const liveEl = live === 'aan'
    ? `<span class="live" role="status">${i('radio')}<span>Live · 11:56</span></span>`
    : live === 'onderbroken' ? `<span class="live live-onderbroken" role="status">${i('wifi-off')}<span>Onderbroken · stand van 11:56</span></span>`
    : `<span class="live live-onderbroken" role="status">${i('wifi-off')}<span>Offline · stand van 11:52</span></span>`;
  return `<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${titel} — Hub (voorbeeld)</title>
<link rel="stylesheet" href="css/peil.css">
<script src="js/proto.js" defer></script>
<script>(function(){var h=location.hash,d=document.documentElement;var t=/thema=donker/.test(h)?'donker':/thema=licht/.test(h)?'licht':(matchMedia('(prefers-color-scheme: dark)').matches?'donker':'licht');d.classList.toggle('dark',t==='donker');if(/thema=/.test(h))d.setAttribute('data-afdruk','');})();</script>
</head>
<body>
<a href="#inhoud" class="skiplink knop knop-primair">Naar inhoud</a>
<div class="min-h-dvh lg:grid lg:grid-cols-[var(--spacing-sidebar)_minmax(0,1fr)]">
  ${kind ? '' : `<aside class="hidden border-r border-border bg-sidebar lg:block">
    <div class="sticky top-0 flex max-h-dvh flex-col gap-6 overflow-y-auto p-4">
      <a href="home.html" class="flex min-h-touch items-center gap-3 px-2 text-xl font-bold text-foreground no-underline">
        <span class="flex size-10 items-center justify-center rounded-lg bg-foreground text-background">${i('server', 'size-6')}</span>
        <span class="leading-tight">Hub<span class="block text-sm font-semibold text-muted-foreground">Thuisplatform</span></span>
      </a>
      <nav aria-label="Hoofdnavigatie"><ul class="flex flex-col gap-1">${zij}</ul></nav>
      <p class="mt-auto text-sm text-muted-foreground">Hub 0.2.0 · ${voorbeeld()}</p>
    </div>
  </aside>`}
  <div class="flex min-h-dvh min-w-0 flex-col">
    <header class="sticky top-0 z-30 border-b border-border bg-card">
      <div class="flex min-h-16 items-center gap-2 px-3 lg:px-6">
        <a href="${kind ? 'kind.html' : 'home.html'}" class="flex min-h-touch items-center gap-2 pr-1 text-lg font-bold text-foreground no-underline ${kind ? '' : 'lg:hidden'}"><span class="flex size-9 items-center justify-center rounded-lg bg-foreground text-background">${i(kind ? 'monitor-play' : 'server')}</span>${kind ? 'Thuis' : 'Hub'}</a>
        ${kind ? '' : `<button type="button" class="knop knop-secundair hidden w-56 justify-start font-normal whitespace-nowrap text-muted-foreground xl:inline-flex 2xl:w-72" aria-keyshortcuts="Control+K">${i('search')}<span>Zoeken</span><kbd class="ml-auto whitespace-nowrap text-foreground">Ctrl K</kbd></button>`}
        <div class="ml-auto flex min-w-0 items-center gap-1">
          ${kind ? '' : `<span class="hidden xl:inline-flex">${liveEl.replace(' role="status"', '')}</span>
          <span class="hidden lg:contents">
            <a href="problemen.html" class="kop-item"${pagina === 'problemen' ? ' aria-current="page"' : ''}>${i('inbox')}Problemen<span class="teller" aria-hidden="true">3</span><span class="sr-only">, 3 open</span></a>
            <a href="goedkeuring-r3.html" class="kop-item"${pagina === 'goedkeuringen' ? ' aria-current="page"' : ''}>${i('clipboard-check')}Goedkeuringen<span class="teller teller-goedkeuring" aria-hidden="true">1</span><span class="sr-only">, 1 wacht</span></a>
            <a href="#" class="kop-item">${i('bot')}AI</a>
          </span>
          <button type="button" class="knop knop-stil knop-icoon xl:hidden" aria-label="Zoeken" aria-keyshortcuts="Control+K">${i('search', 'size-6')}</button>`}
          <button type="button" class="knop knop-stil px-2 lg:px-3" aria-label="Gebruikersmenu: ${kind ? 'Sam (kinderprofiel)' : 'Beheerder'}">${i('circle-user', 'size-6')}<span class="hidden lg:inline">${kind ? 'Sam' : 'Beheerder'}</span>${i('chevron-down', 'hidden size-4 lg:block')}</button>
        </div>
      </div>
      ${kind ? '' : `<div class="border-t border-border px-3 py-1 xl:hidden lg:px-6">${liveEl}</div>`}
    </header>
    ${banner}
    <aside aria-label="Voorbeeldgegevens" class="border-b border-dashed border-border-strong bg-muted px-4 py-2 text-sm lg:px-8"><p>${voorbeeld()} Alle namen, adressen en waarden op dit scherm zijn fictief en dienen alleen het ontwerp.</p></aside>
    <main id="inhoud" tabindex="-1" class="mx-auto w-full max-w-content flex-1 px-4 pt-6 pb-10 sm:px-6 lg:px-8">
${inhoud}
    </main>
    ${kind ? `<nav class="onder-nav sticky bottom-0 z-30 flex border-t border-border bg-card pb-[env(safe-area-inset-bottom)]" aria-label="Hoofdnavigatie">
      <a href="kind.html" class="onder-item" aria-current="page">${i('house')}Home</a>
      <a href="#" class="onder-item">${i('monitor-play')}Kijken</a>
      <a href="#" class="onder-item">${i('search')}Zoeken</a>
      <a href="#" class="onder-item">${i('smile')}Ik</a>
    </nav>` : `<nav class="onder-nav sticky bottom-0 z-30 flex border-t border-border bg-card pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Hoofdnavigatie">${onder}</nav>`}
  </div>
</div>
</body>
</html>
`;
}

// Paginakop (C-02)
export const paginakop = ({ titel, omschrijving = '', bijgewerkt = '', acties = '', kruimel = '' }) => `
${kruimel}
<div class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
  <div class="min-w-0">
    <h1 class="text-2xl font-bold">${titel}</h1>
    ${omschrijving ? `<p class="mt-1 max-w-prose text-muted-foreground">${omschrijving}</p>` : ''}
    ${bijgewerkt ? `<p class="mt-1 text-sm text-muted-foreground">${bijgewerkt}</p>` : ''}
  </div>
  ${acties ? `<div class="flex flex-wrap gap-2">${acties}</div>` : ''}
</div>`;

export const kruimel = (items) => `<nav aria-label="Kruimelpad" class="mb-2"><ol class="flex flex-wrap items-center gap-x-1 text-sm">${items.map(([l, h], k) => k < items.length - 1
  ? `<li class="flex items-center gap-1"><a href="${h}" class="inline-flex min-h-touch min-w-touch items-center justify-center px-1">${l}</a>${i('chevron-right', 'size-4 text-muted-foreground')}</li>`
  : `<li><span aria-current="page" class="inline-flex min-h-touch items-center px-1 font-semibold">${l}</span></li>`).join('')}</ol></nav>`;

// Tabs (shadcn Tabs; prototype-gedrag in proto.js)
export const tabs = (id, items, actief) => `
<div class="tablijst" role="tablist" aria-label="Onderdelen van de app" data-tabs="${id}">
${items.map(([k, l, ic]) => `<button type="button" role="tab" id="${id}-tab-${k}" class="tab" aria-selected="${k === actief}" aria-controls="${id}-paneel-${k}" tabindex="${k === actief ? 0 : -1}">${i(ic)}${l}</button>`).join('')}
</div>`;
export const tabpaneel = (id, k, actief, inhoud) => `<div role="tabpanel" id="${id}-paneel-${k}" aria-labelledby="${id}-tab-${k}" class="pt-5"${k === actief ? '' : ' hidden'}>${inhoud}</div>`;

// ── Lijngrafiek (C-32) — HTML-labels (vaste lettergrootte) + SVG-plot met non-scaling-stroke ─────────────────────
// punten: [{t:'10:00', v:Number|null}] gelijk verdeeld; grens: {v, label}; ymax; eenheid; gat-index-bereiken worden automatisch afgeleid
export function lijngrafiek({ id, titel, beschrijving, punten, ymax, ystap, eenheid, grens, bron, bijgewerkt, reeksnaam }) {
  const n = punten.length, W = 1000, H = 1000;
  const x = (k) => (k / (n - 1)) * 100, y = (v) => 100 - (v / ymax) * 100;
  const segs = []; let cur = [];
  punten.forEach((p, k) => { if (p.v == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push(k); });
  if (cur.length) segs.push(cur);
  const paden = segs.map((s) => `<path d="${s.map((k, j) => `${j ? 'L' : 'M'}${(x(k) * W / 100).toFixed(1)} ${(y(punten[k].v) * H / 100).toFixed(1)}`).join(' ')}" fill="none" stroke="var(--chart-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`).join('');
  const vlakken = segs.map((s) => `<path d="M${(x(s[0]) * W / 100).toFixed(1)} ${H} ${s.map((k) => `L${(x(k) * W / 100).toFixed(1)} ${(y(punten[k].v) * H / 100).toFixed(1)}`).join(' ')} L${(x(s[s.length - 1]) * W / 100).toFixed(1)} ${H} Z" fill="var(--chart-1)" fill-opacity="0.1" stroke="none"/>`).join('');
  // gaten
  const gaten = []; let g0 = null;
  punten.forEach((p, k) => { if (p.v == null && g0 == null) g0 = k; if (p.v != null && g0 != null) { gaten.push([g0 - 1, k]); g0 = null; } });
  const gatEl = gaten.map(([a, b]) => `<div class="arcering-gat absolute inset-y-0 border-x border-dashed border-border-strong" style="left:${x(a)}%;width:${x(b) - x(a)}%"><span class="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-sm bg-card px-1.5 text-sm font-semibold whitespace-nowrap text-foreground">Geen meting</span></div>`).join('');
  const rasters = []; for (let v = 0; v <= ymax; v += ystap) rasters.push(v);
  const raster = rasters.map((v) => `<line x1="0" x2="${W}" y1="${(y(v) * H / 100).toFixed(1)}" y2="${(y(v) * H / 100).toFixed(1)}" stroke="var(${v === 0 ? '--chart-axis' : '--chart-grid'})" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join('');
  const ylab = rasters.map((v) => `<span class="grafiek-ylabel" style="top:${y(v)}%">${v.toLocaleString('nl-NL')}</span>`).join('');
  const xs = punten.map((p, k) => [p, k]).filter(([, k]) => k % Math.ceil(n / 6) === 0 || k === n - 1);
  const xlab = xs.map(([p, k]) => `<span class="grafiek-xlabel ${k !== 0 && k !== n - 1 ? 'hidden sm:inline' : ''}" style="left:${x(k)}%;${k === 0 ? 'translate:0 0' : k === n - 1 ? 'translate:-100% 0' : ''}">${p.t}</span>`).join('');
  const laatste = [...punten.keys()].reverse().find((k) => punten[k].v != null);
  const grensEl = grens ? `<line x1="0" x2="${W}" y1="${(y(grens.v) * H / 100).toFixed(1)}" y2="${(y(grens.v) * H / 100).toFixed(1)}" stroke="var(--chart-limit)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>` : '';
  const grensLabel = grens ? `<span class="absolute right-0 -translate-y-full pb-0.5 text-sm font-semibold text-foreground" style="top:${y(grens.v)}%">${grens.label}</span>` : '';
  const samenvatting = `${titel}. ${beschrijving}`;
  const tabel = `<table class="w-full text-left text-sm"><caption class="sr-only">${titel} als tabel</caption><thead><tr class="border-b border-border-strong"><th scope="col" class="py-1.5 pr-4">Tijd</th><th scope="col" class="py-1.5">${reeksnaam} (${eenheid})</th></tr></thead><tbody>${punten.map((p) => `<tr class="border-b border-border"><th scope="row" class="py-1 pr-4 font-normal cijfers">${p.t}</th><td class="py-1 cijfers">${p.v == null ? '<span class="font-semibold">Geen meting</span>' : p.v.toLocaleString('nl-NL')}</td></tr>`).join('')}</tbody></table>`;
  return `
<figure class="kaart" aria-labelledby="${id}-titel">
  <div class="flex flex-wrap items-start justify-between gap-2">
    <h3 id="${id}-titel" class="kaart-titel">${i('chart-line')}${titel}</h3>
  </div>
  <p class="text-sm text-muted-foreground">${beschrijving}</p>
  <div class="pl-12 pb-7 pt-5">
    <div class="grafiek-vlak" id="${id}" role="img" tabindex="0" aria-label="${esc(samenvatting)} Gebruik de pijltjestoetsen om per meetpunt te lezen." data-grafiek='${JSON.stringify({ punten, ymax, eenheid, reeksnaam })}'>
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="absolute inset-0 size-full overflow-visible" aria-hidden="true" focusable="false">${raster}${vlakken}${paden}${grensEl}</svg>
      ${gatEl}${ylab}${xlab}${grensLabel}
      <span class="grafiek-punt bg-chart-1" style="left:${x(laatste)}%;top:${y(punten[laatste].v)}%"></span>
      <span class="absolute -translate-y-1/2 text-sm font-semibold whitespace-nowrap text-foreground" style="${x(laatste) > 50 ? `right:${100 - x(laatste)}%` : `left:${x(laatste)}%`};top:${y(punten[laatste].v) + 8}%">${nb(punten[laatste].v.toLocaleString('nl-NL') + ' ' + eenheid)}</span>
      <div class="pointer-events-none absolute inset-y-0 hidden w-px bg-foreground" data-kruis></div>
      <div class="grafiek-tip" data-tip></div>
    </div>
  </div>
  <p class="sr-only" aria-live="polite" data-voorlees="${id}"></p>
  <figcaption class="flex flex-col gap-2 border-t border-border pt-3 text-sm text-muted-foreground">
    <span>Bron: ${bron} · bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">${bijgewerkt}</time> · een gat betekent dat er geen meting was (nooit 0).</span>
  </figcaption>
  <details><summary class="inline-flex min-h-touch cursor-pointer items-center gap-2 font-semibold">${i('table-2')}Toon als tabel</summary><div class="mt-2 max-h-72 overflow-y-auto" tabindex="0" role="region" aria-label="${titel}: tabel">${tabel}</div></details>
</figure>`;
}

// Meter (C-32): vulling + spoor van dezelfde trap; boven drempel de beperkt-rol met icoon + tekst.
export const meter = ({ label, waarde, max, eenheid, drempel = 0.9, bron, tijd }) => {
  const f = waarde / max, boven = f >= drempel, pct = Math.round(f * 100);
  return `<div class="flex flex-col gap-2">
  <div class="flex flex-wrap items-baseline justify-between gap-x-3"><span class="font-semibold" id="m-${label.length}">${label}</span><span><span class="text-2xl font-semibold">${nb(waarde.toLocaleString('nl-NL') + ' ' + eenheid)}</span> <span class="text-muted-foreground">van ${nb(max.toLocaleString('nl-NL') + ' ' + eenheid)}</span></span></div>
  <div class="h-3 overflow-hidden rounded-full ${boven ? 'bg-degraded-bg ring-1 ring-degraded' : 'bg-chart-meter-track'}" role="meter" aria-valuemin="0" aria-valuemax="${max}" aria-valuenow="${waarde}" aria-valuetext="${waarde} ${eenheid} van ${max} ${eenheid} (${pct}%)${boven ? ', boven de drempel' : ''}" aria-labelledby="m-${label.length}"><div class="h-full rounded-full ${boven ? 'bg-degraded' : 'bg-chart-1'}" style="width:${pct}%"></div></div>
  ${boven ? `<p class="flex items-center gap-1.5 text-sm font-semibold text-degraded-ink">${i('triangle-alert', 'size-4 text-degraded')}${pct}% van de grens — boven de drempel van ${Math.round(drempel * 100)}%</p>` : `<p class="text-sm text-muted-foreground">${pct}% van de grens</p>`}
</div>`;
};
