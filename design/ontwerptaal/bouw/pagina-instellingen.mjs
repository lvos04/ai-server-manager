// Instellingen in fase P1: S-161 Gebruikers en rollen (incl. kind), S-163 SSO (OIDC-config + test), S-165 (samenvatting
// noodaccount), S-168 meldingskanalen en monitoringbronnen met verbindingstest (B09-002/003/005). Alle data fictief.
import { i, status, knop, kopieer, melding, gate, shell, paginakop, kruimel, voorbeeld } from './ui.mjs';

const pil = (soort, ic, tekst) => `<span class="status status-${soort}">${i(ic)}<span>${tekst}</span></span>`;
const controle = (soort, ic, naam, detail) => `<li class="controle controle-${soort}">${i(ic)}<span class="controle-naam">${naam}</span><span class="controle-detail">${detail}</span></li>`;

const SUB = [['Account', 'user', '#'], ['Gebruikers en toegang', 'users', 'instellingen-toegang.html'], ['Noodaccount', 'life-buoy', 'noodaccount.html'], ['Diensten', 'package', 'diensten.html'],
  ['Monitoring en meldingen', 'bell', 'instellingen-bronnen.html'], ['Apparaat en app', 'smartphone', '#'], ['Auditspoor', 'history', '#'], ['Over deze Hub', 'info', '#']];
const subnav = (huidig) => `<nav aria-label="Instellingen" class="hidden lg:block"><ul class="sticky top-20 flex flex-col gap-1">${SUB.map(([l, ic, h]) => `<li><a href="${h}" class="zij-sub"${l === huidig ? ' aria-current="page"' : ''}>${i(ic)}${l}</a></li>`).join('')}</ul></nav>`;
const layout = (huidig, inhoud) => `<div class="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)]">${subnav(huidig)}<div class="flex min-w-0 flex-col gap-6">${inhoud}</div></div>`;

// ── Gebruikers en toegang ─────────────────────────────────────────────────────────────────────────────────────────
const ROLLEN = [
  ['user-check', 'Beheerder', 'Alles: gebruikers, koppelingen, SSO, noodaccount en (vanaf P2) goedkeuren.'],
  ['user', 'Operator', 'Meten en vernieuwen; incidenten erkennen, uitstellen en oplossen. Geen gebruikers of geheimen.'],
  ['eye', 'Kijker', 'Alleen lezen. Ziet geen geheimen en kan niets wijzigen.'],
  ['smile', 'Kind', 'Alleen Home, Kijken, Zoeken en Ik — met toegestane titels. Nooit beheer.'],
];
const GEBRUIKERS = [
  ['Beheerder', 'beheerder', 'Beheerder', 'Lokaal wachtwoord', '2 actief', true],
  ['Noodaccount', 'noodbeheer', 'Beheerder', 'Noodlogin (wachtwoord + TOTP)', 'geen', false],
  ['Alex', 'alex', 'Operator', 'Lokaal wachtwoord', 'geen', true],
  ['Huisgenoot', 'huisgenoot', 'Kijker', 'SSO · groep gezin', '1 actief', true],
  ['Sam', 'sam', 'Kind', 'SSO · groep kinderen', '1 actief', true],
];

