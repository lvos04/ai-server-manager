// Genereert de aliaslagen (migratiefase 1, "alleen uiterlijk") voor de bestaande apps in ../aliaslagen/ en meet de
// contrasten van de paren die die apps echt gebruiken. Gebruik: node bouw/aliaslagen.mjs  (na genereer.mjs)
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { KLEUREN, META } from './tokens.mjs';
const require = createRequire(import.meta.url);
const { hex: wcag } = require('wcag-contrast');
const D = new URL('../', import.meta.url).pathname;
fs.mkdirSync(D + 'aliaslagen', { recursive: true });
const L = Object.fromEntries(KLEUREN.map((r) => [r[0], r[1]])), Dk = Object.fromEntries(KLEUREN.map((r) => [r[0], r[2]]));
const kop = (app, extra) => `/* Peil ${META.versie} — aliaslaag voor ${app} (migratiefase 1: alleen uiterlijk; routes, functies, teksten en testids blijven).
   GEGENEREERD door ai-server-manager/design/ontwerptaal/bouw/aliaslagen.mjs. Kopie in de app met deze kop + sha256 (O-14); niet met de hand wijzigen.
   ${extra}
   Zie ONTWERPTAAL.md §13 voor het volledige migratiepad (fase 2 componenten, fase 3 opruimen). */\n`;

