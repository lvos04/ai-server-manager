// Genereert uit bouw/tokens.mjs:
//   ../tokens.json        DTCG-bron (licht als $value, donker in $extensions["nl.peil"].modes.donker)
//   ../ontwerptaal.css    Tailwind 4 + shadcn/ui-variabelen, direct te importeren
//   ../statuspagina.css   kleine framework-vrije CSS voor de statuspagina's (zonder JS, prefers-color-scheme)
// Gebruik: node bouw/genereer.mjs
import fs from 'node:fs';
import crypto from 'node:crypto';
import { META, KLEUREN, ALIASSEN, MATEN, TYPO } from './tokens.mjs';

const D = new URL('../', import.meta.url).pathname;
const licht = Object.fromEntries(KLEUREN.map(([k, l]) => [k, l]));
const donker = Object.fromEntries(KLEUREN.map(([k, , d]) => [k, d]));
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');

// ─────────────────────────────────────────────── tokens.json (DTCG) ───────────────────────────────────────────────
const tw = (k) => `bg-${k} / text-${k} / border-${k}`;
const dtcg = {
  $description: `${META.naam} ${META.versie} — ${META.omschrijving} GEGENEREERD uit bouw/tokens.mjs; niet met de hand wijzigen.`,
  $extensions: { 'nl.peil': { naam: META.naam, versie: META.versie, datum: META.datum, modi: ['licht', 'donker'], modusregel: 'licht = $value; donker = $extensions["nl.peil"].modes.donker. CSS: :root = licht; .dark en [data-theme="dark"] = donker; statuspagina: prefers-color-scheme.' } },
  kleur: {},
  maat: {},
  typografie: { familie: {}, rol: {} },
};
for (const [k, l, d, groep, wat] of KLEUREN) {
  dtcg.kleur[groep] ??= {};
  dtcg.kleur[groep][k] = { $type: 'color', $value: l, $description: wat, $extensions: { 'nl.peil': { modes: { donker: d }, css: `--${k}`, tailwind: tw(k) } } };
}
const groepVan = Object.fromEntries(KLEUREN.map(([k, , , g]) => [k, g]));
dtcg.kleur.alias = {};
for (const [k, naar, wat] of ALIASSEN) dtcg.kleur.alias[k] = { $type: 'color', $value: `{kleur.${groepVan[naar]}.${naar}}`, $description: wat, $extensions: { 'nl.peil': { css: `--${k}` } } };
for (const [k, v, t, wat] of MATEN) dtcg.maat[k] = { $type: t, $value: t === 'number' ? Number(v) : v, $description: wat, $extensions: { 'nl.peil': { css: `--${k}` } } };
dtcg.typografie.familie.sans = { $type: 'fontFamily', $value: TYPO.sans, $description: 'Systeemfont: 0 KB, geen fontbestanden (ook bruikbaar op de statuspagina\'s). Inter/Space Grotesk/JetBrains Mono vervallen.' };
dtcg.typografie.familie.mono = { $type: 'fontFamily', $value: TYPO.mono, $description: 'Systeem-mono voor codes, trace-ID, digest, logs.' };
for (const [r, cls, size, lh, w, wat] of TYPO.rollen) dtcg.typografie.rol[r] = { $type: 'typography', $value: { fontFamily: '{typografie.familie.sans}', fontSize: size, lineHeight: lh, fontWeight: w }, $description: `${wat} Tailwind: ${cls}.` };
const tokensJson = JSON.stringify(dtcg, null, 2) + '\n';
fs.writeFileSync(D + 'tokens.json', tokensJson);

// ─────────────────────────────────────────────── ontwerptaal.css ──────────────────────────────────────────────────
const blok = (t, ins = '  ') => Object.entries(t).map(([k, v]) => `${ins}--${k}: ${v};`).join('\n');
const groepen = [...new Set(KLEUREN.map((r) => r[3]))];
const perGroep = (t) => groepen.map((g) => `  /* ${g} */\n` + KLEUREN.filter((r) => r[3] === g).map(([k]) => `  --${k}: ${t[k]};`).join('\n')).join('\n');
const alias = ALIASSEN.map(([k, naar]) => `  --${k}: var(--${naar});`).join('\n');
const alleKleurNamen = [...KLEUREN.map((r) => r[0]), ...ALIASSEN.map((r) => r[0])];
const themeInline = alleKleurNamen.map((k) => `  --color-${k}: var(--${k});`).join('\n');
const maten = MATEN.map(([k, v]) => `  --${k}: ${v};`).join('\n');

