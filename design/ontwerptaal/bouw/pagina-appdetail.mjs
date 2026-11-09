// S-041…S-045 Appdetail met vijf tabs + S-061 Actie-preview (R2) en Metrieken met grafiek. Alle data fictief.
import { i, status, risico, validatie, kwaliteit, knop, deeplink, kopieer, shell, paginakop, kruimel, tabs, tabpaneel, lijngrafiek, meter, melding, meta, nb } from './ui.mjs';

const diffRij = (teken, soort, veld, was, wordt) => `<div role="row" class="grid gap-2 border-b border-border py-2.5 md:grid-cols-[2rem_12rem_minmax(0,1fr)_minmax(0,1fr)] md:items-center">
  <span role="cell" class="flex items-center gap-2"><span class="diff-teken" aria-hidden="true">${teken}</span><span class="sr-only">${soort}</span><span class="font-mono text-sm font-semibold md:hidden">${veld}</span></span>
  <span role="cell" class="hidden font-mono text-sm font-semibold md:block">${veld}</span>
  <span role="cell" class="flex flex-wrap items-baseline gap-2"><span class="text-sm text-muted-foreground md:sr-only">Was</span>${was ? `<span class="diff-was break-all">${was}</span>` : '<span class="text-sm text-muted-foreground">(nieuw)</span>'}</span>
  <span role="cell" class="flex flex-wrap items-baseline gap-2"><span class="text-sm text-muted-foreground md:sr-only">Wordt</span>${wordt ? `<span class="diff-wordt break-all">${wordt}</span>` : '<span class="text-sm text-muted-foreground">(verwijderd)</span>'}</span>
</div>`;

