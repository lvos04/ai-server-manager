// S-166 Diensten + S-014 Dienst koppelen (contract 1.2 H5, §3.2–§3.8, §4.5). Alle data fictief.
// Nieuw in de Hub-ontwerpstap P1: KoppelcodeKaart (C-40a), DienstKaart (C-41a), SleutelsetPaneel (C-57); COMPONENTEN.md §27.
import { i, status, knop, kopieer, foutpaneel, melding, shell, paginakop, kruimel, voorbeeld } from './ui.mjs';

const pil = (soort, ic, tekst) => `<span class="status status-${soort}">${i(ic)}<span>${tekst}</span></span>`;
const tijd = (hhmm, rel, iso = `2026-11-09T${hhmm}:00+01:00`) => `<time datetime="${iso}">${hhmm}</time>${rel ? ` (${rel})` : ''}`;

// DienstKaart (C-41): koppelstatus is neutraal (verbonden is geen gezondheid); gezondheid staat in Apps.
const dienst = ({ id, naam, appId, pillen, feiten, extra = '', acties }) => `
<article class="kaart" aria-labelledby="d-${id}" data-testid="dienst-${appId}">
  <div class="flex flex-col gap-2">
    <h3 id="d-${id}" class="kaart-titel">${i('package')}${naam}</h3>
    <div class="flex flex-wrap gap-2">${pillen}</div>
  </div>
  <dl class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
    <dt class="font-semibold text-muted-foreground">App-id</dt><dd class="font-mono break-all">${appId}</dd>
    ${feiten.map(([a, b]) => `<dt class="font-semibold text-muted-foreground">${a}</dt><dd class="min-w-0">${b}</dd>`).join('')}
  </dl>
  ${extra}
  <div class="mt-auto flex flex-col gap-2 sm:flex-row sm:flex-wrap">${acties}</div>
</article>`;

const actie = (label, ic, naam) => knop(label, { ic, extra: 'w-full sm:w-auto', attrs: `aria-label="${label}: ${naam}"` });

