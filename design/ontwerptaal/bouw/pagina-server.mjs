// S-031 Server → Metrieken (B01-004, B09-001, B09-003). Vorm volgens de dataviz-procedure: huidige waarden als
// StatKaart, verhouding tot een grens als meter, trend als lijn met één y-as; de twee GPU's als small multiples (zelfde
// schaal, elk één reeks) zodat A310 en UHD 770 nooit verwisseld of op één as gemengd worden. Alle data fictief.
import { i, status, kwaliteit, meta, knop, melding, shell, paginakop, kruimel, lijngrafiek, nb, voorbeeld } from './ui.mjs';

const reeks = (waarden, start = 6 * 60) => waarden.map((v, k) => { const m = start + k * 15; return { t: `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`, v }; });

// Meter (C-32) met eigen id (de gedeelde helper leidt het id af van de labellengte).
const meter = ({ id, label, waarde, max, eenheid, tekst, drempel = 0.9 }) => {
  const f = waarde / max, boven = f >= drempel, pct = Math.round(f * 100);
  return `<div class="flex flex-col gap-2">
  <div class="flex flex-wrap items-baseline justify-between gap-x-3"><span class="font-semibold" id="${id}">${label}</span><span><span class="text-2xl font-semibold">${nb(tekst[0])}</span> <span class="text-muted-foreground">van ${nb(tekst[1])}</span></span></div>
  <div class="h-3 overflow-hidden rounded-full ${boven ? 'bg-degraded-bg ring-1 ring-degraded' : 'bg-chart-meter-track'}" role="meter" aria-valuemin="0" aria-valuemax="${max}" aria-valuenow="${waarde}" aria-valuetext="${tekst[0]} van ${tekst[1]} (${pct}%)${boven ? ', boven de drempel' : ''}" aria-labelledby="${id}"><div class="h-full rounded-full ${boven ? 'bg-degraded' : 'bg-chart-1'}" style="width:${pct}%"></div></div>
  ${boven ? `<p class="flex items-center gap-1.5 text-sm font-semibold text-degraded-ink">${i('triangle-alert', 'size-4 text-degraded')}${pct}% van de grens — boven de drempel van ${Math.round(drempel * 100)}%</p>` : `<p class="text-sm text-muted-foreground">${pct}% gebruikt</p>`}
</div>`;
};

const tegel = ({ id, titel, ic, inhoud, metaHtml, variant = '' }) => `<article class="kaart ${variant}" aria-labelledby="${id}"><h3 id="${id}" class="kaart-titel">${i(ic)}${titel}</h3>${inhoud}${metaHtml}</article>`;