const preview = `
<section aria-labelledby="pv-titel" class="kaart gap-5 border-2 border-risk-2" data-testid="actie-preview">
  <div class="flex flex-col gap-2">
    <p class="text-sm font-semibold text-muted-foreground">Voorstel · <code class="code-inline">app.update</code> · aangevraagd door ${'<span class="inline-flex items-center gap-1 font-semibold text-foreground">' + i('bot', 'size-4') + 'AI</span>'}</p>
    <h3 id="pv-titel" class="text-xl font-bold">Voorbeeld-app bijwerken naar 2.5.0</h3>
    <div class="flex flex-wrap items-center gap-2">${risico(2)}<span class="text-sm">Preview geldig tot <time datetime="2026-11-09T12:13:00+01:00">12:13</time> (nog <span class="cijfers font-semibold">14:32</span>)</span></div>
  </div>
  <details class="rounded-lg border border-border-strong">
    <summary class="flex min-h-touch cursor-pointer items-center gap-2 px-3 font-semibold">${i('info')}Waarom R2?</summary>
    <div class="border-t border-border p-3 text-sm"><p>Beleidsregel <code class="code-inline">app.update.default</code> (beleid 1.0, <code class="code-inline">policy_hash 3f9a…c21e</code>) zet elke update op R2: de app is tijdelijk onbereikbaar en een migratie kan data raken.</p><p class="mt-2"><strong>AI stelde R1 voor; het beleid bepaalt R2.</strong> De claim van de AI telt niet mee.</p></div>
  </details>

  <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
    <div class="flex min-w-0 flex-col gap-5">
      <section aria-labelledby="pv-sam" class="flex flex-col gap-2">
        <h4 id="pv-sam" class="font-bold">Samenvatting</h4>
        <dl class="grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
          <dt class="font-semibold text-muted-foreground">Doel</dt><dd>Voorbeeld-app op <span class="font-mono">nas-primair</span> ${'<span class="voorbeeld">Voorbeeld</span>'}</dd>
          <dt class="font-semibold text-muted-foreground">Uitvoerder</dt><dd class="flex flex-wrap items-center gap-2">Executor 0.1.0 ${validatie('NIET GEVALIDEERD (echte NAS)')}</dd>
          <dt class="font-semibold text-muted-foreground">Reikwijdte</dt><dd>Alleen Voorbeeld-app. Geen andere apps hangen ervan af.</dd>
          <dt class="font-semibold text-muted-foreground">Onderbreking</dt><dd>≈&nbsp;30&nbsp;s ${kwaliteit('geschat')}</dd>
          <dt class="font-semibold text-muted-foreground">Verantwoordelijke</dt><dd>Beheerder (goedkeuring per gebonden diff)</dd>
        </dl>
      </section>
      <section aria-labelledby="pv-diff" class="flex min-w-0 flex-col gap-2">
        <h4 id="pv-diff" class="font-bold">Wat verandert er</h4>
        <p class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground"><span><span class="diff-teken mr-1" aria-hidden="true">~</span>gewijzigd</span><span><span class="diff-teken mr-1" aria-hidden="true">+</span>toegevoegd</span><span><span class="diff-teken mr-1" aria-hidden="true">−</span>verwijderd</span></p>
        <div role="table" aria-label="Wijzigingen in de app-instellingen" class="border-t border-border-strong">
          <div role="row" class="hidden border-b border-border-strong py-2 text-sm font-semibold md:grid md:grid-cols-[2rem_12rem_minmax(0,1fr)_minmax(0,1fr)]"><span role="columnheader"><span class="sr-only">Soort</span></span><span role="columnheader">Veld</span><span role="columnheader">Was</span><span role="columnheader">Wordt</span></div>
          ${diffRij('~', 'Gewijzigd', 'image.tag', '2.4.1', '2.5.0')}
          ${diffRij('~', 'Gewijzigd', 'image.digest', 'sha256:91c4…7d02', 'sha256:5be8…a913')}
          ${diffRij('+', 'Toegevoegd', 'env.VOORBEELD_MODUS', '', 'stil')}
          ${diffRij('−', 'Verwijderd', 'env.OUDE_OPTIE', 'aan', '')}
        </div>
      </section>
      <section aria-labelledby="pv-stappen" class="flex flex-col gap-2">
        <h4 id="pv-stappen" class="font-bold">Zo verloopt het</h4>
        <ol class="flex flex-wrap items-center gap-x-2 gap-y-2 text-sm font-semibold" aria-label="Stappen van de uitvoering">
          ${['Back-up', 'Bijwerken', 'Controle na uitvoering', 'Klaar of incident'].map((s, k, a) => `<li class="flex items-center gap-2"><span class="stap-bol" aria-hidden="true">${k + 1}</span>${s}${k < a.length - 1 ? i('arrow-right', 'size-4 text-muted-foreground') : ''}</li>`).join('')}
        </ol>
        <p class="text-sm text-muted-foreground">Pas na de controle (readback) staat er <strong>Uitgevoerd en gecontroleerd</strong>. "Verstuurd" is nog niet klaar.</p>
      </section>
    </div>
    <aside aria-label="Veiligheid van dit voorstel" class="flex flex-col gap-3 rounded-lg bg-muted p-4 text-sm">
      <div><p class="flex items-center gap-2 font-bold">${i('database-backup')}Back-up vereist</p><p class="mt-1">Vóór uitvoering wordt snapshot <span class="font-mono">voorbeeldpool/apps/voorbeeld-app</span> gemaakt. Het herstelpunt-ID komt in de audit.</p></div>
      <div><p class="flex items-center gap-2 font-bold">${i('rotate-ccw')}Terugzetten</p><p class="mt-1">Naar 2.4.1 met dezelfde instellingen. Alleen-tag terugzetten is veilig: geen databasemigratie.</p></div>
      <div><p class="flex items-center gap-2 font-bold">${i('list-checks')}Controle na uitvoering</p><p class="mt-1">Gezond binnen 120&nbsp;s én digest gelijk aan <span class="font-mono">sha256:5be8…a913</span>. Wijkt iets af: gestopt + incident.</p></div>
      <div><p class="flex items-center gap-2 font-bold">${i('lock')}Gebonden aan deze preview</p><p class="mt-1">preview_hash, resource_etag en policy_hash. Verandert er één vóór uitvoering, dan vervalt dit voorstel en vraag je een nieuw aan.</p></div>
    </aside>
  </div>
  <div class="flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:justify-end">
    ${knop('Annuleren', { soort: 'stil' })}${knop('Simuleren (droogtest)', { ic: 'flask-conical' })}${knop('Goedkeuring aanvragen', { soort: 'primair', ic: 'clipboard-check' })}
  </div>
</section>`;

const actieRij = (code, titel, r, wat, extra = '') => `<li class="flex flex-col gap-2 border-b border-border py-3 md:flex-row md:items-center md:gap-4">
  <div class="flex min-w-0 flex-1 flex-col gap-1.5"><div class="flex flex-wrap items-center gap-2">${risico(r)}<span class="font-semibold">${titel}</span></div><p class="text-sm text-muted-foreground"><code class="code-inline text-foreground">${code}</code> · ${wat}</p>${extra}</div>
  <div class="shrink-0">${extra.includes('Geblokkeerd') ? `<button type="button" class="knop knop-secundair w-full md:w-auto" aria-disabled="true">${i('lock')}<span>Geblokkeerd</span><span class="sr-only">: ${titel}</span></button>` : knop('Bekijk voorstel', { ic: 'file-diff', extra: 'w-full md:w-auto', attrs: `aria-label="Bekijk voorstel: ${titel}"` })}</div>
</li>`;

