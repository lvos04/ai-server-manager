// S-040 Apps (lijst, P1) en S-041/S-045 Appdetail in fase P1: gezondheid per onderdeel (TrueNAS-staat, buitenkant,
// binnenkant) en acties zichtbaar maar uitgeschakeld tot fase P2. Alle data fictief.
import { i, status, knop, deeplink, kopieer, meta, melding, shell, paginakop, kruimel, tabs, tabpaneel, voorbeeld } from './ui.mjs';

const kort = (d) => `<span class="font-mono">${d.slice(0, 11)}…${d.slice(-4)}</span>`;
const WIJZE = { ix: 'Custom App (standaardformulier)', cat: 'Catalogusapp', yaml: 'Compose (YAML)' };

// Eén app: [naam, app-id/runtime, status, label, reden, tag, digest, wijze, eigenaar, href]
const APPS = [
  ['Voorbeeld-app', 'voorbeeld-app', 'storing', 'Storing', 'TrueNAS meldt de app als gecrasht; Uptime Kuma krijgt geen antwoord sinds 11:54.', '2.4.1', 'sha256:91c4e07b2f6a8d13c5e9b40a7f21d6c83e5b9a0f4d7c2e1b8a63f50d9e47d02', 'cat', 'App van derden', 'problemen.html'],
  ['appstore-en-fork', 'appstore-en-fork', 'beperkt', 'Beperkt', 'Antwoordt (HTTP 200), maar de worker rondde sinds 10:40 geen taken af.', '0.3.2', 'sha256:5be8a7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6ea913', 'ix', 'Eigen dienst', 'appdetail-p1.html'],
  ['MediaGuard', 'mediaguard', 'onbekend', 'Onbekend', 'Binnenkant volgt in fase P3 (koppeling met MediaGuard). TrueNAS: draait; Uptime Kuma: bereikbaar.', '3.8.0', 'sha256:0c7d4e2f1a9b8c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c21', 'ix', 'Bestaande app', '#'],
  ['my_house', 'my-house', 'verouderd', 'Verouderd', 'Laatste meting 10:12; sindsdien geen antwoord. Status onbekend.', '1.9.3', 'sha256:d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d4e5', 'ix', 'Bestaande app', '#'],
  ['home-control-hub', 'home-control-hub', 'gezond', 'Gezond', 'Bereikbaar en de eigen gezondheidscontrole is vers (11:55).', '0.4.0', 'sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7b81', 'ix', 'Eigen dienst', '#'],
  ['Gotify', 'gotify', 'onbekend', 'Onbekend', 'Geen Uptime Kuma-monitor gekoppeld; alleen de TrueNAS-staat is bekend.', '2.6.1', null, 'cat', 'App van derden', '#'],
  ['Uptime Kuma', 'uptime-kuma', 'gezond', 'Gezond', 'Monitor bereikbaar in 41 ms; TrueNAS: draait.', '2.0.2', 'sha256:2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a', 'cat', 'App van derden', '#'],
];