const css = `/* ==================================================================================================================
   ${META.naam} ${META.versie} — ontwerptaal TrueNAS Home Platform V2
   Tailwind CSS 4 + shadcn/ui (new-york, CSS-variabelen) + lucide-react.
   GEGENEREERD door bouw/genereer.mjs uit bouw/tokens.mjs (bron: tokens.json). Niet met de hand wijzigen.
   Herkomst: ai-server-manager (bron van waarheid). Kopie in een andere repo: zet de herkomstkop + sha256 erboven.

   Gebruik (Next 16 / Vite + @tailwindcss/vite):
       @import "tailwindcss";
       @import "./ontwerptaal.css";
   Donker: klasse .dark óf [data-theme="dark"] op <html>. Het themascript zet ALTIJD het opgeloste thema, ook bij
   "Systeem" (luistert naar matchMedia). Standaard: Systeem.
   Contrast en paletvalidatie: contrast.json. Betekenisregels: ONTWERPTAAL.md §4.
   ================================================================================================================== */

@custom-variant dark (&:where(.dark, .dark *, [data-theme="dark"], [data-theme="dark"] *));

/* ── Licht (standaard) ─────────────────────────────────────────────────────────────────────────────────────────── */
:root {
  color-scheme: light;
${perGroep(licht)}
  /* shadcn-afgeleiden en aliassen */
${alias}
  /* maten */
${maten}
  --shadow-color: 215 25% 10%;
}

/* ── Donker (eigen stappen, geen automatische omkering) ────────────────────────────────────────────────────────── */
.dark,
[data-theme="dark"] {
  color-scheme: dark;
${perGroep(donker)}
  --shadow-color: 0 0% 0%;
}

/* ── Tailwind-thema ────────────────────────────────────────────────────────────────────────────────────────────── */
/* Alleen tokenkleuren compileren: de Tailwind-standaardkleuren (red-500, green-600, …) bestaan niet. */
@theme {
  --color-*: initial;
  --color-white: #ffffff;
  --color-black: #000000;
}

@theme inline {
${themeInline}

  --radius-sm: calc(var(--radius) - 4px);  /* 4 px: risicotag, code, kbd */
  --radius-md: calc(var(--radius) - 2px);  /* 6 px */
  --radius-lg: var(--radius);              /* 8 px: kaart, knop, veld */
  --radius-xl: calc(var(--radius) + 4px);  /* 12 px: dialoog, sheet */
}

@theme {
  --font-sans: ${TYPO.sans};
  --font-mono: ${TYPO.mono};
  /* Typeschaal: Tailwind-standaard (text-sm 14 · base 16 · lg 18 · xl 20 · 2xl 24 · 3xl 30 · 5xl 48).
     text-xs (12 px) is verboden voor inhoud (lintregel); kleinste tekst is text-sm. */

  --spacing-touch: 2.75rem;        /* 44 px: h-touch, min-h-touch, size-touch */
  --spacing-header: 4rem;
  --spacing-bottomnav: 4rem;
  --spacing-sidebar: 16rem;
  --spacing-content: 76rem;
  /* Regellengte: gebruik max-w-prose (Tailwind-standaard 65ch). Geen --spacing-prose: die botste met max-w-prose. */

  /* z-lagen als Tailwind-utilities: z-sticky, z-nav, z-overlay, z-toast (review 1.1.0: --z-* alleen in :root gaf geen utility). */
  --z-index-sticky: 20;
  --z-index-nav: 30;
  --z-index-overlay: 40;
  --z-index-toast: 50;

  --shadow-sm: 0 1px 2px hsl(var(--shadow-color) / 0.10);
  --shadow-md: 0 4px 12px hsl(var(--shadow-color) / 0.14), 0 1px 3px hsl(var(--shadow-color) / 0.10);
  --shadow-lg: 0 12px 32px hsl(var(--shadow-color) / 0.20), 0 2px 6px hsl(var(--shadow-color) / 0.12);

  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-exit: cubic-bezier(0.4, 0, 1, 1);
  --default-transition-duration: 150ms;
  --default-transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  /* Breekpunten: Tailwind-standaard. Navigatiewissel op lg = 1024 px. */
}

/* ── Basislaag ─────────────────────────────────────────────────────────────────────────────────────────────────── */
@layer base {
  html {
    -webkit-text-size-adjust: 100%;
    text-size-adjust: 100%;
    /* Focus mag nooit achter de sticky kopbalk of ondernavigatie verdwijnen (WCAG 2.4.11). */
    scroll-padding-top: calc(var(--header-h) + 0.75rem);
    scroll-padding-bottom: calc(var(--bottomnav-h) + var(--actiebalk-h, 0px) + env(safe-area-inset-bottom, 0px) + 0.75rem);
  }
  /* Pagina met een vaste actiebalk boven de ondernavigatie (wizard, preview op mobiel). */
  html:has([data-actiebalk]) { --actiebalk-h: 4.5rem; }
  @media (width >= 64rem) {
    html { scroll-padding-bottom: 0.75rem; }
    /* 1.1.1 (Hub-review R-03): de kindschil houdt op elke breedte een ondernavigatie; zet data-schil="kind" op de schil. */
    html:has([data-schil="kind"]) { scroll-padding-bottom: calc(var(--bottomnav-h) + env(safe-area-inset-bottom, 0px) + 0.75rem); }
  }
  body {
    background: var(--background);
    color: var(--foreground);
    font-family: var(--font-sans);
    font-size: 1rem;
    line-height: 1.5rem;
  }
  *, ::before, ::after { border-color: var(--border); }
  h1, h2, h3, h4 { font-weight: 700; text-wrap: balance; }
  p, li, dd { text-wrap: pretty; }
  a { color: var(--link); text-decoration-line: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; }
  a:hover { text-decoration-thickness: 2px; }
  code, kbd, samp, pre { font-family: var(--font-mono); font-size: max(0.9375em, 0.875rem); }
  /* Paden, digests, ID's: breken waar nodig, nooit horizontale overloop of afkappen (reflow 320 px). */
  :where(code, kbd, samp, .font-mono) { overflow-wrap: anywhere; }
  /* 1.1.1 (Hub-review R-26, E12): een lang woord zonder breekpunt (variabelenaam, foutnaam) breekt in plaats van over te
     lopen; nodig omdat het systeemfont per machine breder kan zijn (DejaVu Sans op de CI-runner). */
  :where(main) { overflow-wrap: break-word; }
  /* 1.1.1 (Hub-review R-16): een icoon in een lange regel krimpt nooit tot een stip. */
  :where(svg.lucide) { flex-shrink: 0; }
  input, select, textarea { font-size: max(1rem, 16px); }
  ::placeholder { color: var(--muted-foreground); opacity: 1; }
  ::selection { background: var(--primary); color: var(--primary-foreground); }
  :focus-visible,
  /* 1.1.1 (Hub-review R-02, C-66): in een datum- of tijdveld kan de focus op de kalenderknop binnen het veld staan; dan
     geldt :focus-visible niet op het veld. De ring staat daarom ook op :focus-within. */
  :where(input[type="date"], input[type="time"], input[type="datetime-local"], input[type="month"], input[type="week"]):focus-within {
    outline: var(--focus-width) solid var(--ring);
    outline-offset: var(--focus-offset);
    box-shadow: 0 0 0 var(--focus-offset) var(--ring-halo);
  }
  /* Preflight haalt nummering weg; geordende lijsten met betekenis (runbook, stappen) houden nummers. */
  ol[data-genummerd] { list-style: decimal; padding-left: 1.5rem; }
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  /* Windows-hoogcontrast: alleen de randkleur forceren, de randSTIJL (stippel = onbekend) blijft. */
  @media (forced-colors: active) {
    [data-status], [data-risico], [data-as] { border-color: CanvasText !important; }
    :focus-visible { outline-color: Highlight; }
    /* 1.1.1 (MSO-review R-20): een vlak of een inset-balk (box-shadow) verdwijnt in forced colors. Het actieve
       navigatie-item, de gekozen tab en een ingedrukte keuzeknop krijgen daarom een onderstreping in Highlight. */
    [aria-current="page"], [aria-current="step"], [aria-selected="true"], [aria-pressed="true"] {
      text-decoration-line: underline !important;
      text-decoration-thickness: 3px !important;
      text-underline-offset: 4px;
      text-decoration-color: Highlight !important;
    }
  }
}

/* ── Platform-utilities ────────────────────────────────────────────────────────────────────────────────────────── */
/* Verouderd waardevak: 135°-arcering, toon-op-toon. */
@utility arcering {
  background-color: var(--stale-bg);
  background-image: repeating-linear-gradient(135deg, var(--stale-hatch) 0 2px, transparent 2px 9px);
}
/* Gat / geen meting in een grafiek of balk. */
@utility arcering-gat {
  background-image: repeating-linear-gradient(135deg, var(--chart-gap) 0 1.5px, transparent 1.5px 7px);
}
/* Geschat (T-03): 45°, gespiegeld t.o.v. verouderd. */
@utility arcering-geschat {
  background-image: repeating-linear-gradient(45deg, currentColor 0 1.5px, transparent 1.5px 6px);
}
/* Expliciete focusring voor componenten die outline-none meekregen (shadcn-codemod: zie components.json-advies). */
@utility focus-ring {
  &:focus-visible {
    outline: var(--focus-width) solid var(--ring);
    outline-offset: var(--focus-offset);
    box-shadow: 0 0 0 var(--focus-offset) var(--ring-halo);
  }
}
@utility cijfers { font-variant-numeric: tabular-nums; }
@utility min-touch { min-height: var(--touch); min-width: var(--touch); }
`;
fs.writeFileSync(D + 'ontwerptaal.css', css);

