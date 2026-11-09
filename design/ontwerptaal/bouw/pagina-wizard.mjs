// S-047 Installatiewizard, stap 2 van 7 "Parameters" (C-36 Wizard + C-37 SchemaForm + C-38 DatasetPicker). Fictief.
import { i, shell, paginakop, kruimel, knop, melding } from './ui.mjs';

export function wizard() {
  const STAPPEN = [['App kiezen', 'klaar'], ['Parameters', 'huidig'], ['Controle vooraf', ''], ['Preview', ''], ['Goedkeuring', ''], ['Uitvoeren', ''], ['Controle na uitvoering', '']];
  const stepper = `<nav aria-label="Stappen van de installatie" class="mb-6">
  <ol class="flex gap-2 overflow-hidden lg:gap-0">
    ${STAPPEN.map(([t, s], k) => `<li class="flex items-center gap-2 ${s === 'klaar' ? 'stap-klaar' : s === 'huidig' ? 'stap-huidig' : ''} lg:flex-1"${s === 'huidig' ? ' aria-current="step"' : ''}><span class="stap-bol" aria-hidden="true">${s === 'klaar' ? i('check', 'size-4') : k + 1}</span><span class="hidden text-sm lg:inline ${s === 'huidig' ? 'font-bold' : ''}">${t}</span><span class="sr-only lg:hidden">${t}</span>${s === 'klaar' ? '<span class="sr-only"> (klaar)</span>' : ''}${k < STAPPEN.length - 1 ? '<span class="hidden h-0.5 flex-1 bg-border lg:mx-2 lg:block" aria-hidden="true"></span>' : ''}</li>`).join('')}
  </ol>
</nav>`;
  const bron = (t) => `<span class="bron-tag">bron: ${t}</span>`;
  const inhoud = paginakop({ kruimel: kruimel([['Apps', '#'], ['Appstore', '#'], ['Voorbeeld-app installeren', '']]), titel: 'Voorbeeld-app installeren', omschrijving: 'Je wijzigt nog niets. Pas na de preview en de goedkeuring wordt er iets geïnstalleerd.' })
    + stepper + `
<form class="mx-auto flex max-w-3xl flex-col gap-6 pb-24 lg:pb-0" novalidate aria-labelledby="stap-titel">
  <h2 id="stap-titel" class="text-xl font-bold">Stap 2 van 7: Parameters</h2>
  <div class="melding melding-fout flex-col sm:flex-row" role="alert" aria-labelledby="fout-titel" tabindex="-1">
    ${i('octagon-x')}
    <div><h3 id="fout-titel" class="font-bold">2 velden hebben aandacht nodig</h3>
    <ul class="mt-1 flex list-disc flex-col pl-5"><li><a class="inline-flex min-h-touch items-center" href="#poort">Poort: 30480 is al in gebruik</a></li><li><a class="inline-flex min-h-touch items-center" href="#gpu-ja">GPU gebruiken: kies ja of nee</a></li></ul></div>
  </div>

  <fieldset class="flex flex-col gap-2">
    <legend class="veld-label mb-1">Datamap <span class="font-normal text-muted-foreground">(verplicht)</span></legend>
    <p class="veld-hulp" id="data-hulp">Kies een dataset met de rol <em>data</em>. Hier komt <span class="font-mono">/appdata</span> van de app. ${bron('datasetkiezer')}</p>
    <label class="keuze"><input type="radio" name="data" checked aria-describedby="data-hulp"><span class="min-w-0"><span class="block font-mono break-all">voorbeeldpool/apps/voorbeeld-app</span><span class="text-sm text-muted-foreground">rol data · 1,8&nbsp;TiB vrij</span></span></label>
    <label class="keuze"><input type="radio" name="data" disabled aria-describedby="data-hulp r-media"><span class="min-w-0"><span class="block font-mono break-all">voorbeeldpool/media</span><span class="text-sm" id="r-media">Niet te kiezen: mediadatasets zijn geen appdata.</span></span></label>
    <label class="keuze"><input type="radio" name="data" disabled aria-describedby="data-hulp r-mnt"><span class="min-w-0"><span class="block font-mono">/mnt</span><span class="text-sm" id="r-mnt">Niet te kiezen: geen dataset (beleid weigert hostpad /mnt).</span></span></label>
  </fieldset>

  <div class="flex flex-col gap-1.5">
    <label for="poort" class="veld-label">Poort <span class="font-normal text-muted-foreground">(verplicht)</span></label>
    <p id="poort-hulp" class="veld-hulp">Hostpoort op de NAS. Voorstel van het manifest; de Hub controleert conflicten. ${bron('wizard')}</p>
    <input id="poort" class="invoer max-w-48 cijfers" inputmode="numeric" value="30480" aria-invalid="true" aria-describedby="poort-hulp poort-fout">
    <p id="poort-fout" class="veldfout">${i('octagon-x')}<span>Poort 30480 is al in gebruik door Voorbeeld-dienst. Kies een andere poort, bijvoorbeeld 30481.</span></p>
  </div>

  <fieldset class="flex flex-col gap-2" aria-describedby="gpu-hulp gpu-fout">
    <legend class="veld-label mb-1">GPU (Intel render) gebruiken? <span class="font-normal text-muted-foreground">(verplicht)</span></legend>
    <p id="gpu-hulp" class="veld-hulp">De app krijgt dan toegang tot <span class="font-mono">/dev/dri</span>. Er is geen standaardantwoord.</p>
    <div class="flex flex-col gap-2 sm:flex-row">
      <label class="keuze border-2 border-down sm:flex-1"><input type="radio" name="gpu" id="gpu-ja" aria-invalid="true"><span>Ja, GPU gebruiken</span></label>
      <label class="keuze border-2 border-down sm:flex-1"><input type="radio" name="gpu" id="gpu-nee" aria-invalid="true"><span>Nee, alleen CPU</span></label>
    </div>
    <p id="gpu-fout" class="veldfout">${i('octagon-x')}<span>Kies ja of nee.</span></p>
  </fieldset>

  <div class="flex flex-col gap-1.5">
    <span class="veld-label" id="ww-l">Beheerderswachtwoord van de app</span>
    <p class="veld-hulp">De app maakt dit zelf bij de eerste start in <span class="font-mono">/appdata/secrets</span>. Je ziet de waarde nooit, ook niet in de Hub. ${bron('gegenereerd')}</p>
  </div>

  <div class="flex flex-col gap-1.5">
    <label for="tz" class="veld-label">Tijdzone</label>
    <p id="tz-hulp" class="veld-hulp">Standaardwaarde van het platform; je mag hem aanpassen. ${bron('standaard')}</p>
    <select id="tz" class="invoer max-w-72" aria-describedby="tz-hulp"><option>Europe/Amsterdam</option><option>UTC</option></select>
  </div>

  ${melding('info', 'info', '<p>Ingevulde waarden worden bewaard. Je kunt later verder via <strong>Apps → Installaties</strong>.</p>')}

  <div class="fixed inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] z-20 flex gap-2 border-t border-border bg-card p-3 lg:static lg:border-0 lg:bg-transparent lg:p-0 lg:pt-2" data-actiebalk>
    ${knop('Vorige', { soort: 'stil', ic: 'chevron-left' })}
    <span class="flex-1"></span>
    ${knop('Opslaan en later verder', { soort: 'secundair', extra: 'hidden sm:inline-flex' })}
    <button type="submit" class="knop knop-primair"><span>Volgende: controle vooraf</span>${i('chevron-right')}</button>
  </div>
</form>`;
  return shell({ pagina: 'apps', zijHuidig: 'server', titel: 'Voorbeeld-app installeren — stap 2 van 7: parameters', inhoud });
}
