// S-165 Toegang → Noodaccount (contract 1.2 §4.1, H6; Excel B01-006/B13-001). Scenario: na een noodlogin geldt de
// rotatieplicht; de beheerder vernieuwt wachtwoord en TOTP (stap 2 van 3) en draait de zelftest. Alle data fictief.
// Nieuw: TotpInstellen (C-59) en Zelftest als TestResultaat (C-58); zie COMPONENTEN.md §27.
import { i, knop, kopieer, melding, shell, paginakop, kruimel, voorbeeld } from './ui.mjs';

const pil = (soort, ic, tekst) => `<span class="status status-${soort}">${i(ic)}<span>${tekst}</span></span>`;
const controle = (soort, ic, naam, detail) => `<li class="controle controle-${soort}">${i(ic)}<span class="controle-naam">${naam}</span><span class="controle-detail">${detail}</span></li>`;

export function noodaccount() {
  const status = `
<section aria-labelledby="st-titel" class="kaart gap-4" data-testid="noodaccount-status">
  <div class="flex flex-wrap items-center gap-3">
    <h2 id="st-titel" class="text-xl font-bold">Status</h2>
    ${pil('neutraal', 'life-buoy', 'Ingesteld')}${pil('info', 'key-round', 'Rotatie loopt')}
  </div>
  <div class="melding melding-onbekend flex-col sm:flex-row" data-as="onbekend">
    ${i('circle-help')}
    <div class="min-w-0 flex-1"><p class="font-bold">Noodlogin werkt nu niet: de nieuwe TOTP is nog niet bevestigd.</p>
    <p class="mt-1">Na de noodlogin van 8 nov om 21:04 moesten wachtwoord en TOTP opnieuw. Het wachtwoord is vernieuwd; bevestig hieronder de code uit je authenticator-app. Tot dan kan "OIDC verplicht" ook niet aan.</p></div>
  </div>
  <dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
    <div><dt class="font-semibold text-muted-foreground">Account</dt><dd class="font-mono">noodbeheer</dd></div>
    <div><dt class="font-semibold text-muted-foreground">Rol</dt><dd>Beheerder (vast)</dd></div>
    <div><dt class="font-semibold text-muted-foreground">Sessieduur</dt><dd>60 min, niet te verlengen</dd></div>
    <div><dt class="font-semibold text-muted-foreground">Laatst gebruikt</dt><dd><time datetime="2026-11-08T21:04:00+01:00">8 nov 2026, 21:04</time> · incident gemeld</dd></div>
    <div><dt class="font-semibold text-muted-foreground">Herbevestiging</dt><dd>Volgende uiterlijk <time datetime="2027-02-06">6 feb 2027</time>. Elke 90 dagen een melding, nooit een blokkade.</dd></div>
    <div><dt class="font-semibold text-muted-foreground">Inloggen kan</dt><dd>Alleen vanaf privé-adressen (LAN of VPN), nooit vanaf internet.</dd></div>
  </dl>
</section>`;

  const STAPPEN = [['Nieuw wachtwoord', 'klaar'], ['Authenticator-app en code', 'huidig']];
  const stepper = `<nav aria-label="Stappen van het vernieuwen" class="mb-2"><ol class="flex flex-wrap gap-x-4 gap-y-2">${STAPPEN.map(([t, s], k) => `<li class="flex items-center gap-2 ${s === 'klaar' ? 'stap-klaar' : s === 'huidig' ? 'stap-huidig' : ''}"${s === 'huidig' ? ' aria-current="step"' : ''}><span class="stap-bol" aria-hidden="true">${s === 'klaar' ? i('check', 'size-4') : k + 1}</span><span class="text-sm ${s === 'huidig' ? 'font-bold' : ''}">${t}</span>${s === 'klaar' ? '<span class="sr-only"> (klaar)</span>' : ''}</li>`).join('')}</ol></nav>`;

  const totp = `
<section aria-labelledby="totp-titel" class="kaart gap-4" data-testid="totp-instellen">
  <h2 id="totp-titel" class="text-xl font-bold">Wachtwoord en TOTP vernieuwen</h2>
  ${stepper}
  <h3 class="text-lg font-bold">Stap 2 van 2: Authenticator-app instellen en code bevestigen</h3>
  ${melding('info', 'info', '<p><strong>Dit geheim zie je maar één keer.</strong> Zet het nu in je authenticator-app en bewaar een kopie offline, bijvoorbeeld op papier bij je herstelkit. De Hub toont het hierna nooit meer.</p>')}
  <div class="grid gap-4 lg:grid-cols-2">
    ${kopieer('Geheim (handmatig invoeren)', ['JBSW', 'Y3DP', 'EHPK', '3PXP', 'K7QV', '2MDA'].map((g) => `<span class="whitespace-nowrap">${g}</span>`).join(' '))}
    ${kopieer('Koppeling voor de app (otpauth)', 'otpauth://totp/TrueNAS%20Home%20Platform:noodbeheer?secret=JBSWY3DPEHPK3PXPK7QV2MDA&amp;issuer=TrueNAS%20Home%20Platform&amp;digits=6&amp;period=30')}
  </div>
  <p class="flex items-start gap-2 text-sm">${i('smartphone', 'mt-0.5 size-4 shrink-0')}<span>Kies in de app "Code toevoegen" en dan "Sleutel invoeren" (tijdgebaseerd, 6 cijfers, elke 30 seconden). De namen verschillen per app. ${voorbeeld()}</span></p>
  <form class="flex flex-col gap-2 border-t border-border pt-4" aria-labelledby="code-l">
    <h4 id="code-l" class="font-bold">Code bevestigen</h4>
    <label for="totp-code" class="veld-label">Code uit de authenticator-app</label>
    <p id="totp-hulp" class="veld-hulp">6 cijfers. De code wisselt elke 30 seconden; een oude code werkt niet.</p>
    <input id="totp-code" class="invoer max-w-48 font-mono cijfers" inputmode="numeric" autocomplete="one-time-code" maxlength="6" aria-describedby="totp-hulp">
    <div class="flex flex-col gap-2 pt-1 sm:flex-row">${knop('Code bevestigen', { soort: 'primair', ic: 'check', extra: 'w-full sm:w-auto' })}${knop('Opnieuw beginnen', { soort: 'stil', ic: 'rotate-ccw', extra: 'w-full sm:w-auto' })}</div>
  </form>
</section>`;

  const zelftest = `
<section aria-labelledby="zt-titel" class="kaart gap-4" data-testid="zelftest">
  <div class="flex flex-col gap-1">
    <h2 id="zt-titel" class="text-xl font-bold">Zelftest</h2>
    <p class="max-w-prose">Controleert of noodlogin zou werken, zonder in te loggen en zonder Authentik of het netwerk te gebruiken. Er verandert niets.</p>
  </div>
  <div>${knop('Zelftest uitvoeren', { ic: 'list-checks', extra: 'w-full sm:w-auto' })}</div>
  <div class="flex flex-col gap-2">
    <p class="font-semibold" role="status">Uitkomst om <time datetime="2026-11-09T11:56:00+01:00">11:56</time>: noodlogin werkt nu niet (1 controle mislukt).</p>
    <ul class="controles">
      ${controle('ok', 'check', 'Noodaccount', 'Aanwezig en actief.')}
      ${controle('fout', 'octagon-x', 'TOTP', 'Nog niet bevestigd: rotatie loopt. Bevestig de code hierboven.')}
      ${controle('ok', 'check', 'Privé-adres wordt toegelaten', 'Testadres <span class="font-mono">10.0.0.1</span> telt als privé.')}
      ${controle('ok', 'check', 'Internetadres wordt geweigerd', 'Documentatie-adres <span class="font-mono">192.0.2.10</span> telt niet als privé.')}
      ${controle('onbekend', 'circle-help', 'Jouw adres zoals de Hub het ziet', '<span class="font-mono">172.17.0.1</span> — <strong>Onbekend:</strong> dit lijkt het gateway-adres van het Docker-netwerk. Dan ziet de Hub niet het echte adres van je apparaat en is de controle op privé-adressen zwakker. Niet gevalideerd op de NAS.')}
    </ul>
  </div>
</section>`;

  const instellingen = `
<section aria-labelledby="in-titel" class="kaart gap-4">
  <h2 id="in-titel" class="text-xl font-bold">Noodlogin gebruiken</h2>
  ${kopieer('Adres van de noodlogin (zet dit in je herstelkit)', 'http://hub.voorbeeld:30400/inloggen/nood')}
  <div class="flex flex-col gap-1.5">
    <label for="duur" class="veld-label">Sessieduur van een noodlogin</label>
    <p id="duur-hulp" class="veld-hulp">5 tot 240 minuten; standaard 60. De sessie is niet te verlengen.</p>
    <div class="flex flex-wrap items-center gap-2"><input id="duur" class="invoer max-w-32 cijfers" inputmode="numeric" value="60" aria-describedby="duur-hulp"><span>minuten</span></div>
  </div>
  <p class="flex items-start gap-2 text-sm">${i('lock', 'mt-0.5 size-4 shrink-0 text-gate')}<span>Wijzigen vraagt je eigen wachtwoord. Dit zijn geen acties voor de AI: die kan het noodaccount niet zien, voorstellen of wijzigen.</span></p>
</section>`;

  const inhoud = paginakop({
    kruimel: kruimel([['Instellingen', 'instellingen-toegang.html'], ['Toegang', 'instellingen-toegang.html'], ['Noodaccount', '']]),
    titel: 'Noodaccount',
    omschrijving: 'Een lokaal account waarmee je de Hub in kunt als inloggen via SSO niet werkt. Met wachtwoord én een code uit een authenticator-app, alleen vanaf je eigen netwerk.',
    bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist)',
  }) + `<div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] xl:items-start"><div class="flex min-w-0 flex-col gap-6">${status}${totp}</div><div class="flex min-w-0 flex-col gap-6">${zelftest}${instellingen}</div></div>`;
  return shell({ pagina: 'instellingen', titel: 'Noodaccount', inhoud });
}