export function instellingenToegang() {
  const rollen = `<dl class="grid gap-3 sm:grid-cols-2">${ROLLEN.map(([ic, r, w]) => `<div class="rounded-lg border border-border p-3"><dt class="flex items-center gap-2 font-semibold">${i(ic, 'size-5 text-muted-foreground')}${r}</dt><dd class="mt-1 text-sm">${w}</dd></div>`).join('')}</dl>`;
  const acties = (naam, nood) => nood
    ? `<a href="noodaccount.html" class="knop knop-secundair knop-klein w-full xl:w-auto">${i('life-buoy')}<span>Noodaccount beheren</span></a>`
    : `<button type="button" class="knop knop-secundair knop-klein w-full xl:w-auto" aria-label="Rol wijzigen: ${naam}">${i('user-check')}<span>Rol wijzigen</span></button><button type="button" class="knop knop-secundair knop-klein w-full xl:w-auto" aria-label="Sessies intrekken: ${naam}">${i('log-out')}<span>Sessies intrekken</span></button>`;
  const rij = ([naam, gb, rol, aan, ses, gewoon]) => `<tr class="border-b border-border align-top"><th scope="row" class="py-3 pr-4 text-left font-normal"><span class="block font-semibold">${naam}</span><span class="font-mono text-sm text-muted-foreground">${gb}</span></th><td class="py-3 pr-4">${rol}</td><td class="py-3 pr-4 text-sm">${aan}</td><td class="py-3 pr-4 text-sm">${ses}</td><td class="py-3"><div class="flex flex-wrap justify-end gap-2">${acties(naam, !gewoon)}</div></td></tr>`;
  const kaart = ([naam, gb, rol, aan, ses, gewoon]) => `<li class="kaart gap-2"><p class="font-semibold">${naam} <span class="font-mono text-sm font-normal text-muted-foreground">${gb}</span></p><dl class="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm"><dt class="font-semibold text-muted-foreground">Rol</dt><dd>${rol}</dd><dt class="font-semibold text-muted-foreground">Aanmelden</dt><dd>${aan}</dd><dt class="font-semibold text-muted-foreground">Sessies</dt><dd>${ses}</dd></dl><div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">${acties(naam, !gewoon)}</div></li>`;
  const gebruikers = `
<section aria-labelledby="gb-titel" class="kaart gap-4" data-testid="gebruikers">
  <div class="flex flex-wrap items-center justify-between gap-2"><h2 id="gb-titel" class="text-xl font-bold">Gebruikers en rollen</h2>${knop('Gebruiker toevoegen', { soort: 'primair', ic: 'user-plus' })}</div>
  <h3 class="sr-only">Gebruikers</h3>
  <table class="hidden w-full text-left xl:table"><caption class="sr-only">Gebruikers</caption><thead class="bg-muted text-sm"><tr><th scope="col" class="py-2 pr-4">Gebruiker</th><th scope="col" class="py-2 pr-4">Rol</th><th scope="col" class="py-2 pr-4">Aanmelden</th><th scope="col" class="py-2 pr-4">Sessies</th><th scope="col" class="py-2"><span class="sr-only">Acties</span></th></tr></thead><tbody>${GEBRUIKERS.map(rij).join('')}</tbody></table>
  <ul class="grid gap-3 md:grid-cols-2 xl:hidden">${GEBRUIKERS.map(kaart).join('')}</ul>
  <label class="keuze w-fit"><input type="checkbox"><span>Gedeactiveerde gebruikers tonen (1)</span></label>
  <details class="rounded-lg border border-border-strong">
    <summary class="flex min-h-touch cursor-pointer items-center gap-2 px-3 font-semibold">${i('chevron-down', 'size-5 klap-icoon')}Wat mag elke rol?</summary>
    <div class="flex flex-col gap-3 border-t border-border p-3">${rollen}
    <p class="text-sm">Via SSO bepaalt de groep de rol. Hoort iemand bij meerdere groepen, dan wint <strong>Kind</strong>; anders de hoogste rol. Zonder passende groep: geen toegang. De AI kan rollen nooit wijzigen.</p></div>
  </details>
</section>`;

  const groep = (g, r) => `<tr class="border-b border-border"><th scope="row" class="py-2 pr-4 text-left font-mono text-sm font-normal break-all">${g}</th><td class="py-2">${r}</td></tr>`;
  const sso = `
<section aria-labelledby="sso-titel" class="kaart gap-4" data-testid="sso">
  <div class="flex flex-wrap items-center gap-3"><h2 id="sso-titel" class="text-xl font-bold">Inloggen via SSO</h2>${pil('neutraal', 'power', 'Uit')}</div>
  <p class="max-w-prose">Inloggen met je Authentik-account (OpenID Connect). Lokaal inloggen en het noodaccount blijven altijd werken.</p>
  ${gate('Inschakelen kan nog niet: geblokkeerd door de HTTPS-voorwaarde', 'besluit D17 (HTTPS) op Getest. De testlogin hieronder is wel geslaagd.', knop('D17 openen', { ic: 'chevron-right', href: '#' }))}
  <form class="flex flex-col gap-4" aria-labelledby="sso-titel">
    <div class="flex flex-col gap-1.5"><label for="issuer" class="veld-label">Issuer-adres</label><p id="issuer-hulp" class="veld-hulp">Exact zoals Authentik het noemt, alleen https. Wijzigen zet SSO uit tot een nieuwe testlogin slaagt.</p><input id="issuer" class="invoer font-mono" value="https://auth.voorbeeld/application/o/hub/" aria-describedby="issuer-hulp"></div>
    <div class="flex flex-col gap-1.5"><label for="client" class="veld-label">Client-ID</label><input id="client" class="invoer max-w-96 font-mono" value="hub-voorbeeld"></div>
    <div class="flex flex-col gap-1.5"><span class="veld-label" id="geheim-l">Clientgeheim</span><p class="flex flex-wrap items-center gap-2"><span class="font-mono">••••7f3a</span><span class="text-sm text-muted-foreground">opgeslagen 9 nov 2026 · de waarde wordt nooit getoond</span></p><div>${knop('Geheim vervangen', { ic: 'key-round', attrs: 'aria-describedby="geheim-l"' })}</div></div>
    ${kopieer('Terugkeer-adres (zet dit in Authentik)', 'http://hub.voorbeeld:30400/api/v1/auth/oidc/callback')}
    ${melding('info', 'info', '<p>Dit terugkeer-adres is <strong>http</strong>. De aanmeldcode is beschermd met PKCE en een browsercookie, maar zet HTTPS aan zodra D17 klaar is.</p>')}
  </form>
  <div class="flex flex-col gap-2">
    <h3 class="font-bold">Controle van de issuer</h3>
    <p class="text-sm" role="status">Geslaagd · opgehaald om <time datetime="2026-11-09T11:48:00+01:00">11:48</time>.</p>
    <ul class="controles">
      ${controle('ok', 'check', 'Issuer klopt exact', 'Gelijk aan het adres hierboven.')}
      ${controle('ok', 'check', 'Zelfde oorsprong', 'Alle endpoints op hetzelfde adres als de issuer.')}
      ${controle('ok', 'check', 'Sleutels', '1 sleutel (RS256); symmetrische ondertekening wordt geweigerd.')}
    </ul>
  </div>
  <h3 class="font-bold">Groep → rol</h3>
  <table class="w-full text-left"><caption class="sr-only">Koppeling van Authentik-groepen aan rollen</caption><thead class="bg-muted text-sm"><tr><th scope="col" class="py-2 pr-4">Groep in Authentik</th><th scope="col" class="py-2">Rol in de Hub</th></tr></thead><tbody>${groep('hub-beheerders', 'Beheerder')}${groep('hub-operators', 'Operator')}${groep('gezin', 'Kijker')}${groep('kinderen', 'Kind')}</tbody></table>
  <div class="flex flex-col gap-2 border-t border-border pt-4">
    <h3 class="font-bold">Testlogin</h3>
    <p class="flex flex-wrap items-center gap-2">${pil('neutraal', 'check', 'Geslaagd')}<span>om <time datetime="2026-11-09T11:50:00+01:00">11:50</time> als <span class="font-mono">beheerder</span> · groep hub-beheerders → Beheerder. Er is geen sessie gemaakt.</span></p>
    <div class="flex flex-col gap-2 sm:flex-row">${knop('Testlogin starten', { ic: 'log-in', extra: 'w-full sm:w-auto' })}</div>
  </div>
  <div class="flex flex-col gap-1 border-t border-border pt-4">
    <span class="veld-label">OIDC verplicht</span>
    <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3"><button type="button" class="knop knop-secundair w-full sm:w-auto" aria-disabled="true" aria-describedby="verplicht-reden">${i('lock')}<span>OIDC verplicht maken</span></button><span id="verplicht-reden" class="text-sm">Kan pas als SSO aanstaat én het noodaccount werkt (nu niet: TOTP wacht op bevestiging).</span></div>
  </div>
  <div class="melding melding-onbekend flex-col sm:flex-row" data-as="onbekend">${i('circle-help')}<div class="min-w-0 flex-1"><p class="font-bold">Advies van home-control-hub: minste rechten deels gecontroleerd.</p><p class="mt-1 text-sm">Niet alle rechten van de Hub-client in Authentik konden worden nagegaan. Bijgewerkt <time datetime="2026-11-09T11:30:00+01:00">11:30</time>.</p></div></div>
</section>`;

  const nood = `
<section aria-labelledby="nood-titel" class="kaart gap-3">
  <div class="flex flex-wrap items-center gap-3"><h2 id="nood-titel" class="text-xl font-bold">Noodaccount</h2>${pil('info', 'key-round', 'Rotatie loopt')}</div>
  <p>Noodlogin werkt nu niet: de nieuwe TOTP is nog niet bevestigd.</p>
  <a href="noodaccount.html" class="knop knop-secundair knop-blok sm:w-fit"><span>Noodaccount openen</span>${i('chevron-right')}</a>
</section>`;

  const inhoud = paginakop({ kruimel: kruimel([['Instellingen', '#'], ['Gebruikers en toegang', '']]), titel: 'Gebruikers en toegang',
    omschrijving: 'Wie de Hub mag gebruiken en hoe je inlogt.', bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist)' })
    + layout('Gebruikers en toegang', gebruikers + sso + nood);
  return shell({ pagina: 'instellingen', titel: 'Gebruikers en toegang', inhoud });
}

// ── Monitoring en meldingen ───────────────────────────────────────────────────────────────────────────────────────
export function instellingenBronnen() {
  const bron = ({ id, naam, soort, adres, sleutel, pillen, inhoud, acties }) => `<article class="kaart gap-3" aria-labelledby="${id}"><div class="flex flex-col gap-2"><h3 id="${id}" class="kaart-titel">${i('activity')}${naam}</h3><div class="flex flex-wrap gap-2">${pillen}</div></div>
  <dl class="grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm"><dt class="font-semibold text-muted-foreground">Soort</dt><dd>${soort}</dd><dt class="font-semibold text-muted-foreground">Adres</dt><dd class="font-mono break-all">${adres}</dd><dt class="font-semibold text-muted-foreground">${sleutel[0]}</dt><dd><span class="font-mono">${sleutel[1]}</span> · ${sleutel[2]}</dd></dl>${inhoud}<div class="mt-auto flex flex-col gap-2 sm:flex-row sm:flex-wrap">${acties}</div></article>`;

  const bronnen = `
<section aria-labelledby="br-titel" class="flex flex-col gap-4" data-testid="monitoringbronnen">
  <div class="flex flex-wrap items-center justify-between gap-2"><h2 id="br-titel" class="text-xl font-bold">Monitoringbronnen</h2>${knop('Bron toevoegen', { soort: 'primair', ic: 'plus', href: '#bron-nieuw' })}</div>
  <p class="max-w-prose text-sm">De Hub leest deze bronnen alleen. "Uitgelezen" zegt dat het lezen lukte; of een app gezond is, zie je bij Apps.</p>
  <div class="grid gap-4 xl:grid-cols-2">
    ${bron({ id: 'b-kuma', naam: 'Uptime Kuma', soort: 'Uptime Kuma 2.x (gevonden)', adres: 'http://nas.voorbeeld:31050', sleutel: ['API-sleutel', '••••a9k2', 'opgeslagen 8 nov'],
      pillen: pil('neutraal', 'check', 'Uitgelezen om 11:55'),
      inhoud: `<p class="text-sm">23 monitors · 19 gekoppeld aan een app · 4 niet gekoppeld (<a href="#">koppelen</a>).</p>`,
      acties: knop('Nu uitlezen', { ic: 'plug-zap', extra: 'w-full sm:w-auto' }) + knop('Wijzigen', { ic: 'settings', extra: 'w-full sm:w-auto' }) })}
    ${bron({ id: 'b-beszel', naam: 'Beszel', soort: 'Beszel (readonly-gebruiker)', adres: 'http://nas.voorbeeld:30090', sleutel: ['Wachtwoord', '••••Lm4q', 'opgeslagen 8 nov'],
      pillen: status('storing', 'Uitlezen mislukt'),
      inhoud: `<p class="reden">Inloggen geweigerd sinds <time datetime="2026-11-09T11:20:00+01:00">11:20</time>: het wachtwoord van de readonly-gebruiker klopt niet meer. GPU- en CPU-metingen uit Beszel zijn nu onbekend; er is een incident geopend.</p>`,
      acties: knop('Wachtwoord vervangen', { soort: 'primair', ic: 'key-round', extra: 'w-full sm:w-auto' }) + knop('Nu uitlezen', { ic: 'plug-zap', extra: 'w-full sm:w-auto' }) })}
  </div>
  <form id="bron-nieuw" class="kaart gap-4" aria-labelledby="nieuw-titel">
    <h3 id="nieuw-titel" class="text-lg font-bold">Bron toevoegen</h3>
    <fieldset class="flex flex-col gap-2"><legend class="veld-label mb-1">Soort bron <span class="font-normal text-muted-foreground">(verplicht)</span></legend>
      <div class="flex flex-col gap-2 sm:flex-row"><label class="keuze sm:flex-1"><input type="radio" name="soort" checked><span>Uptime Kuma</span></label><label class="keuze sm:flex-1"><input type="radio" name="soort"><span>Beszel</span></label></div></fieldset>
    <div class="flex flex-col gap-1.5"><label for="b-naam" class="veld-label">Naam</label><input id="b-naam" class="invoer max-w-80"></div>
    <div class="flex flex-col gap-1.5"><label for="b-adres" class="veld-label">Adres</label><p id="b-adres-hulp" class="veld-hulp">Vorm: http(s)://&lt;adres&gt;:&lt;poort&gt;. Geen localhost; de Hub draait in een eigen container.</p><input id="b-adres" class="invoer font-mono" aria-describedby="b-adres-hulp"></div>
    <div class="flex flex-col gap-1.5"><label for="b-key" class="veld-label">API-sleutel</label><p id="b-key-hulp" class="veld-hulp">Maak in Uptime Kuma onder Instellingen een API-sleutel. Wordt versleuteld opgeslagen; je ziet daarna alleen de laatste 4 tekens.</p><input id="b-key" type="password" class="invoer max-w-96" autocomplete="off" aria-describedby="b-key-hulp"></div>
    <div class="flex flex-col gap-2 sm:flex-row">${knop('Opslaan en testen', { soort: 'primair', ic: 'plug-zap', extra: 'w-full sm:w-auto' })}${knop('Annuleren', { soort: 'stil', extra: 'w-full sm:w-auto' })}</div>
    <p class="text-sm text-muted-foreground">De test leest de bron echt uit en toont het echte resultaat. Lukt het niet, dan blijft de bron opgeslagen met de reden en is wat hij meet onbekend.</p>
  </form>
</section>`;

  const kanalen = `
<section aria-labelledby="kn-titel" class="flex flex-col gap-4" data-testid="meldingskanalen">
  <h2 id="kn-titel" class="text-xl font-bold">Meldingskanalen</h2>
  <article class="kaart gap-3" aria-labelledby="k-gotify">
    <div class="flex flex-col gap-2"><h3 id="k-gotify" class="kaart-titel">${i('bell')}Gotify thuis</h3><div class="flex flex-wrap gap-2">${pil('neutraal', 'power', 'Aan')}</div></div>
    <dl class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
      <dt class="font-semibold text-muted-foreground">Adres</dt><dd class="font-mono break-all">http://nas.voorbeeld:30081</dd>
      <dt class="font-semibold text-muted-foreground">App-token</dt><dd><span class="font-mono">••••Zk2P</span> · opgeslagen 8 nov</dd>
      <dt class="font-semibold text-muted-foreground">Vanaf ernst</dt><dd>Info</dd>
      <dt class="font-semibold text-muted-foreground">Stille uren</dt><dd>23:00–07:00 · kritiek gaat altijd door</dd>
      <dt class="font-semibold text-muted-foreground">Hoogstens</dt><dd>10 meldingen per 15 min, daarna één samenvatting</dd>
    </dl>
    <div class="flex flex-col gap-1" role="status"><p class="text-sm"><strong>Testmelding:</strong> om <time datetime="2026-11-09T11:30:00+01:00">11:30</time> door Gotify aangenomen. Of hij op je telefoon aankwam, kan de Hub niet zien.</p></div>
    <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">${knop('Testmelding versturen', { ic: 'send', extra: 'w-full sm:w-auto' })}${knop('Wijzigen', { ic: 'settings', extra: 'w-full sm:w-auto' })}</div>
  </article>
  <article class="kaart gap-3" aria-labelledby="k-oob">
    <h3 id="k-oob" class="kaart-titel">${i('life-buoy')}Meldt er nog iets als de Hub uitvalt?</h3>
    <ul class="controles">
      ${controle('ok', 'check', 'Uptime Kuma bewaakt de Hub', 'Monitor "Hub" gevonden; Kuma meldt zelf, buiten de Hub om.')}
      ${controle('onbekend', 'circle-help', 'Kuma → Gotify', 'Handmatig bevestigd op 8 nov 2026. De Hub kan de meldinstelling van Kuma niet lezen; dit is niet door de Hub gevalideerd.')}
      ${controle('onbekend', 'circle-slash', 'Als de hele NAS uitvalt', 'Dan meldt niemand iets: Uptime Kuma en Gotify draaien op dezelfde NAS.')}
    </ul>
    <div>${knop('Handmatige test vastleggen', { ic: 'list-checks', extra: 'w-full sm:w-auto' })}</div>
  </article>
</section>`;

  const inhoud = paginakop({ kruimel: kruimel([['Instellingen', '#'], ['Monitoring en meldingen', '']]), titel: 'Monitoring en meldingen',
    omschrijving: 'Waar de Hub zijn metingen vandaan haalt en hoe hij je waarschuwt.', bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist)' })
    + layout('Monitoring en meldingen', bronnen + kanalen + `<p class="text-sm">${voorbeeld()} Adressen en sleutels zijn fictief.</p>`);
  return shell({ pagina: 'instellingen', titel: 'Monitoring en meldingen', inhoud });
}
