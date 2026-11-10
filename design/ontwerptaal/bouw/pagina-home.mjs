// S-020 Home (en T-10 offline-variant). Alle data fictief.
import { i, status, risico, ernst, meta, knop, vervolg, shell, paginakop, melding, nb, kwaliteit } from './ui.mjs';

const kaart = ({ id, titel, ic, badge = '', variant = '', inhoud, metaHtml, verder, busy }) => `
<article class="kaart ${variant}" aria-labelledby="${id}"${busy ? ' aria-busy="true"' : ''} data-testid="kaart-${id}">
  <h3 id="${id}" class="kaart-titel">${i(ic)}${titel}</h3>
  ${badge ? `<div class="flex flex-wrap gap-2">${badge}</div>` : ''}
  ${inhoud}
  ${metaHtml || ''}
  ${verder || ''}
</article>`;

export function home({ offline = false } = {}) {
  // 1.1.1 (E15): offline wordt een laatst bekende Gezond (en Gepauzeerd) "Verouderd"; Beperkt en Storing blijven staan met
  // de tijd van de stand (een bekend probleem verdwijnt niet als de verbinding wegvalt); Onbekend en Nog niet blijven.
  const BLIJFT = ['storing', 'beperkt'];
  const offlineStatus = (s, l, verouderd) => (BLIJFT.includes(s) ? status(s, `${l} · stand van 11:52`) : s === 'onbekend' || s === 'nogniet' ? status(s, l) : status('verouderd', verouderd));
  const st = (s, l) => (offline ? offlineStatus(s, l, 'Verouderd · stand van 11:52') : status(s, l));
  // Review 1.1.0 — offline-regel: LEZEN blijft werken met de laatst bekende stand; alleen wat iets wijzigt of een verse
  // server nodig heeft (testen, wizard, vernieuwen, goedkeuren) staat uit. Zelfde label = overal dezelfde toestand.
  const LEZEN = ['Incident bekijken', 'Voorstel beoordelen'];
  const uit = (label, ic) => (offline && LEZEN.includes(label)
    ? `<div class="flex flex-col gap-1 sm:items-end">${knop(label, { soort: 'secundair', ic, href: label === 'Incident bekijken' ? 'problemen.html' : 'appdetail.html', extra: 'w-full sm:w-auto' })}<span class="text-sm text-muted-foreground">Toont de stand van 11:52</span></div>`
    : offline
    ? `<div class="flex flex-col gap-1 sm:items-end"><button type="button" class="knop knop-secundair w-full sm:w-auto" aria-disabled="true" aria-describedby="offline-reden">${i(ic)}<span>${label}</span></button><span class="text-sm text-muted-foreground">Uit: je bent offline</span></div>`
    : knop(label, { soort: label === 'Incident bekijken' ? 'primair' : 'secundair', ic, href: label === 'Incident bekijken' ? 'problemen.html' : label === 'Voorstel beoordelen' ? 'appdetail.html' : label === 'Onboarding verder' ? 'wizardstap.html' : '#', extra: 'w-full sm:w-auto' }));

  const rij = (naam, s, label, reden, href = '#') => `<li><a href="${href}" class="flex min-h-touch flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-foreground no-underline hover:bg-accent sm:flex-nowrap sm:px-2">
    <span class="mr-auto font-semibold sm:mr-0 sm:w-32 sm:shrink-0">${naam}</span>${offline ? offlineStatus(s, label, 'Verouderd') : status(s, label)}<span class="reden min-w-0 flex-1 basis-full sm:basis-auto">${reden}</span>${i('chevron-right', 'hidden size-5 shrink-0 text-muted-foreground sm:block')}</a></li>`;

  const systeem = `
<section aria-labelledby="sys-titel" class="kaart border-2 ${offline ? 'border-dashed border-unknown' : 'border-down'}" data-testid="systeemstatus">
  <div class="flex flex-wrap items-center gap-3">
    <h2 id="sys-titel" class="text-xl font-bold">Systeemstatus</h2>
    ${offline ? status('onbekend', 'Onbekend — offline', 'status-groot') : status('storing', 'Storing', 'status-groot')}
  </div>
  <p>${offline ? 'Laatst bekend om 11:52: <strong>Storing</strong>. Zonder verbinding weten we niet hoe het nu is.' : '<strong>1 storing · 1 beperkt · 1 onbekend</strong> · 3 gezond · 1 gepauzeerd · 1 nog niet beschikbaar. De totaalstatus is nooit beter dan het slechtste onderdeel; onbekend telt niet als gezond.'}</p>
  <ul class="divide-y divide-border border-y border-border">
    ${rij('Apps', 'storing', 'Storing', 'Voorbeeld-app start steeds opnieuw (crashloop). Automatisch herstel is gestopt.', 'problemen.html')}
    ${rij('Media', 'beperkt', 'Beperkt', 'MediaGuard antwoordt (HTTP 200), maar rondt geen taken af.')}
    ${rij('Huis', 'onbekend', 'Onbekend', 'my_house reageert niet sinds 10:12 — gegevens verouderd.', 'huis.html')}
    ${rij('Opslag', 'gezond', 'Gezond', 'voorbeeldpool ONLINE · scrub 3 dagen geleden zonder fouten.')}
    ${rij('Back-ups', 'gezond', 'Gezond', 'Hersteltest van foto én database geslaagd op 7 nov.')}
    ${rij('Meldingen', 'gezond', 'Gezond', 'Gotify bereikbaar · testmelding 11:30 afgeleverd.')}
    ${rij('GPU en AV1', 'gepauzeerd', 'Gepauzeerd', 'MediaGuard-noodstop sinds 09:04 (door Beheerder). Geen storing.')}
    ${rij('Netwerk', 'nogniet', 'Nog niet beschikbaar', 'Volgt in fase P5 (netwerk, persoonlijke AI en kosten).')}
  </ul>
</section>`;

  const actie = (soort, kop, tekst, knopHtml) => `<li class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center">
    <div class="flex min-w-0 flex-1 flex-col gap-1.5"><div class="flex flex-wrap items-center gap-2">${soort}<span class="font-semibold">${kop}</span></div><p class="text-sm text-muted-foreground">${tekst}</p></div>
    <div class="shrink-0">${knopHtml}</div></li>`;
  const acties = `
<section aria-labelledby="actie-titel" class="kaart">
  <h2 id="actie-titel" class="text-xl font-bold">Wat actie nodig heeft</h2>
  <p class="text-sm text-muted-foreground" id="offline-reden">${offline ? 'Acties die iets wijzigen staan uit tot de verbinding terug is. Er wordt niets in een wachtrij gezet.' : 'Volgorde: storing, goedkeuring, gate, onboarding.'}</p>
  <ol class="divide-y divide-border">
    ${actie(ernst('hoog'), 'Voorbeeld-app start steeds opnieuw', 'Automatisch herstel is gestopt na 2 pogingen. Eerste melding 10:02, laatste 11:54 (×100).', uit('Incident bekijken', 'inbox'))}
    ${actie(risico(2), 'Voorbeeld-app bijwerken naar 2.5.0', 'Aangevraagd door de AI · verloopt over <span class="cijfers">14:32</span>. Back-up wordt vooraf gemaakt.', uit('Voorstel beoordelen', 'clipboard-check'))}
    ${actie(`<span class="inline-flex items-center gap-1.5 rounded-sm border-2 border-gate bg-gate-bg px-2 py-0.5 text-sm font-semibold text-gate-ink" data-as="gate">${i('lock', 'size-4')}Gate dicht</span>`, 'Geblokkeerd door de DNS-gate', 'Nodig: terugvalroute voor DNS getest (D11). Dit is geen storing; er wacht een voorwaarde.', uit('Terugvalroute testen', 'list-checks'))}
    ${actie(`<span class="inline-flex items-center gap-1.5 rounded-sm border-2 border-border-strong px-2 py-0.5 text-sm font-semibold">${i('list-checks', 'size-4')}Onboarding</span>`, '12 besluiten nog open', '5 van 18 besluiten getest. Zonder besluiten blijven sommige functies dicht.', uit('Onboarding verder', 'chevron-right'))}
  </ol>
</section>`;

  const m = (bron, tijd, rel, poging) => meta({ bron, tijd: offline ? '11:52' : tijd, rel: offline ? 'stand bij het wegvallen van de verbinding' : rel, poging });
  // Offline: elke kaart is verouderd → gestippelde rand + waarde in het gearceerde vak (ONTWERPTAAL §4.4), niet alleen een badge.
  const vak = (html) => (offline ? html.replace(/<p><span class="waarde">([\s\S]*?)<\/p>/, '<div class="waardevak-verouderd"><p class="text-sm font-semibold text-foreground">Laatst bekend · 11:52</p><p><span class="waarde">$1<span class="sr-only"> (laatst bekende waarde, verouderd)</span></p></div>') : html);
  const kaarten0 = [
    kaart({ id: 'downloads', titel: 'Downloads en bibliotheek', ic: 'download', badge: st('gezond'),
      inhoud: `<p><span class="waarde">4</span> <span class="eenheid">${nb('downloads actief')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm">Bibliotheek: <strong>1.284</strong> titels · 3 verzoeken in behandeling.</p>`,
      metaHtml: m('MediaGuard', '11:55', '1 min geleden'), verder: vervolg('Downloads bekijken') }),
    kaart({ id: 'gpu', titel: 'GPU en AV1', ic: 'microchip', badge: st('gepauzeerd', 'Gepauzeerd'),
      inhoud: `<p class="text-sm">De AV1-wachtrij staat stil door de <strong>MediaGuard-noodstop</strong> (sinds 09:04, door Beheerder). Dit is een bewuste pauze, geen storing.</p>
      <p><span class="waarde">12</span> <span class="eenheid">${nb('items in de wachtrij')}</span> ${kwaliteit('gemeten')}</p>
      <div class="rounded-md border-2 border-dashed border-unknown bg-unknown-bg p-3 text-unknown-ink"><p class="flex flex-wrap items-center gap-2 font-semibold">${i('circle-help', 'size-5 text-unknown')}GPU-temperatuur: Onbekend</p><p class="mt-1 text-sm">Niet gemeten: Beszel levert geen temperatuur voor deze GPU. We tonen geen schatting en nooit 0&nbsp;°C.</p></div>`,
      metaHtml: m('MediaGuard (wachtrij), Beszel (GPU)', '11:55', '1 min geleden'), verder: vervolg('Werklast bekijken') }),
    kaart({ id: 'apps', titel: 'Apps en uptime', ic: 'layout-grid', badge: st('storing', 'Storing'),
      inhoud: `<p><span class="waarde">13 van 14</span> <span class="eenheid">${nb('apps gezond')}</span> ${kwaliteit('gemeten')}</p><p class="reden">Voorbeeld-app: start steeds opnieuw (crashloop).</p><p class="text-sm">Uptime afgelopen 30 dagen: <strong>99,2%</strong> ${kwaliteit('gemeten')}</p>`,
      metaHtml: m('TrueNAS-API, Uptime Kuma', '11:56', 'zojuist'), verder: vervolg('Apps bekijken', 'appdetail.html') }),
    kaart({ id: 'huis', titel: 'Huiscomfort en energie', ic: 'sofa', variant: 'kaart-verouderd', badge: `${status('onbekend', 'Onbekend')}${status('verouderd', 'Verouderd')}`,
      inhoud: `<div class="waardevak-verouderd"><p class="text-sm font-semibold text-foreground">Laatst bekend · 10:12</p><p><span class="waarde">20,5</span> <span class="eenheid">°C</span><span class="sr-only"> (laatst bekende waarde, verouderd)</span> <span class="text-sm text-muted-foreground">woonkamer</span></p></div>
      <p class="reden">my_house reageert niet sinds 10:12. Bediening staat uit tot de bron weer antwoordt.</p>
      <p class="text-sm">Energie vandaag: <strong>Onbekend</strong> — afgeleid van dezelfde bron, dus ook verouderd.</p>`,
      metaHtml: meta({ bron: 'my_house', tijd: '10:12', rel: '1 u 44 min geleden', poging: '11:56 (geen antwoord)' }), verder: vervolg('Huis openen', 'huis.html') }),
    kaart({ id: 'backups', titel: 'Veiligheid en back-ups', ic: 'database-backup', badge: st('gezond'),
      inhoud: `<p><span class="waarde">8 van 8</span> <span class="eenheid">${nb('datasets gedekt')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm">Laatste hersteltest: <strong>geslaagd</strong> op 7 nov (foto én database, checksums gelijk).</p>`,
      metaHtml: m('TrueNAS-snapshots, OneDrive-controle, hersteltest', '11:40', '16 min geleden'), verder: vervolg('Back-ups bekijken') }),
    kaart({ id: 'acties', titel: 'Nieuwste acties', ic: 'history',
      inhoud: `<ul class="flex flex-col divide-y divide-border">
        <li class="flex flex-col gap-1 py-2">${risico(1)}<span class="font-semibold">Voorbeeld-dienst herstarten</span><span class="text-sm">Uitgevoerd en gecontroleerd om 11:51 · gezond na 34&nbsp;s</span></li>
        <li class="flex flex-col gap-1 py-2">${risico(2)}<span class="font-semibold">Voorbeeld-app bijwerken naar 2.5.0</span><span class="text-sm">Wacht op goedkeuring · verloopt over <span class="cijfers">14:32</span></span></li>
        <li class="flex flex-col gap-1 py-2">${risico(1)}<span class="font-semibold">Snapshot voorbeeldpool/data</span><span class="text-sm">Mislukt om 08:00 · incident geopend</span></li></ul>`,
      metaHtml: m('Hub-audit', '11:51', '5 min geleden'), verder: vervolg('Audit bekijken') }),
    kaart({ id: 'onboarding', titel: 'Onboarding', ic: 'list-checks',
      inhoud: `<p><span class="waarde">5 van 18</span> <span class="eenheid">${nb('besluiten getest')}</span></p>
      <div class="h-3 overflow-hidden rounded-full bg-chart-meter-track" role="progressbar" aria-valuemin="0" aria-valuemax="18" aria-valuenow="5" aria-valuetext="5 van 18 besluiten getest" aria-label="Voortgang onboarding"><div class="h-full w-[28%] rounded-full bg-chart-1"></div></div>
      <p class="text-sm">12 open · 1 geblokkeerd (wacht op hersteltest D05).</p>`,
      metaHtml: m('Hub', '11:56', 'zojuist'), verder: offline ? `<div class="mt-auto flex flex-col gap-1"><button type="button" class="knop knop-secundair knop-blok" aria-disabled="true" aria-describedby="offline-reden"><span>Onboarding verder</span>${i('chevron-right')}</button><span class="text-sm text-muted-foreground">Uit: je bent offline</span></div>` : vervolg('Onboarding verder', 'wizardstap.html') }),
    offline ? kaart({ id: 'kosten', titel: 'Kosten', ic: 'wallet', variant: 'kaart-onbekend', badge: status('onbekend', 'Onbekend'),
      inhoud: `<p class="reden">Nog nooit opgehaald en je bent offline. We tonen geen schatting en geen 0.</p>`,
      metaHtml: `<dl class="meta"><dt>Bron</dt><dd>Hub (AI-tegoed, energietarief)</dd><dt>Bijgewerkt</dt><dd>nog nooit</dd><dt>Geprobeerd</dt><dd><time datetime="2026-11-09T11:52:00+01:00">11:52</time> (offline)</dd></dl>` }) :
    kaart({ id: 'kosten', titel: 'Kosten', ic: 'wallet', busy: true,
      inhoud: `<p class="sr-only">Laden…</p><div aria-hidden="true" class="flex flex-col gap-3"><div class="skelet h-9 w-32"></div><div class="skelet h-4 w-full"></div><div class="skelet h-4 w-2/3"></div></div><p class="text-sm text-muted-foreground">AI-tegoed en energiekosten ophalen… dit duurt langer dan verwacht.</p>`,
      metaHtml: `<dl class="meta"><dt>Bron</dt><dd>Hub (AI-tegoed, energietarief)</dd><dt>Bijgewerkt</dt><dd>nog niet — wordt opgehaald sinds <time datetime="2026-11-09T11:55:50+01:00">11:55</time></dd></dl>` }),
  ];

  const kaarten = offline ? kaarten0.map((h) => (/data-testid="kaart-(huis|kosten)"/.test(h) ? h : vak(h).replace('<article class="kaart ', '<article class="kaart kaart-verouderd '))) : kaarten0;
  const banner = offline ? `<div class="border-b-2 border-dashed border-unknown bg-unknown-bg px-4 py-3 text-unknown-ink lg:px-8" role="status"><p class="flex items-start gap-2 font-semibold">${i('wifi-off', 'mt-0.5 size-5 shrink-0 text-unknown')}<span>Je bent offline. Gegevens zijn niet actueel; acties zijn uitgeschakeld. Zodra de verbinding terug is, halen we alles opnieuw op.</span></p></div>` : '';
  const inhoud = paginakop({ titel: 'Home', bijgewerkt: offline ? 'Stand van 11:52 · niet actueel (offline)' : 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist) · vernieuwt elke 60 s',
    acties: offline ? `<button type="button" class="knop knop-secundair" aria-disabled="true" aria-describedby="offline-reden">${i('refresh-cw')}<span>Vernieuwen</span></button>` : knop('Vernieuwen', { ic: 'refresh-cw' }) })
    + `<div class="mb-6 grid gap-6 xl:grid-cols-2 xl:items-start">${systeem}${acties}</div>` + `<h2 class="sr-only">Overzicht</h2><div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">${kaarten.join('')}</div>`;
  return shell({ pagina: 'home', titel: offline ? 'Home (offline)' : 'Home', inhoud, banner, live: offline ? 'offline' : 'aan' });
}