// ─────────────────────────────────────────────── statuspagina.css ─────────────────────────────────────────────────
// Bron: bouw/statuspagina.bron.css (semantische klassen met var(--x)). Alleen gebruikte variabelen, in hex.
const bron = fs.readFileSync(D + 'bouw/statuspagina.bron.css', 'utf8');
const gebruikt = [...new Set([...bron.matchAll(/var\(--([a-z0-9-]+)\)/g)].map((m) => m[1]))].filter((k) => k in licht);
const varsL = gebruikt.map((k) => `--${k}:${licht[k]}`).join(';');
const varsD = gebruikt.map((k) => `--${k}:${donker[k]}`).join(';');
const mini = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, ' ').replace(/\s*([{}:;,>])\s*/g, '$1').replace(/;}/g, '}').trim();
const kern = `:root{color-scheme:light dark;${varsL}}@media (prefers-color-scheme:dark){:root{${varsD}}}` + mini(bron);
const spKop = `/*! ${META.naam} statuspagina.css ${META.versie} · bron ai-server-manager/design/ontwerptaal · sha256:${sha(kern).slice(0, 16)} */\n`;
const sp = spKop + kern + '\n';
fs.writeFileSync(D + 'statuspagina.css', sp);

// ─────────────────────────────────────────────── statuspagina.html (sjabloon) ─────────────────────────────────────
const ICONEN = JSON.parse(fs.readFileSync(D + 'bouw/iconen.json', 'utf8'));
// 1.1.1 (E03/E04): elke toon heeft een eigen symbool met dezelfde naam (#i-<toon>), zodat een rij nooit het icoon van een
// andere betekenis krijgt (ONTWERPTAAL §7). 'feit' = neutraal feit (info-icoon in inkt), geen gezondheid.
const ICOON = { gezond: 'circle-check', beperkt: 'triangle-alert', storing: 'octagon-x', onbekend: 'circle-help', gate: 'lock', info: 'info', gekoppeld: 'link-2', niet_gekoppeld: 'link-2-off',
  verouderd: 'clock-alert', niet_beschikbaar: 'circle-slash', nog_niet: 'hourglass', beleid: 'ban', feit: 'info' };
let sj = fs.readFileSync(D + 'bouw/statuspagina.sjabloon.html', 'utf8').replace('/*STATUSPAGINA_CSS*/', sp.trim()).replace('{{peil_versie}}', META.versie);
for (const [k, n] of Object.entries(ICOON)) sj = sj.replaceAll(`{{icoon_${k}}}`, ICONEN[n]);
fs.writeFileSync(D + 'statuspagina.html', sj);
console.log('statuspagina.html (sjabloon)', Buffer.byteLength(sj), 'B');

console.log('tokens.json', tokensJson.length, 'B ·', KLEUREN.length, 'kleuren +', ALIASSEN.length, 'aliassen');
console.log('ontwerptaal.css', css.length, 'B');
console.log('statuspagina.css', Buffer.byteLength(sp), 'B (', gebruikt.length, 'variabelen ) gzip', (await import('node:zlib')).gzipSync(sp).length, 'B');