// ── MediaGuard en MSO (Tailwind 4 aanwezig; importeer eerst ontwerptaal.css, daarna mg.css, daarna dit bestand) ─────
const MG = {
  'bg': 'background', 'surface': 'card', 'raised': 'popover', 'sunken': 'muted', 'text': 'foreground', 'text-2': 'muted-foreground',
  'text-3': 'muted-foreground', 'border': 'border', 'border-soft': 'border', 'border-strong': 'border-strong', 'accent': 'primary',
  'accent-hover': 'primary-hover', 'on-accent': 'primary-foreground', 'accent-tint': 'info-bg', 'focus': 'ring', 'success': 'healthy',
  'success-tint': 'healthy-bg', 'warning': 'degraded', 'warning-tint': 'degraded-bg', 'danger': 'down', 'danger-tint': 'down-bg',
  'info': 'info', 'info-tint': 'info-bg', 'neutral-tint': 'unknown-bg', 'viz-1': 'chart-1', 'viz-2': 'chart-2', 'viz-3': 'chart-3',
  'viz-4': 'chart-4', 'viz-5': 'chart-5', 'viz-6': 'chart-other', 'viz-grid': 'chart-grid', 'lane-gpu': 'domain-lane-gpu', 'lane-cpu': 'domain-lane-cpu',
};
const mgVars = Object.entries(MG).map(([a, b]) => `  --mg-${a}: var(--${b});`).join('\n');
const mg = kop('MediaGuard (apps/web/styles/mg.css) en MSO (apps/web/styles/mg.css + mso.css)', 'Volgorde in globals.css: @import "tailwindcss"; @import "./ontwerptaal.css"; @import "./mg.css"; @import "./peil-alias.css";') + `
:root, :root[data-theme="light"], :root[data-theme="dark"] {
${mgVars}
  --mg-overlay: rgb(0 0 0 / 0.5);
  --mg-font: var(--font-sans);
  --mg-mono: var(--font-mono);
  --mg-r-sm: var(--radius-sm); --mg-r: var(--radius-lg); --mg-r-md: var(--radius-md); --mg-r-lg: var(--radius-lg); --mg-r-xl: var(--radius-xl);
  --mg-fs-11: 0.875rem; --mg-fs-12: 0.875rem; --mg-fs-13: 0.875rem;  /* ondergrens 14 px voor regels die deze variabelen gebruiken; harde px-maten (mg.css ±120, inline ±189) volgen pas in fase 2/3 */
  --mg-shadow-1: var(--shadow-sm); --mg-shadow-2: var(--shadow-md); --mg-shadow-3: var(--shadow-lg);
  --mg-ease: var(--ease-standard);
}
/* Correcties die alleen het uiterlijk raken (gemeten fouten uit onderzoek/BESTAANDE_UI.md) */
:root .btn--danger-solid, :root[data-theme] .btn--danger-solid { border-color: var(--destructive); background: var(--destructive); color: var(--destructive-foreground); } /* was 3,18:1 */
:root .icon-btn .dot-badge { background: var(--foreground); color: var(--background); font-size: 0.875rem; min-width: 1.25rem; height: 1.25rem; line-height: 1.25rem; } /* tellers neutraal, nooit rood */
:root .step--done .step-no { background: var(--foreground); border-color: var(--foreground); color: var(--background); } /* klaar ≠ gezond */
@media (pointer: coarse), (width < 64rem) { :root .btn, :root .icon-btn, :root .segmented button { min-height: 2.75rem; } :root .icon-btn { min-width: 2.75rem; } } /* MSO miste de 44 px-regels */
/* Review 1.1.0 — correcties die in 1.0.0 ontbraken (gemeten in mg.css/mso.css/av1.css, alleen gelezen) */
:root .estop[aria-pressed="true"] { background: var(--destructive); border-color: var(--destructive); color: var(--destructive-foreground); } /* was #fff op --mg-danger: in donker 2,0:1 */
:root .estop--pause, :root .estop--pause:hover { border-color: var(--paused); background: var(--paused-bg); color: var(--paused-ink); } /* pauze = Gepauzeerd (info), niet amber (ONTWERPTAAL §13.4) */
:root .estop--pause[aria-pressed="true"] { background: var(--paused); border-color: var(--paused); color: var(--primary-foreground); }
:root .diff .diff-removed { background: var(--diff-old-bg); color: var(--diff-old-ink); text-decoration-color: currentColor; } /* diff zonder rood/groen (C-20) */
:root .diff .diff-added { background: var(--diff-new-bg); color: var(--diff-new-ink); font-weight: 600; }
:root .diff .diff-changed { background: var(--diff-new-bg); }
:root .confidence .bar > span { background: var(--foreground); } /* AI-zekerheid is inkt, nooit groen (T-24) */
:root .qribbon .q-dv, :root[data-theme] .qribbon .q-dv, :root .qribbon .q-hdr, :root .qribbon .q-av1 { color: var(--foreground); background: transparent; } /* kwaliteit is geen status: geen violet/amber/groen */
:root .job-lane, :root .job-lane--gpu, :root .job-lane--cpu { color: var(--foreground); } /* tekst nooit in reekskleur (lane-cpu was 3,2:1) */
:root .job-lane--gpu .ico { color: var(--domain-lane-gpu); } :root .job-lane--cpu .ico { color: var(--domain-lane-cpu); }
:root .phase-bar--verify > span { background: var(--foreground); } /* controle-fase ≠ gezond */
:root .phase-bar--paused > span { background: var(--paused); }
:root .phase-bar--stale > span { opacity: 1; background-color: var(--stale); background-image: repeating-linear-gradient(135deg, var(--stale-hatch) 0 2px, transparent 2px 6px); } /* nooit opacity */
`;
fs.writeFileSync(D + 'aliaslagen/mediaguard-mso.css', mg);

