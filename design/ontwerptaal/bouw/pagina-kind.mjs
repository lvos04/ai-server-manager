// S-021 Home (kindvariant) in de kinderschil: Home · Kijken · Zoeken · Ik. Geen beheer, geen codes in beeld.
import { i, shell, voorbeeld } from './ui.mjs';
export function kind() {
  const titel = (t, rest) => `<li><a href="#" class="flex min-h-touch items-center gap-3 rounded-lg border border-border bg-card p-3 text-foreground no-underline hover:bg-accent"><span class="flex size-12 shrink-0 items-center justify-center rounded-md bg-muted">${i('film', 'size-6 text-muted-foreground')}</span><span class="min-w-0 flex-1"><span class="block font-semibold">${t}</span><span class="text-sm text-muted-foreground">${rest}</span></span>${i('play', 'size-6 shrink-0')}<span class="sr-only"> (opent Jelly Leon in een nieuw tabblad)</span></a></li>`;
  const inhoud = `
<h1 class="mb-1 text-2xl font-bold">Hoi Sam</h1>
<p class="mb-6 text-muted-foreground">Hier zie je wat je kunt kijken.</p>
<section aria-labelledby="verder" class="mb-6 flex flex-col gap-3">
  <h2 id="verder" class="text-xl font-bold">Verder kijken</h2>
  <ul class="flex flex-col gap-2">${titel('Ruimteavontuur', 'Aflevering 4 · nog 12 minuten')}${titel('Dierenbos', 'Film · halverwege')}</ul>
</section>
<section aria-labelledby="vragen" class="mb-6 flex flex-col gap-3">
  <h2 id="vragen" class="text-xl font-bold">Wat je hebt gevraagd</h2>
  <ul class="flex flex-col gap-2">
    <li class="kaart flex-row items-center gap-3">${i('hourglass', 'size-6 shrink-0 text-info')}<span><span class="block font-semibold">Robotvrienden</span><span class="text-sm">Een volwassene kijkt ernaar.</span></span></li>
    <li class="kaart flex-row items-center gap-3">${i('play', 'size-6 shrink-0 text-foreground')}<span><span class="block font-semibold">Zeehondenklas</span><span class="text-sm">Je kunt kijken.</span></span></li>
  </ul>
</section>
<section aria-labelledby="mis" class="flex flex-col gap-3">
  <h2 id="mis" class="text-xl font-bold">Even niet</h2>
  <div class="melding melding-onbekend flex-col sm:flex-row">${i('circle-help')}<div><p class="font-semibold">Zoeken werkt nu even niet.</p><p class="mt-1">Er ging iets mis. Vraag het aan een volwassene.</p>
    <details class="mt-2"><summary class="inline-flex min-h-touch cursor-pointer items-center gap-2 font-semibold">${i('chevron-down', 'size-5 klap-icoon')}Details voor een volwassene</summary><p class="text-sm">Code <code class="code-inline">upstream_timeout</code> · Trace-ID</p><code class="code-veld mt-1">2b9f6c10-8d4e-4a71-b3c5-6e0d9a2f7b18</code></details></div></div>
</section>
<p class="mt-6 text-sm text-muted-foreground">${voorbeeld()} Kinderprofiel: alleen titels die voor jou zijn toegestaan.</p>`;
  return shell({ pagina: 'kind', titel: 'Home (kinderprofiel)', inhoud, kind: true });
}