export function serverMetrieken() {
  const sub = `<nav aria-label="Server" class="mb-6"><ul class="flex flex-wrap gap-2">
    ${[['Overzicht', '#'], ['Apps', 'apps.html'], ['Metrieken', 'server-metrieken.html'], ['Meetdekking', '#'], ['Logs', '#']].map(([l, h]) => `<li><a href="${h}" class="sub-item"${l === 'Metrieken' ? ' aria-current="page"' : ''}>${l}</a></li>`).join('')}
  </ul></nav>`;

  const periode = `<div class="flex flex-wrap items-center gap-2" role="group" aria-label="Periode">
    <span class="mr-1 text-sm font-semibold">Periode</span>
    ${['1 u', '6 u', '24 u', '7 d', '30 d'].map((p) => `<button type="button" class="knop ${p === '6 u' ? 'knop-primair' : 'knop-secundair'} knop-klein" aria-pressed="${p === '6 u'}">${nb(p)}</button>`).join('')}
    <span class="basis-full text-sm text-muted-foreground sm:basis-auto">Ruwe metingen tot 6 u; 7 d per 5 min; langer per uur.</span>
  </div>`;

  const kpi = `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    ${tegel({ id: 't-cpu', titel: 'CPU-gebruik', ic: 'cpu', inhoud: `<p><span class="waarde">23</span> <span class="eenheid">%</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">alle threads samen, nu</p>`, metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
    ${tegel({ id: 't-temp', titel: 'CPU-temperatuur', ic: 'thermometer', inhoud: `<p><span class="waarde">48</span> <span class="eenheid">${nb('°C')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">heetste kern</p>`, metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
    ${tegel({ id: 't-mem', titel: 'Geheugen', ic: 'memory-stick', inhoud: meter({ id: 'm-geheugen', label: 'Gebruikt', waarde: 41.2, max: 62.6, eenheid: 'GiB', tekst: ['41,2 GiB', '62,6 GiB'] }), metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
    ${tegel({ id: 't-arc', titel: 'ZFS-cache (ARC)', ic: 'database', inhoud: `<p><span class="waarde">22,1</span> <span class="eenheid">GiB</span> ${kwaliteit('gemeten')}</p><p class="text-sm">Trefkans <strong>97%</strong> ${kwaliteit('gemeten')}</p>`, metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
  </div>`;

  const cpu = lijngrafiek({ id: 'g-cpu', titel: 'CPU-gebruik', beschrijving: 'Afgelopen 6 u, per kwartier. Schommelt tussen 12 en 41%. Tussen 08:15 en 08:45 was er geen meting.',
    punten: reeks([18, 21, 19, 24, 27, 31, 29, 33, 35, null, null, null, 38, 41, 36, 30, 26, 22, 25, 28, 24, 20, 17, 23]), ymax: 100, ystap: 25, eenheid: '%', bron: 'TrueNAS (reporting.realtime)', bijgewerkt: '11:56', reeksnaam: 'CPU' });

  const gpuA = lijngrafiek({ id: 'g-a310', titel: 'Intel Arc A310 — gebruik', beschrijving: 'Afgelopen 6 u, per kwartier. AV1-taken pieken tot 78%.',
    punten: reeks([4, 6, 52, 71, 78, 64, 12, 8, 5, 3, 44, 69, 75, 58, 9, 6, 4, 61, 73, 66, 14, 7, 5, 31]), ymax: 100, ystap: 25, eenheid: '%', bron: 'Beszel', bijgewerkt: '11:55', reeksnaam: 'A310' });
  const gpuU = lijngrafiek({ id: 'g-uhd770', titel: 'Intel UHD 770 — gebruik', beschrijving: 'Afgelopen 6 u, per kwartier. Geen meting meer na 09:45; daarna verouderd.',
    punten: reeks([9, 11, 8, 14, 22, 18, 12, 10, 9, 13, 16, 12, 10, 8, 11, 9, null, null, null, null, null, null, null, null]), ymax: 100, ystap: 25, eenheid: '%', bron: 'Beszel', bijgewerkt: '09:45', reeksnaam: 'UHD 770', verouderd: 'Verouderd sinds 09:45' });

  const onbekendTemp = (gpu) => `<div class="rounded-md border-2 border-dashed border-unknown bg-unknown-bg p-3 text-unknown-ink"><p class="flex flex-wrap items-center gap-2 font-semibold">${i('circle-help', 'size-5 text-unknown')}Temperatuur: Onbekend</p><p class="mt-1 text-sm">Geen bron levert de temperatuur van de ${gpu}. We tonen geen schatting en nooit 0&nbsp;°C.</p></div>`;
  const gpus = `<section aria-labelledby="gpu-titel" class="flex flex-col gap-4">
  <h2 id="gpu-titel" class="text-xl font-bold">GPU's</h2>
  <p class="max-w-prose text-sm">Elke GPU heeft een eigen grafiek met dezelfde schaal (0–100%). De koppeling loopt via het PCI-slot, nooit via de naam van het apparaat in <span class="font-mono">/dev/dri</span>.</p>
  <div class="grid gap-4 xl:grid-cols-2 xl:items-start">
      ${tegel({ id: 't-a310', titel: 'Intel Arc A310', ic: 'microchip', inhoud: `<p class="font-mono text-sm">PCI 0000:03:00.0 ${voorbeeld()}</p><div class="grid gap-3 sm:grid-cols-2"><p><span class="waarde">31</span> <span class="eenheid">%</span> ${kwaliteit('gemeten')}<span class="block text-sm text-muted-foreground">gebruik nu</span></p><p><span class="waarde">18</span> <span class="eenheid">W</span> ${kwaliteit('gemeten')}<span class="block text-sm text-muted-foreground">vermogen nu</span></p></div>${onbekendTemp('A310')}`, metaHtml: meta({ bron: 'Beszel (gebruik, vermogen)', tijd: '11:55', rel: '1 min geleden' }) })}
      <div class="min-w-0 xl:order-3">${gpuA}</div>
      ${tegel({ id: 't-uhd', titel: 'Intel UHD 770', ic: 'microchip', variant: 'kaart-verouderd xl:order-2', inhoud: `<p class="font-mono text-sm">PCI 0000:00:02.0 ${voorbeeld()}</p><div class="flex flex-wrap gap-2">${status('onbekend', 'Onbekend')}${status('verouderd', 'Verouderd')}</div>
        <div class="waardevak-verouderd"><p class="text-sm font-semibold text-foreground">Laatst bekend · 09:45</p><p><span class="waarde">9</span> <span class="eenheid">%</span><span class="sr-only"> (laatst bekende waarde, verouderd)</span> <span class="text-sm text-muted-foreground">gebruik</span></p></div>
        <p class="reden">Beszel levert sinds 09:45 geen nieuwe meting voor deze GPU.</p>
        <div class="rounded-md border-2 border-dashed border-unknown bg-unknown-bg p-3 text-unknown-ink"><p class="flex flex-wrap items-center gap-2 font-semibold">${i('circle-slash', 'size-5 text-unknown')}Vermogen: Niet beschikbaar</p><p class="mt-1 text-sm">Beszel levert geen vermogen voor deze GPU. <code class="code-inline">capability_unavailable</code></p></div>
        ${onbekendTemp('UHD 770')}`, metaHtml: meta({ bron: 'Beszel', tijd: '09:45', rel: '2 u 11 min geleden', poging: '11:55 (geen meting voor deze GPU)' }) })}
      <div class="min-w-0 xl:order-4">${gpuU}</div>
  </div>
</section>`;

  const opslag = `<section aria-labelledby="pool-titel" class="kaart gap-4">
  <h2 id="pool-titel" class="text-xl font-bold">Opslag</h2>
  <div class="grid gap-6 md:grid-cols-2">
    ${meter({ id: 'm-pool1', label: 'voorbeeldpool', waarde: 5.1, max: 7.2, eenheid: 'TiB', tekst: ['5,1 TiB', '7,2 TiB'] })}
    ${meter({ id: 'm-pool2', label: 'back-uppool', waarde: 6.7, max: 7.2, eenheid: 'TiB', tekst: ['6,7 TiB', '7,2 TiB'] })}
  </div>
  ${meta({ bron: 'TrueNAS (pool.query)', tijd: '11:54', rel: '2 min geleden' })}
</section>`;

  const netwerk = `<div class="grid gap-4 sm:grid-cols-2">
    ${tegel({ id: 't-in', titel: 'Netwerk ontvangen', ic: 'download', inhoud: `<p><span class="waarde">12,4</span> <span class="eenheid">${nb('Mbit/s')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">alle interfaces samen, nu</p>`, metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
    ${tegel({ id: 't-uit', titel: 'Netwerk verzonden', ic: 'send', inhoud: `<p><span class="waarde">3,1</span> <span class="eenheid">${nb('Mbit/s')}</span> ${kwaliteit('gemeten')}</p><p class="text-sm text-muted-foreground">alle interfaces samen, nu</p>`, metaHtml: meta({ bron: 'TrueNAS (reporting.realtime)', tijd: '11:56', rel: 'zojuist' }) })}
  </div>`;

  const dekking = `<section aria-labelledby="dk-titel" class="kaart">
  <h2 id="dk-titel" class="text-xl font-bold">Meetdekking</h2>
  <p><strong>14 van 19</strong> metrieken hebben nu een verse bron. Hiaten: GPU-temperatuur (beide GPU's), schijftemperatuur, CPU en geheugen per app.</p>
  ${melding('info', 'info', '<p>Het Beszel-systeem <strong>mini-pc</strong> telt niet mee: die hoort niet bij het platform (D10).</p>')}
  <a href="#" class="knop knop-secundair knop-blok mt-1 sm:w-fit"><span>Meetdekking bekijken</span>${i('chevron-right')}</a>
</section>`;

  const inhoud = paginakop({
    kruimel: kruimel([['Server', '#'], ['Metrieken', '']]),
    titel: 'Metrieken',
    omschrijving: 'Live metingen van de NAS met bron en tijd. Wat geen verse bron heeft, staat als onbekend — nooit als 0.',
    bijgewerkt: 'Bijgewerkt <time datetime="2026-11-09T11:56:00+01:00">11:56</time> (zojuist) · vernieuwt elke 60 s',
    acties: knop('Vernieuwen', { ic: 'refresh-cw' }),
  }) + sub + `<div class="flex flex-col gap-6">${periode}<h2 class="sr-only">Nu</h2>${kpi}${cpu}${gpus}${opslag}${netwerk}${dekking}</div>`;
  return shell({ pagina: 'server', titel: 'Server — metrieken', inhoud });
}