// ── my_house (Vite, React 18, géén Tailwind: zelfstandige waarden in hex, eigen variabelenamen blijven) ─────────────
const MH = {
  'bg': 'background', 'surface': 'card', 'surface-2': 'muted', 'sunken': 'accent', 'border': 'border', 'border-strong': 'border-strong',
  'input-border': 'input', 'text': 'foreground', 'text-2': 'muted-foreground', 'muted': 'muted-foreground', 'primary': 'primary',
  'on-primary': 'primary-foreground', 'link': 'link', 'link-hover': 'primary-hover', 'focus': 'ring',
  'heat': 'domain-heat', 'heat-ink': 'domain-heat-ink', 'heat-bg': 'domain-heat-bg', 'heat-soft': 'domain-heat-soft',
  'cool': 'domain-cool', 'cool-ink': 'domain-cool-ink', 'cool-bg': 'domain-cool-bg', 'cool-soft': 'domain-cool-soft',
  'boiler': 'domain-boiler', 'light-on': 'domain-light-on-bg', 'light-ink': 'domain-light-on-ink', 'rest': 'chart-other', 'stale': 'stale-ink',
  'ok': 'healthy-ink', 'ok-bg': 'healthy-bg', 'warn': 'degraded-ink', 'warn-dot': 'degraded', 'warn-bg': 'degraded-bg', 'warn-ink': 'degraded-ink',
  'error': 'down-ink', 'error-bg': 'down-bg',
  // extra (nieuw, met voorvoegsel peil- zodat niets botst)
  'peil-unknown': 'unknown', 'peil-unknown-bg': 'unknown-bg', 'peil-unknown-ink': 'unknown-ink', 'peil-stale': 'stale', 'peil-stale-hatch': 'stale-hatch',
  'peil-disabled': 'disabled-foreground', 'peil-ring-halo': 'ring-halo',
};
const mhBlok = (t) => Object.entries(MH).map(([a, b]) => `--${a}: ${t[b]};`).join(' ');
const mh = kop('my_house (apps/web/src/styles.css)', 'Importeer NA styles.css (main.tsx: import "./styles.css"; import "./peil-alias.css"). Geen Tailwind nodig (O-10).') + `
:root { color-scheme: light; ${mhBlok(L)} --radius: 8px; --font-body: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", Arial, sans-serif; --font-head: var(--font-body); --shadow: 0 1px 2px rgb(11 15 20 / 0.10); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; ${mhBlok(Dk)} } }
:root[data-theme="dark"] { color-scheme: dark; ${mhBlok(Dk)} }
/* Correcties die alleen het uiterlijk raken */
.pill.heat { color: var(--heat-ink); }   /* tekst op heat-bg: oranje → inkt (>= 7:1) */
.pill.cool { color: var(--cool-ink); }
.q { font-size: 14px; }
.q.measured { background: var(--sunken); color: var(--text-2); }   /* meetkwaliteit is geen gezondheid: nooit groen */
.q.missing { background: var(--peil-unknown-bg); color: var(--peil-unknown-ink); box-shadow: inset 0 0 0 2px var(--peil-unknown); }
.offline-banner { background: var(--peil-unknown-bg); color: var(--peil-unknown-ink); border: 2px dashed var(--peil-unknown); }
.light-tile:disabled { opacity: 1; border: 2px dashed var(--peil-unknown); color: var(--text); }   /* was opacity .6: onleesbaar */
.is-offline .live, .from-snapshot .main .live { opacity: 1; filter: none; background-image: repeating-linear-gradient(135deg, var(--peil-stale-hatch) 0 2px, transparent 2px 9px); }
.from-snapshot .main .card { opacity: 1; filter: none; border-style: dashed; border-color: var(--peil-stale); }
.wizard-step.done .wizard-num { background: var(--text); border-color: var(--text); color: var(--bg); }   /* klaar ≠ gezond */
.btn:disabled, .icon-btn:disabled { opacity: 1; color: var(--peil-disabled); border-style: dashed; border-color: var(--border-strong); }
.btn.primary:hover:not(:disabled) { opacity: 1; background: var(--link-hover); }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; box-shadow: 0 0 0 2px var(--peil-ring-halo); }
`;
fs.writeFileSync(D + 'aliaslagen/my_house.css', mh);

