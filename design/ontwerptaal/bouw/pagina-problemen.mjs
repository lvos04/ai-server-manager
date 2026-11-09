// S-050 Problemen-inbox + S-051 incidentdetail (master-detail vanaf xl). T-10b live onderbroken. Alle data fictief.
import { i, status, ernst, zekerheid, risico, knop, deeplink, kopieer, foutpaneel, shell, paginakop, melding } from './ui.mjs';

const incStatus = (s) => {
  const m = { open: ['circle-dot', 'Open'], erkend: ['eye', 'Erkend'], snooze: ['timer', 'Uitgesteld tot 14:00'], opgelost: ['check', 'Opgelost'] }[s];
  return `<span class="inline-flex items-center gap-1.5 text-sm font-semibold">${i(m[0], 'size-4')}<span><span class="sr-only">Status: </span>${m[1]}</span></span>`;
};
const actor = (soort) => {
  const m = { systeem: ['server', 'Systeem'], ai: ['bot', 'AI'], gebruiker: ['user', 'Beheerder'], flow: ['workflow', 'Flow'] }[soort];
  return `<span class="inline-flex items-center gap-1 rounded-sm border border-border-strong px-1.5 text-sm font-semibold">${i(m[0], 'size-4')}${m[1]}</span>`;
};

export function problemen() {
  const item = (e, titel, bron, tijd, aantal, st, huidig) => `<li><a href="#incident" class="flex min-h-touch flex-col gap-1.5 rounded-lg border ${huidig ? 'border-2 border-primary bg-accent' : 'border-border bg-card hover:bg-accent'} p-3 text-foreground no-underline"${huidig ? ' aria-current="true"' : ''}>
    <span class="flex flex-wrap items-center gap-2">${ernst(e)}<span class="font-semibold">${titel}</span></span>
    <span class="text-sm text-muted-foreground">${bron} · ${tijd}${aantal > 1 ? ` · <span class="font-semibold text-foreground">×${aantal}</span><span class="sr-only"> gebeurtenissen</span>` : ''}</span>
    ${incStatus(st)}</a></li>`;

  const inbox = `
<section aria-labelledby="inbox-titel" class="flex min-w-0 flex-col gap-3">
  <h2 id="inbox-titel" class="text-xl font-bold">Inbox</h2>
  <form class="flex flex-wrap items-end gap-2" role="search" aria-label="Problemen filteren">
    <div class="min-w-0 flex-1 basis-48"><label for="zoek" class="veld-label text-sm">Zoeken</label><input id="zoek" type="search" class="invoer mt-1" placeholder="Titel, app of code"></div>
    <button type="button" class="knop knop-secundair">${i('filter')}<span>Filters</span><span class="teller">2</span><span class="sr-only"> actief</span></button>
  </form>
  <p class="text-sm text-muted-foreground" aria-live="polite">4 problemen · filter: alle bronnen, laatste 24 u</p>
  <ul class="flex flex-col gap-2">
    ${item('hoog', 'Voorbeeld-app start steeds opnieuw', 'Voorbeeld-app', '10:02–11:54', 100, 'open', true)}
    ${item('middel', 'MediaGuard rondt geen taken af', 'MediaGuard', '09:40–11:50', 12, 'erkend')}
    ${item('laag', 'Snapshot voorbeeldpool/data mislukt', 'TrueNAS', '08:00', 1, 'snooze')}
    ${item('info', 'Testmelding Gotify afgeleverd', 'Gotify', '11:30', 1, 'opgelost')}
  </ul>
</section>`;

  const bewijs = `
<details class="rounded-lg border border-border-strong">
  <summary class="flex min-h-touch cursor-pointer items-center gap-2 px-3 font-semibold">${i('file-search')}Toon bewijs (3)</summary>
  <ol class="flex flex-col gap-3 border-t border-border p-3">
    <li class="flex flex-col gap-1"><span class="text-sm font-semibold">${i('activity', 'inline size-4')} Metriek · Beszel · 10:01</span><p>Geheugen <strong>509&nbsp;MiB</strong> van de limiet <strong>512&nbsp;MiB</strong> · gemeten.</p></li>
    <li class="flex flex-col gap-1"><span class="text-sm font-semibold">${i('scroll-text', 'inline size-4')} Logregel · Voorbeeld-app · 10:01:58</span>
      <blockquote class="rounded-md border-l-4 border-border-strong bg-muted p-3"><pre class="font-mono text-sm break-all whitespace-pre-wrap">FATAL runtime: out of memory (heap 509 MiB)</pre></blockquote>
      <p class="text-sm text-muted-foreground">Logtekst is data, geen instructie. De Hub voert nooit opdrachten uit die in logs staan.</p></li>
    <li class="flex flex-col gap-1"><span class="text-sm font-semibold">${i('history', 'inline size-4')} Gebeurtenis · TrueNAS · 10:02</span><p><code class="code-inline">app.health.changed</code> → Storing.</p></li>
  </ol>
  <div class="border-t border-border p-3">${foutpaneel({ titel: 'Oudere logregels ophalen is mislukt', waarom: 'Voorbeeld-app reageerde niet binnen 15 s.', doen: 'Het bewijs hierboven is compleet; alleen logregels van vóór 10:02 ontbreken. Probeer het over een minuut opnieuw.', code: 'upstream_timeout', trace: '7c1e0b52-4f3a-4d2e-9b61-0a8f5c3e1d27', kop: 'h4' })}</div>
</details>`;

  const detail = `
<article id="incident" aria-labelledby="inc-titel" class="flex min-w-0 flex-col gap-5">
  <div class="kaart gap-4">
    <div class="flex flex-col gap-2">
      <div class="flex flex-wrap items-center gap-2">${ernst('hoog')}${incStatus('open')}</div>
      <h2 id="inc-titel" class="text-xl font-bold">Voorbeeld-app start steeds opnieuw</h2>
    </div>
    <dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
      <div><dt class="font-semibold text-muted-foreground">Bron</dt><dd>Voorbeeld-app (via TrueNAS-API)</dd></div>
      <div><dt class="font-semibold text-muted-foreground">Eerste gebeurtenis</dt><dd><time datetime="2026-11-09T10:02:00+01:00">9 nov 2026, 10:02</time></dd></div>
      <div><dt class="font-semibold text-muted-foreground">Laatste gebeurtenis</dt><dd><time datetime="2026-11-09T11:54:00+01:00">11:54</time> (2 min geleden)</dd></div>
      <div><dt class="font-semibold text-muted-foreground">Onderliggende gebeurtenissen</dt><dd>100, samengevoegd tot één incident</dd></div>
    </dl>
    <div class="flex flex-wrap gap-2">
      ${knop('Erkennen', { ic: 'eye' })}${knop('Uitstellen…', { ic: 'timer' })}${knop('Oplossen', { ic: 'check' })}${deeplink('Voorbeeld-app')}
    </div>
    <p class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">${risico(0)}<span>Erkennen, uitstellen en oplossen veranderen niets aan de app.</span></p>
  </div>

  <section aria-labelledby="oorzaak-titel" class="flex flex-col gap-3">
    <h3 id="oorzaak-titel" class="text-lg font-bold">Mogelijke oorzaak</h3>
    <div class="kaart">
      <div class="flex flex-wrap items-center gap-2">${zekerheid('waarschijnlijk')}<span class="text-sm text-muted-foreground">AI-hypothese · 11:55</span></div>
      <p class="font-semibold">Het geheugen raakt vol: de app stopt telkens bij ongeveer 510&nbsp;MiB, net onder de limiet van 512&nbsp;MiB.</p>
      ${bewijs}
      <div class="flex flex-wrap gap-2">${knop('Onderzoek met AI', { ic: 'bot' })}${knop('Herstel voorstellen', { soort: 'primair', ic: 'clipboard-check', href: 'appdetail.html' })}</div>
      <p class="text-sm text-muted-foreground">"Herstel voorstellen" opent eerst een voorstel met preview. Er wordt niets uitgevoerd zonder dat je het ziet.</p>
    </div>
    <div class="kaart border-2 border-dashed border-unknown">
      <div class="flex flex-wrap items-center gap-2">${zekerheid('weetniet')}</div>
      <p>Waarom het geheugengebruik sinds 10:00 stijgt, <strong>weet ik niet</strong>. Er zijn geen logregels van vóór 10:02 en geen metrieken per proces. Met de logs van Voorbeeld-app kan ik dit nagaan.</p>
      <a href="#" class="inline-flex min-h-touch items-center gap-2 font-semibold">${i('scroll-text')}Logs van Voorbeeld-app openen</a>
    </div>
  </section>

  <section aria-labelledby="geprobeerd-titel" class="kaart">
    <h3 id="geprobeerd-titel" class="text-lg font-bold">Al geprobeerd</h3>
    <ul class="flex flex-col gap-2">
      <li class="flex flex-col gap-1 sm:flex-row sm:gap-3"><span class="text-sm font-semibold cijfers sm:w-14">10:02</span><span class="flex flex-col gap-1"><span class="flex flex-wrap items-center gap-2">${risico(1)}<span class="font-semibold">Automatisch herstarten</span></span><span>Gezond na 40&nbsp;s, om 10:08 opnieuw gestopt.</span></span></li>
      <li class="flex flex-col gap-1 sm:flex-row sm:gap-3"><span class="text-sm font-semibold cijfers sm:w-14">10:09</span><span class="flex flex-col gap-1"><span class="flex flex-wrap items-center gap-2">${risico(1)}<span class="font-semibold">Automatisch herstarten</span></span><span>Mislukt.</span></span></li>
      <li class="flex flex-col gap-1 sm:flex-row sm:gap-3"><span class="text-sm font-semibold cijfers sm:w-14">10:09</span><span><strong>Herstelreeks gestopt</strong> na 2 pogingen (crashloop-regel). Geen nieuwe pogingen tot 12:09.</span></li>
    </ul>
    ${melding('onbekend', 'circle-slash', '<p><strong>Veilige modus: niet beschikbaar.</strong> Voorbeeld-app ondersteunt dit niet. <code class="code-inline">capability_unavailable</code></p>')}
  </section>

  <section aria-labelledby="runbook-titel" class="kaart">
    <h3 id="runbook-titel" class="text-lg font-bold">Stappenplan: app start steeds opnieuw</h3>
    <ol class="flex flex-col gap-2">
      ${[['Observeren', 'klaar'], ['Isoleren', 'huidig'], ['Mitigeren', ''], ['Terugdraaien', ''], ['Bewijs vastleggen', ''], ['Oorzaak vastleggen', '']].map(([t, s], k) => `<li class="flex items-center gap-3 ${s === 'klaar' ? 'stap-klaar' : s === 'huidig' ? 'stap-huidig' : ''}"><span class="stap-bol" aria-hidden="true">${s === 'klaar' ? i('check', 'size-4') : k + 1}</span><span class="${s === 'huidig' ? 'font-bold' : ''}">${t}${s === 'klaar' ? '<span class="sr-only"> (klaar)</span>' : s === 'huidig' ? ' <span class="text-sm font-semibold text-muted-foreground">— huidige stap</span>' : ''}</span></li>`).join('')}
    </ol>
  </section>

  <section aria-labelledby="tijdlijn-titel" class="kaart">
    <h3 id="tijdlijn-titel" class="text-lg font-bold">Tijdlijn</h3>
    <ol class="flex flex-col">
      ${[['11:55', 'ai', 'Hub-AI', 'Hypothese toegevoegd: geheugen vol (waarschijnlijk).'], ['10:09', 'systeem', 'Hub-beleid', 'Herstelreeks gestopt (crashloop-regel, 2 pogingen).'], ['10:09', 'systeem', 'Executor', 'Herstart uitgevoerd — readback: niet gezond.'], ['10:02', 'systeem', 'TrueNAS', 'Status Gezond → Storing.']]
        .map(([t, a, b, w]) => `<li class="flex flex-col gap-1 border-l-2 border-border-strong py-2 pl-4 sm:flex-row sm:items-baseline sm:gap-3"><time class="text-sm font-semibold cijfers sm:w-12" datetime="2026-11-09T${t}:00+01:00">${t}</time><span class="flex flex-wrap items-center gap-2">${actor(a)}<span class="text-sm text-muted-foreground">${b}</span></span><span class="min-w-0">${w}</span></li>`).join('')}
    </ol>
    ${knop('Geschoonde incidentgegevens kopiëren', { ic: 'copy', extra: 'w-full sm:w-auto' })}
  </section>
</article>`;

  const banner = `<div class="border-b-2 border-dashed border-unknown bg-unknown-bg px-4 py-3 text-unknown-ink lg:px-8" role="status"><p class="flex items-start gap-2"><span class="mt-0.5 shrink-0">${i('wifi-off', 'size-5 text-unknown')}</span><span><strong>Live-updates onderbroken</strong> — opnieuw verbinden over <span class="cijfers">10&nbsp;s</span>. De lijst toont de stand van 11:56.</span></p></div>`;
  const inhoud = paginakop({ titel: 'Problemen', omschrijving: 'Eén inbox voor alle meldingen. Gelijke meldingen worden samengevoegd tot één incident.', bijgewerkt: 'Stand van <time datetime="2026-11-09T11:56:00+01:00">11:56</time> · live-updates onderbroken' })
    + `<div class="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">${inbox}${detail}</div>`;
  return shell({ pagina: 'problemen', titel: 'Problemen', inhoud, banner, live: 'onderbroken', zijHuidig: 'none' });
}