export function apps() {
  const chips = [['Alle', 7, true], ['Storing', 1], ['Beperkt', 1], ['Onbekend', 3], ['Gezond', 2]]
    .map(([l, n, aan]) => `<button type="button" class="knop ${aan ? 'knop-primair' : 'knop-secundair'} knop-klein" aria-pressed="${!!aan}">${l} <span class="cijfers">(${n})</span></button>`).join('');
  const filter = `
<form class="flex flex-col gap-3" role="search" aria-label="Apps filteren">
  <div class="flex flex-wrap items-end gap-2">
    <div class="min-w-0 flex-1 basis-56"><label for="zoek-app" class="veld-label text-sm">Zoeken</label><input id="zoek-app" type="search" class="invoer mt-1" placeholder="Naam, app-id of image"></div>
    <button type="button" class="knop knop-secundair">${i('filter')}<span>Meer filters</span></button>
  </div>
  <div class="flex flex-wrap gap-2" role="group" aria-label="Gezondheid">${chips}</div>
</form>`;

  const rij = ([naam, id, st, label, reden, tag, digest, wijze, eig, href]) => `<tr class="border-b border-border align-top">
  <th scope="row" class="py-3 pr-4 text-left font-normal"><a href="${href}" class="inline-flex min-h-touch flex-col justify-center font-semibold">${naam}</a><span class="block font-mono text-sm text-muted-foreground">${id}</span></th>
  <td class="py-3 pr-4"><div class="flex flex-col gap-1.5">${status(st, label)}<span class="reden">${reden}</span></div></td>
  <td class="py-3 pr-4 text-sm"><span class="font-semibold">${tag}</span><span class="block">${digest ? kort(digest) : 'digest onbekend'}</span></td>
  <td class="py-3 pr-4 text-sm">${WIJZE[wijze]}<span class="block text-muted-foreground">${eig}</span></td>
  <td class="py-3 text-right"><a href="#" class="knop knop-secundair knop-klein" target="_blank" rel="noopener">${i('square-arrow-out-up-right')}<span>Openen</span><span class="sr-only"> ${naam} (opent in een nieuw tabblad)</span></a></td>
</tr>`;
  const tabel = `<table class="hidden w-full text-left lg:table" aria-labelledby="lijst-titel">
  <thead class="bg-muted text-sm"><tr><th scope="col" class="w-52 px-0 py-2 pr-4 font-semibold">App</th><th scope="col" class="py-2 pr-4 font-semibold">Gezondheid</th><th scope="col" class="py-2 pr-4 font-semibold">Versie</th><th scope="col" class="py-2 pr-4 font-semibold">Installatie en eigenaar</th><th scope="col" class="py-2 font-semibold"><span class="sr-only">Openen</span></th></tr></thead>
  <tbody>${APPS.map(rij).join('')}</tbody></table>`;
  const kaart = ([naam, id, st, label, reden, tag, digest, wijze, eig, href]) => `<li class="kaart gap-2">
  <div class="flex flex-wrap items-start justify-between gap-2"><a href="${href}" class="inline-flex min-h-touch items-center text-lg font-semibold">${naam}</a>${status(st, label)}</div>
  <p class="reden">${reden}</p>
  <dl class="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm"><dt class="font-semibold text-muted-foreground">App-id</dt><dd class="font-mono break-all">${id}</dd><dt class="font-semibold text-muted-foreground">Versie</dt><dd>${tag} · ${digest ? kort(digest) : 'digest onbekend'}</dd><dt class="font-semibold text-muted-foreground">Installatie</dt><dd>${WIJZE[wijze]}</dd><dt class="font-semibold text-muted-foreground">Eigenaar</dt><dd>${eig}</dd></dl>
  <a href="#" class="knop knop-secundair w-full sm:w-auto" target="_blank" rel="noopener">${i('square-arrow-out-up-right')}<span>Openen in ${naam}</span><span class="sr-only"> (opent in een nieuw tabblad)</span></a>
</li>`;
  const lijst = `
<section aria-labelledby="lijst-titel" class="kaart gap-4" data-testid="app-lijst">
  <div class="flex flex-wrap items-baseline justify-between gap-2"><h2 id="lijst-titel" class="text-xl font-bold">Apps op de NAS</h2><p class="text-sm text-muted-foreground" aria-live="polite">7 apps · slechtste status eerst · filter: alle</p></div>
  ${tabel}
  <ul class="flex flex-col gap-3 lg:hidden">${APPS.map(kaart).join('')}</ul>
</section>`;

  const inhoud = paginakop({
    kruimel: kruimel([['Server', 'server-metrieken.html'], ['Apps', '']]),
    titel: 'Apps',
    omschrijving: 'Alle apps op de NAS met hun gezondheid. Alleen lezen: herstarten, bijwerken en andere acties volgen in fase P2.',
    bijgewerkt: 'Catalogus bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> · inventaris van <time datetime="2026-11-09T11:54:00+01:00">11:54</time> (TrueNAS app.query)',
    acties: knop('Catalogus bijwerken', { ic: 'refresh-cw' }),
  }) + `<div class="flex flex-col gap-4">${filter}<p class="text-sm">Gezond betekent: bereikbaar én (voor apps met eigen taken) een verse controle van binnenuit. "Draait" volgens TrueNAS alleen is nooit gezond.</p>${lijst}</div>`;
  return shell({ pagina: 'apps', zijHuidig: 'server', titel: 'Apps', inhoud });
}

const onderdeel = (naam, bron, st, label, reden, tijd) => `<li class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5">
  <span class="mr-auto min-w-0 sm:mr-0 sm:w-44 sm:shrink-0"><span class="block font-semibold">${naam}</span><span class="text-sm text-muted-foreground">${bron}</span></span>
  ${st ? status(st, label) : `<span class="status status-neutraal">${i('power')}<span>${label}</span></span>`}
  <span class="reden basis-full sm:basis-auto sm:flex-1">${reden}${tijd ? ` · <time datetime="2026-11-09T${tijd}:00+01:00">${tijd}</time>` : ''}</span></li>`;

const P2 = (titel, code, wat, naam) => `<li class="flex flex-col gap-2 border-b border-border py-3 md:flex-row md:items-center md:gap-4">
  <div class="flex min-w-0 flex-1 flex-col gap-1"><span class="font-semibold">${titel}</span><p class="text-sm text-muted-foreground"><code class="code-inline text-foreground">${code}</code> · ${wat}</p></div>
  <div class="flex shrink-0 flex-col gap-1 md:items-end"><button type="button" class="knop knop-secundair w-full md:w-auto" aria-disabled="true" aria-describedby="p2-reden">${i('hourglass')}<span>${titel}</span><span class="sr-only">: ${naam}</span></button><span class="text-sm text-muted-foreground">Volgt in fase P2</span></div>
</li>`;

