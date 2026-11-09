// S-090 Huis (kamerkaart), S-092 klimaat (Gree-zone, conflict, handmatig), S-093 energie met boiler ALLEEN LEZEN.
import { i, status, kwaliteit, meta, knop, shell, paginakop, melding, nb, deeplink } from './ui.mjs';

const chip = (soort, ic, t) => `<span class="inline-flex min-h-8 items-center gap-1.5 rounded-md bg-domain-${soort}-bg px-2.5 text-sm font-semibold text-domain-${soort}-ink">${i(ic, 'size-4')}${t}</span>`; // icoon in de inkt: domeinkleur op het eigen vlak haalt in licht maar 2,7–2,8:1 (review 1.1.0)

export function huis() {
  const woonkamer = `
<article class="kaart" aria-labelledby="k-woon" data-testid="kaart-woonkamer">
  <h2 id="k-woon" class="kaart-titel">${i('sofa')}Woonkamer</h2>${status('gezond')}
  <div class="grid grid-cols-2 gap-3">
    <div><p class="text-sm font-semibold text-muted-foreground">Temperatuur</p><p><span class="waarde">20,5</span> <span class="eenheid">°C</span></p>${kwaliteit('gemeten')}</div>
    <div><p class="text-sm font-semibold text-muted-foreground">Luchtvochtigheid</p><p><span class="waarde">48</span> <span class="eenheid">%</span></p>${kwaliteit('gemeten')}</div>
  </div>
  <div class="flex flex-col gap-2 rounded-lg border border-border p-3">
    <div class="flex flex-wrap items-center justify-between gap-2"><span class="font-semibold" id="doel-l">Doel</span>${chip('heat', 'flame', 'Verwarmen')}</div>
    <div class="flex items-center gap-3" role="group" aria-labelledby="doel-l">
      <button type="button" class="knop knop-secundair knop-icoon" aria-label="Doel 0,5 graad lager">${i('minus')}</button>
      <output class="min-w-24 text-center text-2xl font-semibold cijfers" aria-live="polite">${nb('21,0 °C')}</output>
      <button type="button" class="knop knop-secundair knop-icoon" aria-label="Doel 0,5 graad hoger">${i('plus')}</button>
    </div>
    <p class="flex items-center gap-2 text-sm font-semibold" role="status">${i('loader-circle', 'size-4')}Verstuurd — wacht op bevestiging van my_house</p>
  </div>
  <div class="flex flex-col gap-2">
    <p class="font-semibold">Verlichting</p>
    <div class="grid grid-cols-2 gap-2">
      <button type="button" class="flex min-h-touch flex-col items-start gap-1 rounded-lg border-2 border-domain-light-on bg-domain-light-on-bg p-3 text-left text-domain-light-on-ink" aria-pressed="true">${i('lightbulb', 'size-5')}<span class="font-semibold">Plafondlamp</span><span class="text-sm">Aan · 80%</span></button>
      <button type="button" class="flex min-h-touch flex-col items-start gap-1 rounded-lg border border-border-strong bg-card p-3 text-left" aria-pressed="false">${i('lightbulb-off', 'size-5 text-muted-foreground')}<span class="font-semibold">Leeslamp</span><span class="text-sm text-muted-foreground">Uit</span></button>
    </div>
  </div>
  ${meta({ bron: 'my_house (Zigbee-sensor woonkamer)', tijd: '11:55', rel: '1 min geleden' })}
</article>`;

  const slaapkamer = `
<article class="kaart kaart-verouderd" aria-labelledby="k-slaap" data-testid="kaart-slaapkamer">
  <h2 id="k-slaap" class="kaart-titel">${i('sofa')}Slaapkamer</h2><div class="flex flex-wrap gap-2">${status('onbekend')}${status('verouderd')}</div>
  <div class="waardevak-verouderd"><p class="text-sm font-semibold text-foreground">Laatst bekend · 06:40</p><p><span class="waarde">18,2</span> <span class="eenheid">°C</span><span class="sr-only"> (laatst bekende waarde, verouderd)</span></p></div>
  <p class="reden">De sensor meldt zich niet sinds 06:40 (5 u geleden). De optimalisatie voor deze kamer is gestopt.</p>
  <div class="flex flex-col gap-1"><button type="button" class="knop knop-secundair" aria-disabled="true" aria-describedby="slaap-uit">${i('thermometer')}<span>Doel aanpassen</span></button><p id="slaap-uit" class="text-sm text-muted-foreground">Bediening uit: zonder verse meting stuurt de Hub niets aan.</p></div>
  ${meta({ bron: 'my_house (Zigbee-sensor slaapkamer)', tijd: '06:40', rel: '5 u geleden', poging: '11:55 (geen antwoord van de sensor)' })}
</article>`;

  const klimaat = `
<article class="kaart" aria-labelledby="k-gree" data-testid="kaart-klimaat">
  <h2 id="k-gree" class="kaart-titel">${i('fan')}Klimaat · gedeelde buitenunit</h2>
  <ul class="flex flex-col divide-y divide-border">
    <li class="flex flex-col gap-2 py-3">
      <div class="flex flex-wrap items-center gap-2"><span class="mr-auto font-semibold">Zone woonkamer</span>${chip('heat', 'flame', 'Verwarmen · 21&nbsp;°C')}</div>
      <p class="text-sm text-muted-foreground">Actieve sensor: woonkamer (vers, 11:55).</p>
      <div class="flex flex-wrap gap-2"><button type="button" class="knop border-2 border-domain-heat bg-domain-heat-bg text-domain-heat-ink hover:bg-domain-heat-bg" aria-pressed="true">${i('flame')}<span>Verwarmen</span>${i('check', 'size-4')}</button><button type="button" class="knop knop-secundair" aria-disabled="true" aria-describedby="conflict">${i('snowflake')}<span>Koelen</span></button></div>
      ${melding('gate', 'lock', '<p id="conflict"><strong>Koelen geblokkeerd.</strong> De gedeelde buitenunit verwarmt al voor deze zones. Verwarmen en koelen tegelijk kan niet (conflict).</p>')}
    </li>
    <li class="flex flex-col gap-2 py-3">
      <div class="flex flex-wrap items-center gap-2"><span class="mr-auto font-semibold">Zone werkkamer</span><span class="inline-flex min-h-8 items-center gap-1.5 rounded-md border-2 border-border-strong px-2.5 text-sm font-semibold">${i('hand', 'size-4')}Handmatig uit</span></div>
      <p class="text-sm">Uitgezet met de afstandsbediening om 10:30. <strong>Blijft uit tot je hervat</strong>; de AI en automatisering slaan deze zone over.</p>
      <div>${knop('Hervatten', { ic: 'play' })}</div>
    </li>
  </ul>
  ${meta({ bron: 'my_house (Gree-adapter)', tijd: '11:55', rel: '1 min geleden' })}
</article>`;

  const boiler = `
<article class="kaart" aria-labelledby="k-boiler" data-testid="kaart-boiler">
  <h2 id="k-boiler" class="kaart-titel">${i('shower-head', 'size-5 text-domain-boiler')}Boiler</h2>
  <div class="flex flex-wrap gap-2"><span class="inline-flex min-h-8 items-center gap-1.5 rounded-sm border-2 border-gate bg-gate-bg px-2 text-sm font-semibold text-gate-ink" data-as="beleid">${i('ban', 'size-4')}Alleen meten</span></div>
  <div class="grid grid-cols-2 gap-3">
    <div><p class="text-sm font-semibold text-muted-foreground">Vermogen nu</p><p><span class="waarde">2,1</span> <span class="eenheid">kW</span></p>${kwaliteit('gemeten')}</div>
    <div><p class="text-sm font-semibold text-muted-foreground">Vandaag</p><p><span class="waarde">3,4</span> <span class="eenheid">kWh</span></p>${kwaliteit('gemeten')}</div>
  </div>
  <p class="text-sm">Kosten vandaag ≈&nbsp;€&nbsp;1,02 ${kwaliteit('geschat')} <span class="text-muted-foreground">(vast tarief uit D-besluit, geen dynamische prijs)</span></p>
  ${melding('beleid', 'ban', '<p><strong>Schakelen is altijd uitgeschakeld (beleid).</strong> De Hub, de AI, flows en spraak kunnen de boiler niet aan- of uitzetten. Er is bewust geen schakelaar.</p>')}
  ${meta({ bron: 'Energy Socket boiler via my_house', tijd: '11:55', rel: '1 min geleden' })}
</article>`;

  // Energie vandaag: hoge segmentbalk (één geheel, ≤ 6 delen) + legenda + tabel
  const delen = [['Boiler', 3.4, 'bg-chart-3', 'gemeten'], ['Airco', 2.6, 'bg-chart-1', 'gemeten (1-fasemeter)'], ['Overig', 5.2, 'bg-chart-other', 'afgeleid: P1 min gemeten']];
  const tot = 11.2;
  const energie = `
<figure class="kaart" aria-labelledby="k-energie" data-testid="kaart-energie">
  <h2 id="k-energie" class="kaart-titel">${i('zap')}Energie vandaag</h2>
  <p><span class="waarde">11,2</span> <span class="eenheid">kWh</span> ${kwaliteit('gemeten')} <span class="text-sm text-muted-foreground">totaal (P1-meter)</span></p>
  <div class="flex h-2 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
    ${delen.map(([n, v, c]) => `<div class="${c} ${n === 'Overig' ? 'arcering-geschat text-card' : ''}" style="width:${(v / tot) * 100}%"></div>`).join('')}
  </div>
  <table class="w-full text-left text-sm"><caption class="sr-only">Energie vandaag per verbruiker</caption><thead><tr class="border-b border-border-strong"><th scope="col" class="py-1.5">Verbruiker</th><th scope="col" class="py-1.5 pl-3 text-right">kWh</th><th scope="col" class="py-1.5 pl-3 text-right">Deel</th><th scope="col" class="hidden py-1.5 pl-3 sm:table-cell">Kwaliteit</th></tr></thead>
  <tbody>${delen.map(([n, v, c, q]) => `<tr class="border-b border-border"><th scope="row" class="py-2 font-normal"><span class="flex items-center gap-2"><span class="legenda-vlak ${c} ${n === 'Overig' ? 'arcering-geschat text-card' : ''}" aria-hidden="true"></span>${n}</span><span class="block text-muted-foreground sm:hidden">${q}</span></th><td class="py-2 pl-3 text-right cijfers">${v.toLocaleString('nl-NL')}</td><td class="py-2 pl-3 text-right cijfers">${Math.round((v / tot) * 100)}%</td><td class="hidden py-2 pl-3 sm:table-cell">${q}</td></tr>`).join('')}</tbody></table>
  <p class="flex items-start gap-1.5 text-sm">${i('info', 'mt-0.5 size-4 shrink-0 text-info')}<span>Meterreset om 03:00: de waarde tot dan is gecorrigeerd (kwaliteit: <strong>afgeleid</strong>). Verbruik per airco-binnenunit bestaat niet: daar is geen meter voor.</span></p>
  <figcaption>${meta({ bron: 'P1-meter, Energy Socket en airco-meter via my_house', tijd: '11:55', rel: '1 min geleden', iso: '2026-11-09T11:55:00+01:00' })}</figcaption>
</figure>`;

  const inhoud = paginakop({ titel: 'Huis', omschrijving: 'my_house is de eigenaar van deze gegevens; de Hub toont ze en vraagt my_house om te schakelen.', bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:55:00+01:00">11:55</time> (1 min geleden)', acties: deeplink('my_house') })
    + `<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">${woonkamer}${slaapkamer}${klimaat}${boiler}${energie}</div>`;
  return shell({ pagina: 'huis', titel: 'Huis', inhoud });
}