// ── Hub P0 (ai-server-manager/apps/web/src/app/globals.css) — overbrugging tot de componenten shadcn zijn ─────────
const HUB = {
  'bg': 'background', 'surface': 'card', 'surface-2': 'muted', 'text': 'foreground', 'on-primary': 'primary-foreground', 'focus': 'ring', 'danger': 'down',
  'ok-bg': 'healthy-bg', 'ok-fg': 'healthy-ink', 'info-fg': 'info-ink', 'warn-bg': 'degraded-bg', 'warn-fg': 'degraded-ink',
  'bad-bg': 'down-bg', 'bad-fg': 'down-ink', 'unknown-fg': 'unknown-ink', 'neutral-bg': 'muted', 'neutral-fg': 'foreground',
  // info-bg en unknown-bg NIET opnemen: --info-bg: var(--info-bg) is een cyclus → de variabele wordt ongeldig (review 1.1.0,
  // gemeten in Chromium: bg-info-bg en bg-unknown-bg werden transparant). Peil levert beide namen al zelf.
};
for (const [a, b] of Object.entries(HUB)) if (a === b) throw new Error(`aliaslaag Hub: --${a} verwijst naar zichzelf (cyclus)`);
const hub = kop('de Hub P0 (apps/web/src/app/globals.css)', 'Stappen vooraf: (1) themascript dat ALTIJD data-theme="light|dark" + .dark zet (ook bij Systeem); (2) codemod: elke var(--muted) in de Hub-CSS → var(--muted-foreground); (3) verwijder in globals.css de DRIE eigen kleurblokken volledig (:root, @media (prefers-color-scheme: dark) :root:not([data-theme=light]) en :root[data-theme=dark]) — anders wint het media-blok (specificiteit 0,2,0) van deze laag en krijg je een half donker thema.') + `
:root, :root[data-theme] {
${Object.entries(HUB).map(([a, b]) => `  --${a}: var(--${b});`).join('\n')}
  --font: var(--font-sans);
  --mono: var(--font-mono);
  --shadow: var(--shadow-sm);
  --bottom-nav-h: var(--bottomnav-h);
}
/* Veldranden 1,42:1 → >= 3:1 (WCAG 1.4.11) */
input, select, textarea, fieldset { border-color: var(--input); }
`;
fs.writeFileSync(D + 'aliaslagen/hub-p0.css', hub);

// ── Contrast van de paren die my_house echt gebruikt (uit styles.css, alleen gelezen) ───────────────────────────────
const t = (th, n) => (th === 'licht' ? L : Dk)[MH[n] || n];
const MHP = [['text', 'bg'], ['text-2', 'surface'], ['muted', 'bg'], ['muted', 'surface'], ['text-2', 'sunken'], ['text-2', 'surface-2'], ['on-primary', 'primary'],
  ['heat-ink', 'heat-bg'], ['cool-ink', 'cool-bg'], ['light-ink', 'light-on'], ['ok', 'ok-bg'], ['warn-ink', 'warn-bg'], ['error', 'error-bg'], ['stale', 'surface'],
  ['peil-unknown-ink', 'peil-unknown-bg'], ['link', 'surface'],
  ['heat-ink', 'heat-soft'], ['cool-ink', 'cool-soft'], ['bg', 'primary'], ['text', 'surface-2'], ['muted', 'surface-2']]; // review 1.1.0: .schedule-bar .warm/.cold, .brand-mark, .nav-link:hover, .mode-btn.blocked
const MHU = [['border-strong', 'surface'], ['input-border', 'surface'], ['heat', 'surface'], ['cool', 'surface'], ['boiler', 'surface'], ['rest', 'surface'], ['focus', 'surface'], ['warn-dot', 'surface']];
const MHI = [['heat', 'heat-bg']]; // informatief: rand van .mode-btn.heat; de grens met --surface draagt de vorm
const res = {};
for (const th of ['licht', 'donker']) res[th] = [...MHP.map(([a, b]) => ({ paar: `--${a} op --${b}`, ratio: +wcag(t(th, a), t(th, b)).toFixed(2), eis: 4.5 })), ...MHU.map(([a, b]) => ({ paar: `--${a} op --${b}`, ratio: +wcag(t(th, a), t(th, b)).toFixed(2), eis: 3 })), ...MHI.map(([a, b]) => ({ paar: `--${a} op --${b}`, ratio: +wcag(t(th, a), t(th, b)).toFixed(2), eis: 0, info: true }))]
  .map((r) => ({ ...r, oordeel: r.info ? 'info (decoratieve rand binnen de knop)' : r.ratio >= r.eis ? 'voldoet' : 'VOLDOET NIET' }));
const cj = JSON.parse(fs.readFileSync(D + 'contrast.json', 'utf8'));
cj.aliaslagen = { my_house: res, opmerking: 'Paren zoals my_house ze in styles.css gebruikt, na de aliaslaag. .light-tile.on: --light-ink op --light-on (was in richting C 1:1).' };
fs.writeFileSync(D + 'contrast.json', JSON.stringify(cj, null, 2) + '\n');
const fout = Object.values(res).flat().filter((r) => r.oordeel === 'VOLDOET NIET');
console.log('aliaslagen geschreven; my_house-paren:', Object.values(res).flat().length, 'fouten:', fout.length, fout.map((f) => f.paar + ' ' + f.ratio).join(', '));