const acties = `
<div class="flex flex-col gap-5">
  <section aria-labelledby="acties-lijst" class="kaart">
    <h2 id="acties-lijst" class="text-lg font-bold">Toegestane acties</h2>
    <p class="text-sm text-muted-foreground">Elke actie opent eerst een voorstel met preview, risico, back-up en controle na uitvoering. Wie mag goedkeuren, bepaalt de server.</p>
    <ul>
      ${actieRij('app.restart', 'Herstarten', 1, 'onderbreking ≈ 30 s · geen back-up nodig')}
      ${actieRij('app.stop', 'Stoppen', 1, 'app blijft uit tot je hem start')}
      ${actieRij('app.update', 'Bijwerken naar 2.5.0', 2, 'back-up vooraf · onderbreking ≈ 30 s', '<p class="text-sm font-semibold">Voorstel staat hieronder open.</p>')}
      ${actieRij('app.rollback', 'Terugzetten naar 2.3.0', 2, 'herstelplan nodig', `<p class="flex items-start gap-1.5 text-sm text-gate-ink">${i('lock', 'mt-0.5 size-4 shrink-0 text-gate')}<span><strong>Geblokkeerd:</strong> 2.3.0 gebruikt een ouder databaseschema. Alleen-tag terugzetten kan niet; gebruik het volledige herstelplan (dataset + database).</span></p>`)}
      ${actieRij('app.uninstall', 'Verwijderen (container)', 2, 'data blijft bewaard op de dataset')}
    </ul>
    <p class="flex items-start gap-2 pt-3 text-sm">${i('ban', 'mt-0.5 size-4 shrink-0 text-gate')}<span><strong>Data verwijderen (R3)</strong> staat hier bewust niet. Dat is een aparte flow met een eigen bevestiging en wordt nooit door de AI aangeboden.</span></p>
  </section>
  ${preview}
</div>`;

const punten = (() => {
  const t = []; const v = [380, 386, 391, 395, 402, 410, 418, 425, 431, 440, 452, 461, 470, null, null, null, 482, 488, 494, 498, 503, 507, 505, 498];
  for (let k = 0; k < v.length; k++) { const m = 6 * 60 + k * 15; t.push({ t: `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`, v: v[k] }); }
  return t;
})();

const metrieken = `
<div class="flex flex-col gap-5">
  <h2 class="sr-only">Metrieken</h2>
  <div class="flex flex-wrap items-center gap-2" role="group" aria-label="Periode">
    <span class="mr-1 text-sm font-semibold">Periode</span>
    ${['1 u', '6 u', '24 u', '7 d', '30 d'].map((p) => `<button type="button" class="knop ${p === '6 u' ? 'knop-primair' : 'knop-secundair'} knop-klein" aria-pressed="${p === '6 u'}">${nb(p)}</button>`).join('')}
  </div>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <article class="kaart" aria-labelledby="t-cpu"><h3 id="t-cpu" class="kaart-titel">${i('cpu')}CPU</h3><p><span class="waarde">12</span> <span class="eenheid">%</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">gemiddeld, afgelopen 6 u</p>${meta({ bron: 'Beszel', tijd: '11:55', rel: '1 min geleden' })}</article>
    <article class="kaart" aria-labelledby="t-mem"><h3 id="t-mem" class="kaart-titel">${i('memory-stick')}Geheugen</h3>${meter({ label: 'Gebruik nu', waarde: 498, max: 512, eenheid: 'MiB' })}${meta({ bron: 'Beszel', tijd: '11:55', rel: '1 min geleden' })}</article>
    <article class="kaart kaart-onbekend" aria-labelledby="t-gpu" data-testid="capability-unavailable"><h3 id="t-gpu" class="kaart-titel">${i('microchip')}GPU per app</h3>${status('nietbeschikbaar', 'Niet beschikbaar')}<p class="reden">Beszel levert geen GPU-gebruik per app. We tonen geen schatting.</p><p class="text-sm"><code class="code-inline">capability_unavailable</code> · bron Beszel · <span class="font-mono">/api/systems</span></p></article>
    <article class="kaart" aria-labelledby="t-herstart"><h3 id="t-herstart" class="kaart-titel">${i('rotate-ccw')}Herstarts</h3><p><span class="waarde">2</span> <span class="eenheid">${nb('in 6 u')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">beide automatisch (R1), daarna gestopt</p>${meta({ bron: 'TrueNAS-API', tijd: '11:56', rel: 'zojuist' })}</article>
  </div>
  ${lijngrafiek({ id: 'g-geheugen', titel: 'Geheugengebruik', beschrijving: 'Afgelopen 6 u, per kwartier. Stijgt van 380 naar ongeveer 505 MiB, vlak onder de limiet van 512 MiB. Tussen 09:15 en 09:45 was er geen meting.', punten, ymax: 600, ystap: 100, eenheid: 'MiB', grens: { v: 512, label: 'Limiet 512 MiB' }, bron: 'Beszel', bijgewerkt: '11:55', reeksnaam: 'Geheugen' })}
</div>`;