export function diensten() {
  const vingerafdruk = '7QK2-M4XD-9HCR-T1VB';

  const sleutelset = `
<section aria-labelledby="va-titel" class="kaart gap-4">
  <h2 id="va-titel" class="flex items-center gap-2 text-xl font-bold">${i('fingerprint-pattern')}Vingerafdruk van deze Hub</h2>
  <p class="max-w-prose">Een dienst toont na het koppelen de vingerafdruk van de Hub waarmee hij gekoppeld is. Komt die niet overeen met deze, koppel dan niet en trek de dienst in.</p>
  ${kopieer('Vingerafdruk van de Hub-sleutelset', vingerafdruk)}
  <details class="rounded-lg border border-border-strong">
    <summary class="flex min-h-touch cursor-pointer items-center gap-2 px-3 font-semibold">${i('chevron-down', 'size-5 klap-icoon')}Publieke sleutelset voor bestaande apps</summary>
    <div class="flex flex-col gap-3 border-t border-border p-3">
      <p class="text-sm">Voor MediaGuard, MSO en my_house: plak deze sleutelset in hun instellingen (contract §2.3). Het zijn alleen <strong>publieke</strong> sleutels; er staat geen geheim in.</p>
      ${kopieer('Sleutelset (jwks en policy-sleutel, JSON)', '{"jwks":{"keys":[{"kty":"OKP","crv":"Ed25519","x":"vb3Lr0…voorbeeld","kid":"b41c…"}]},"policy_public_key":{"kty":"OKP","crv":"Ed25519","x":"Qm8x…voorbeeld","kid":"77ad…"},"keyset_fingerprint":"' + vingerafdruk + '"}')}
    </div>
  </details>
</section>`;

  const koppelen = `
<section aria-labelledby="koppel-titel" id="koppelen" class="kaart gap-5" data-testid="dienst-koppelen">
  <h2 id="koppel-titel" class="flex items-center gap-2 text-xl font-bold">${i('link-2')}Dienst koppelen</h2>
  <form class="flex flex-col gap-4" aria-labelledby="koppel-titel">
    <div class="flex flex-col gap-1.5">
      <label for="dienst-kies" class="veld-label">Welke dienst?</label>
      <p id="dienst-hulp" class="veld-hulp">Alleen eigen diensten van het platform. De executor koppel je via Onboarding → Executor (koppelcode 30 minuten).</p>
      <select id="dienst-kies" class="invoer max-w-80" aria-describedby="dienst-hulp"><option>appstore-en-fork</option><option>home-control-hub</option><option>jelly-leon-platform</option><option>zoeken-en-persoonlijke-ai</option></select>
    </div>
    <fieldset class="flex flex-col gap-2">
      <legend class="veld-label mb-1">Hoe koppel je? <span class="font-normal text-muted-foreground">(verplicht)</span></legend>
      <label class="keuze"><input type="radio" name="wijze"><span class="min-w-0"><span class="block font-semibold">Enrollment-token in het Custom App-formulier (aanbevolen)</span><span class="text-sm">Je vult drie omgevingsvariabelen in bij de app in TrueNAS. Niemand anders kan ertussen komen.</span></span></label>
      <label class="keuze"><input type="radio" name="wijze" checked><span class="min-w-0"><span class="block font-semibold">Koppelcode op de statuspagina van de dienst</span><span class="text-sm">Voor een dienst die al draait. Je vult de code en de vingerafdruk in op de statuspagina.</span></span></label>
    </fieldset>
    <div>${knop('Koppelcode maken', { soort: 'primair', ic: 'key-round', extra: 'w-full sm:w-auto' })}</div>
  </form>

  <div class="flex flex-col gap-4 rounded-lg border-2 border-border-strong p-4" data-testid="koppelcode">
    <div class="flex flex-col gap-1">
      <h3 class="text-lg font-bold">Koppelcode voor appstore-en-fork</h3>
      <p class="text-sm">Gemaakt om ${tijd('11:56')} door Beheerder · geldig tot ${tijd('12:56')} · nog <span class="cijfers font-semibold">59:12</span></p>
    </div>
    <span class="code-groot" aria-hidden="true">K7MW-2QXD-9RTH</span>
    ${kopieer('Koppelcode', 'K7MW-2QXD-9RTH')}
    ${kopieer('Vingerafdruk van de Hub', vingerafdruk)}
    ${melding('info', 'info', '<p><strong>Deze code zie je maar één keer.</strong> Hij werkt één keer en verloopt na 60 minuten. Een nieuwe code maakt deze niet ongeldig.</p>')}
    <ol class="flex flex-col gap-3">
      <li class="flex gap-3"><span class="stap-bol" aria-hidden="true">1</span><span class="min-w-0">Open de statuspagina van appstore-en-fork: <span class="font-mono break-all">http://nas.voorbeeld:30430</span> ${voorbeeld()}<span class="block text-sm text-muted-foreground">Adres gemeten: NAS-adres uit D03 + hostpoort uit de inventaris.</span></span></li>
      <li class="flex gap-3"><span class="stap-bol" aria-hidden="true">2</span><span class="min-w-0">Vul daar het Hub-adres, de koppelcode en de vingerafdruk in en kies <strong>Koppelen</strong>.</span></li>
      <li class="flex gap-3"><span class="stap-bol" aria-hidden="true">3</span><span class="min-w-0">Vergelijk daarna op de statuspagina de vingerafdruk met die hierboven.</span></li>
    </ol>
    <p class="flex items-center gap-2 text-sm font-semibold">${i('hourglass', 'size-4')}Wacht op de dienst — deze pagina toont de koppeling zodra appstore-en-fork zich meldt.</p>
  </div>
</section>`;

  const lijst = `
<section aria-labelledby="lijst-titel" class="flex flex-col gap-3" data-testid="dienstenregister">
  <div class="flex flex-wrap items-baseline justify-between gap-2">
    <h2 id="lijst-titel" class="text-xl font-bold">Gekoppelde diensten</h2>
    <p class="text-sm text-muted-foreground">5 gekoppeld · 1 ingetrokken (verborgen)</p>
  </div>
  <p class="max-w-prose text-sm">"Gekoppeld" zegt alleen dat de dienst een geldige sleutel heeft. Of hij gezond is, zie je bij <a href="apps.html">Apps</a>.</p>
  <div class="grid gap-4 xl:grid-cols-2 xl:items-start">
    ${dienst({ id: 1, naam: 'home-control-hub', appId: 'home-control-hub', pillen: pil('neutraal', 'link-2', 'Gekoppeld'),
      feiten: [['Versie', '0.4.0'], ['Gekoppeld', `8 nov, via koppelcode`], ['Laatste contact', tijd('11:55', '1 min geleden')], ['Token', '<span class="font-mono">••••Q7xD</span> · 12 dagen oud']],
      acties: actie('Rotatie aanvragen', 'key-round', 'home-control-hub') + actie('Ontkoppelen…', 'unlink', 'home-control-hub') + actie('Intrekken…', 'shield-x', 'home-control-hub') })}
    ${dienst({ id: 2, naam: 'appstore-en-fork', appId: 'appstore-en-fork', pillen: pil('neutraal', 'link-2', 'Gekoppeld') + pil('info', 'key-round', 'Rotatie aangevraagd'),
      feiten: [['Versie', '0.3.2'], ['Gekoppeld', '7 nov, via enrollment-token'], ['Laatste contact', tijd('11:38', '18 min geleden')], ['Token', '<span class="font-mono">••••m2Ra</span> · 2 dagen oud']],
      extra: `<p class="text-sm">Rotatie aangevraagd om ${tijd('11:40')} door Beheerder. De dienst roteert zelf bij zijn volgende aanroep; daarna blijft het oude token nog hooguit 10 minuten geldig.</p>`,
      acties: actie('Ontkoppelen…', 'unlink', 'appstore-en-fork') + actie('Intrekken…', 'shield-x', 'appstore-en-fork') })}
    ${dienst({ id: 3, naam: 'jelly-leon-platform', appId: 'jelly-leon-platform', pillen: pil('neutraal', 'link-2', 'Gekoppeld'),
      feiten: [['Versie', '0.2.0'], ['Gekoppeld', '9 mei, via enrollment-token'], ['Laatste contact', tijd('11:54', '2 min geleden')], ['Token', '<span class="font-mono">••••a91K</span> · 194 dagen oud']],
      extra: melding('info', 'key-round', '<p><strong>Token ouder dan 180 dagen.</strong> We raden aan rotatie aan te vragen. De Hub roteert nooit zelf en de AI kan het niet aanvragen.</p>'),
      acties: actie('Rotatie aanvragen', 'key-round', 'jelly-leon-platform') + actie('Ontkoppelen…', 'unlink', 'jelly-leon-platform') + actie('Intrekken…', 'shield-x', 'jelly-leon-platform') })}
    ${dienst({ id: 4, naam: 'zoeken-en-persoonlijke-ai', appId: 'zoeken-en-persoonlijke-ai', pillen: pil('neutraal', 'link-2', 'Gekoppeld'),
      feiten: [['Versie', '0.1.4'], ['Gekoppeld', '6 nov, via koppelcode'], ['Laatste contact', '<time datetime="2026-11-07T09:12:00+01:00">7 nov, 09:12</time> (2 dagen geleden)'], ['Token', '<span class="font-mono">••••c0Vt</span> · 3 dagen oud']],
      extra: foutpaneel({ titel: 'Ontkoppelen is mislukt', waarom: 'De dienst is niet bereikbaar; er is niets ontkoppeld en niets ingetrokken.', doen: 'Start de dienst in TrueNAS en probeer het opnieuw. Of trek alleen de registratie in: de dienst merkt dat bij zijn volgende aanroep.', code: 'service_unreachable', trace: '3e8a1c57-0b6d-4f29-a1e4-9c7d2b5f8e03', kop: 'h4', details: 'HTTP 502 · POST /api/v1/services/…/unlink · reden: verbinding geweigerd (dienst → /connector/v1/hub-link/unlink)' }),
      acties: actie('Rotatie aanvragen', 'key-round', 'zoeken-en-persoonlijke-ai') + actie('Intrekken…', 'shield-x', 'zoeken-en-persoonlijke-ai') })}
    ${dienst({ id: 5, naam: 'Executor', appId: 'ai-server-manager-executor', pillen: pil('neutraal', 'link-2', 'Gekoppeld'),
      feiten: [['Versie', '0.1.0'], ['Gekoppeld', '8 nov, via koppelcode (30 min)'], ['Laatste contact', tijd('11:56', 'zojuist')], ['Schrijfsleutel', 'Alleen op de executorpagina; de Hub ziet hem nooit.']],
      acties: `<a href="#" class="knop knop-secundair w-full sm:w-auto" target="_blank" rel="noopener">${i('square-arrow-out-up-right')}<span>Executorpagina openen</span><span class="sr-only"> (opent in een nieuw tabblad)</span></a>` + actie('Intrekken…', 'shield-x', 'Executor') })}
  </div>
  <label class="keuze w-fit"><input type="checkbox"><span>Ingetrokken diensten tonen (1)</span></label>
</section>`;

  const inhoud = paginakop({
    kruimel: kruimel([['Instellingen', 'instellingen-toegang.html'], ['Diensten', '']]),
    titel: 'Diensten',
    omschrijving: 'Eigen diensten van het platform en hun koppeling met de Hub. Koppelen, rotatie en intrekken doe je hier; de diensten zelf tonen alleen hun status.',
    bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist)',
    acties: knop('Dienst koppelen', { soort: 'primair', ic: 'link-2', href: '#koppelen' }),
  }) + `<div class="flex flex-col gap-6">${sleutelset}${koppelen}${lijst}</div>`;
  return shell({ pagina: 'instellingen', titel: 'Diensten', inhoud });
}
