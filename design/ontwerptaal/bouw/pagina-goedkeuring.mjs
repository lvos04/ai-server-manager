// S-063 Goedkeuring (detail), R3 in twee stappen: stap 2 met getypte bevestiging. Volledige pagina, geen dialoog.
import { i, risico, kopieer, shell, paginakop, kruimel, knop, melding } from './ui.mjs';

export function goedkeuring() {
  const stap = (n, t, s) => `<li class="flex items-center gap-2 ${s}"><span class="stap-bol" aria-hidden="true">${s === 'stap-klaar' ? i('check', 'size-4') : n}</span><span class="${s === 'stap-huidig' ? 'font-bold' : ''}">${t}${s === 'stap-klaar' ? '<span class="sr-only"> (klaar)</span>' : s === 'stap-huidig' ? '<span class="sr-only"> (huidige stap)</span>' : ''}</span></li>`;
  const inhoud = paginakop({
    kruimel: kruimel([['Goedkeuringen', '#'], ['Data verwijderen', '']]),
    titel: 'Data van Voorbeeld-app verwijderen',
    omschrijving: 'Aangevraagd door Beheerder om 11:58 · deze actie is nooit door de AI voorgesteld.',
  }) + `
<div class="mx-auto flex max-w-3xl flex-col gap-5">
  <div class="kaart gap-4 border-2 border-risk-3">
    <div class="flex flex-wrap items-center gap-3">${risico(3)}<span class="text-sm">Goedkeuring geldig tot <time datetime="2026-11-09T12:13:00+01:00">12:13</time> (nog <span class="cijfers font-semibold">9:41</span>)</span></div>
    <ol class="flex flex-wrap gap-x-6 gap-y-2" aria-label="Stappen van de goedkeuring">${stap(1, 'Voorstel controleren', 'stap-klaar')}${stap(2, 'Bevestigen', 'stap-huidig')}</ol>
    <h2 class="text-xl font-bold">Stap 2 van 2: bevestigen</h2>
    <section aria-labelledby="gevolgen" class="flex flex-col gap-2">
      <h3 id="gevolgen" class="font-bold">Wat er gebeurt</h3>
      <ul class="flex list-disc flex-col gap-1 pl-6">
        <li>De app <strong>Voorbeeld-app</strong> wordt verwijderd (container en instellingen).</li>
        <li>De dataset <span class="font-mono">voorbeeldpool/apps/voorbeeld-app</span> wordt <strong>gewist</strong> (4,2&nbsp;GiB).</li>
        <li>Dit kun je niet ongedaan maken, behalve met het herstelpunt hieronder.</li>
        <li>Andere apps, media en foto's worden niet aangeraakt.</li>
      </ul>
    </section>
    ${kopieer('Herstelpunt (gemaakt om 11:59)', 'snap-voorbeeldpool-apps-voorbeeld-app-2026-11-09T1159Z')}
    <details class="rounded-lg border border-border-strong">
      <summary class="flex min-h-touch cursor-pointer items-center gap-2 px-3 font-semibold">${i('lock')}Gebonden velden</summary>
      <dl class="grid gap-x-4 gap-y-1 border-t border-border p-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
        <dt class="font-semibold text-muted-foreground">preview_hash</dt><dd class="font-mono break-all">b71e…09fa</dd>
        <dt class="font-semibold text-muted-foreground">resource_etag</dt><dd class="font-mono break-all">"a3c9-17"</dd>
        <dt class="font-semibold text-muted-foreground">policy_hash</dt><dd class="font-mono break-all">3f9a…c21e</dd>
        <dt class="font-semibold text-muted-foreground">Back-upgate</dt><dd>Open (alle voorwaarden gemeten om 11:56)</dd>
      </dl>
      <p class="border-t border-border p-3 text-sm">Verandert één gebonden veld vóór uitvoering, dan vervalt deze goedkeuring en vraag je een nieuw voorstel aan.</p>
    </details>
    <form class="flex flex-col gap-2" onsubmit="return false">
      <label for="bevestig" class="veld-label">Typ <span class="font-mono">voorbeeld-app</span> om te bevestigen</label>
      <p id="bevestig-hulp" class="veld-hulp">Zo weet je zeker dat je de juiste app verwijdert.</p>
      <input id="bevestig" class="invoer font-mono" autocomplete="off" autocapitalize="off" spellcheck="false" aria-describedby="bevestig-hulp bevestig-reden" data-bevestig-tekst="voorbeeld-app" data-bevestig-knop="bevestig-knop" data-bevestig-reden="bevestig-reden">
      <p id="bevestig-reden" class="text-sm text-muted-foreground" aria-live="polite">Typ eerst de naam van de app om te bevestigen.</p>
      <div class="mt-2 flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:justify-end">
        ${knop('Annuleren', { soort: 'secundair' })}
        ${knop('Weigeren…', { soort: 'stil', ic: 'x' })}
        <button type="submit" id="bevestig-knop" class="knop knop-gevaar" aria-disabled="true">${i('trash-2')}<span>Data definitief verwijderen</span></button>
      </div>
    </form>
  </div>
  ${melding('info', 'info', '<p>Na goedkeuren voert de executor de stappen uit: <strong>gecontroleerd → uitgevoerd → controle na uitvoering</strong>. Dubbel drukken leidt tot één uitvoering.</p>')}
</div>`;
  return shell({ pagina: 'goedkeuringen', zijHuidig: 'none', titel: 'Goedkeuring: data verwijderen (stap 2 van 2)', inhoud });
}