const statusTab = `
<section aria-labelledby="checks" class="kaart">
  <h2 id="checks" class="text-lg font-bold">Controles</h2>
  <ul class="divide-y divide-border">
    ${[['Proces', 'storing', 'Storing', 'Stopt na ±6 min met "out of memory".'], ['Gezondheidscontrole', 'storing', 'Storing', 'Geen antwoord sinds 11:54.'], ['Opslag /appdata', 'gezond', 'Gezond', 'voorbeeldpool/apps/voorbeeld-app bereikbaar.'], ['Inlog-credential', 'onbekend', 'Onbekend', 'Niet gecontroleerd: app reageert niet.']]
      .map(([n, s, l, r]) => `<li class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5"><span class="mr-auto font-semibold sm:mr-0 sm:w-40">${n}</span>${status(s, l)}<span class="reden basis-full sm:basis-auto">${r}</span></li>`).join('')}
  </ul>
</section>`;

export function appdetail(actief = 'acties') {
  const kop = paginakop({
    kruimel: kruimel([['Server', '#'], ['Apps', '#'], ['Voorbeeld-app', '']]),
    titel: 'Voorbeeld-app',
    omschrijving: 'Geïmporteerd · eigenaar: TrueNAS-catalogus · versie 2.4.1',
    acties: deeplink('Voorbeeld-app'),
  });
  const kopStatus = `<div class="kaart mb-6 gap-4">
    <div class="flex flex-wrap items-center gap-3">${status('storing', 'Storing', 'status-groot')}<p class="min-w-0 flex-1 basis-60">Start steeds opnieuw (crashloop). Automatisch herstel is gestopt na 2 pogingen. <a href="problemen.html">Incident bekijken</a></p></div>
    <div class="grid gap-4 md:grid-cols-2">${kopieer('Image-digest', 'sha256:91c4e07b2f6a8d13c5e9b40a7f21d6c83e5b9a0f4d7c2e1b8a63f50d9e47d02')}${meta({ bron: 'TrueNAS-API (app.query), Uptime Kuma', tijd: '11:56', rel: 'zojuist', extra: [['Uptime 30 d', '99,2% · gemeten'], ['Data-dataset', '<span class="font-mono">voorbeeldpool/apps/voorbeeld-app</span>']] })}</div>
  </div>`;
  const T = [['status', 'Status', 'activity'], ['metrieken', 'Metrieken', 'chart-line'], ['logs', 'Logs', 'scroll-text'], ['versies', 'Versies', 'tag'], ['acties', 'Acties', 'list-checks']];
  const inhoud = kop + kopStatus + tabs('app', T, actief)
    + tabpaneel('app', 'status', actief, statusTab)
    + tabpaneel('app', 'metrieken', actief, metrieken)
    + tabpaneel('app', 'logs', actief, `<div class="kaart"><h2 class="text-lg font-bold">Logs</h2><pre class="overflow-x-auto rounded-md bg-muted p-3 font-mono text-sm">11:54:02 INFO  start\n11:54:40 WARN  geheugen 498 MiB\n11:55:01 FATAL out of memory</pre><p class="text-sm text-muted-foreground">Geschoond: geheimen en tokens zijn verwijderd.</p></div>`)
    + tabpaneel('app', 'versies', actief, `<div class="kaart"><h2 class="text-lg font-bold">Versies</h2><p>Huidig 2.4.1 · beschikbaar 2.5.0 (geen schemawijziging).</p></div>`)
    + tabpaneel('app', 'acties', actief, acties);
  return shell({ pagina: 'apps', zijHuidig: 'server', titel: `Voorbeeld-app — ${actief === 'acties' ? 'acties' : 'metrieken'}`, inhoud });
}