export function appdetailP1() {
  const naam = 'appstore-en-fork';
  const kop = paginakop({
    kruimel: kruimel([['Server', 'server-metrieken.html'], ['Apps', 'apps.html'], [naam, '']]),
    titel: naam,
    omschrijving: 'Eigen dienst · Custom App (standaardformulier) · versie 0.3.2',
    acties: deeplink(naam),
  });
  const kopStatus = `<section class="kaart mb-6 gap-4" aria-labelledby="gz-titel" data-testid="app-gezondheid">
  <h2 id="gz-titel" class="sr-only">Gezondheid</h2>
  <div class="flex flex-wrap items-center gap-3">${status('beperkt', 'Beperkt', 'status-groot')}<p class="min-w-0 flex-1 basis-60">Antwoordt (HTTP 200), maar de worker rondde sinds 10:40 geen taken af. <a href="problemen.html">Incident bekijken</a></p></div>
  <div><h3 class="font-bold">Gezondheid per onderdeel</h3>
  <ul class="divide-y divide-border border-y border-border">
    ${onderdeel('TrueNAS-staat', 'TrueNAS app.query', null, 'Draait', 'Draaien alleen is geen bewijs van gezond.', '11:54')}
    ${onderdeel('Buitenkant', 'Uptime Kuma', 'gezond', 'Gezond', 'HTTP 200 in 84 ms.', '11:55')}
    ${onderdeel('Binnenkant', 'Gezondheidscontrole van de dienst', 'beperkt', 'Beperkt', 'Controle "worker": geen afgeronde taken sinds 10:40.', '11:55')}
  </ul></div>
  <div class="grid gap-4 md:grid-cols-2">${kopieer('Image-digest', 'sha256:5be8a7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6ea913')}${meta({ bron: 'TrueNAS-API (app.query, app.image.query), Uptime Kuma', tijd: '11:56', rel: 'zojuist', extra: [['Image', '<span class="font-mono break-all">ghcr.io/voorbeeld/appstore-en-fork:0.3.2</span>'], ['Data-dataset', '<span class="font-mono">voorbeeldpool/<wbr>apps/<wbr>appstore</span>'], ['Resourcegrenzen', 'Onbekend — de Hub leest de app-configuratie niet (kan geheimen bevatten).']] })}</div>
</section>`;
  const T = [['status', 'Status', 'activity'], ['metrieken', 'Metrieken', 'chart-line'], ['logs', 'Logs', 'scroll-text'], ['versies', 'Versies', 'tag'], ['acties', 'Acties', 'list-checks']];
  const acties = `
<section aria-labelledby="ac-titel" class="kaart gap-4">
  <h2 id="ac-titel" class="text-lg font-bold">Acties</h2>
  ${melding('nogniet', 'hourglass', `<p id="p2-reden"><strong>Nog niet beschikbaar — volgt in fase P2 (veilig automatiseren).</strong> Dan opent elke actie eerst een voorstel met preview, het risico volgens het beleid, een back-up vooraf en een controle na uitvoering. Tot dan wijzigt de Hub niets aan apps.</p>`)}
  <ul>
    ${P2('Herstarten', 'app.restart', 'risico bepaalt het beleid (R1 of R2)', naam)}
    ${P2('Stoppen', 'app.stop', 'risico bepaalt het beleid', naam)}
    ${P2('Bijwerken', 'app.update', 'back-up vooraf; risico bepaalt het beleid', naam)}
    ${P2('Terugzetten', 'app.rollback', 'alleen met een herstelplan', naam)}
    ${P2('Verwijderen (container)', 'app.uninstall', 'data blijft bewaard op de dataset', naam)}
  </ul>
  <p class="flex items-start gap-2 text-sm">${i('ban', 'mt-0.5 size-4 shrink-0 text-gate')}<span><strong>Data verwijderen (R3)</strong> staat hier bewust niet. Dat is een aparte flow met een eigen bevestiging en wordt nooit door de AI aangeboden.</span></p>
  <p class="text-sm">Wat nu al kan: <strong>Openen in ${naam}</strong> (bovenaan) — alleen lezen, de Hub wijzigt niets. ${voorbeeld()}</p>
</section>`;
  const inhoud = kop + kopStatus + tabs('app', T, 'acties')
    + tabpaneel('app', 'status', 'acties', '<div class="kaart"><h2 class="text-lg font-bold">Status</h2><p>Controles, uptime en laatste incidenten.</p></div>')
    + tabpaneel('app', 'metrieken', 'acties', '<div class="kaart"><h2 class="text-lg font-bold">Metrieken</h2><p>Zie het patroon in de metriekenschermen.</p></div>')
    + tabpaneel('app', 'logs', 'acties', '<div class="kaart"><h2 class="text-lg font-bold">Logs</h2><p>Geschoonde logregels van deze dienst.</p></div>')
    + tabpaneel('app', 'versies', 'acties', '<div class="kaart"><h2 class="text-lg font-bold">Versies</h2><p>Huidige versie en image-historie.</p></div>')
    + tabpaneel('app', 'acties', 'acties', acties);
  return shell({ pagina: 'apps', zijHuidig: 'server', titel: `${naam} — acties`, inhoud });
}
