// Peil — ontwerptaal TrueNAS Home Platform V2 · versie 1.1.0
// BRON VAN WAARHEID voor alle tokens. Alles in ../ (tokens.json, ontwerptaal.css, statuspagina.css, contrast.json)
// wordt hieruit gegenereerd met `node bouw/genereer.mjs`. Wijzig waarden alleen hier.
//
// Kleurregels (bindend, zie ONTWERPTAAL.md §4):
//  1. Twee tekstniveaus (foreground, muted-foreground): beide >= 7:1 op elk oppervlak, licht én donker.
//  2. Eén betekenis per kleurfamilie: groen = gemeten en gezond · amber = beperkt · rood = storing/gevaar (R3) ·
//     grijs + stippel = onbekend/verouderd · blauw = interactie/info · violet = menselijke goedkeuring (R2).
//  3. Status-, risico- en gatekleuren liggen in lichtheid BUITEN de grafiekband (licht: L <= 0,50; donker: L >= 0,74),
//     grafiekreeksen en domeinkleuren BINNEN de band. Harde controle: OKLab-ΔE×100 >= 15 tussen elke grafiek-/
//     domeinkleur en elke status-/risico-/goedkeuringskleur (bouw/contrast.mjs).
//  4. Per status drie tokens: <naam> (icoon/rand, >= 4,5:1 op -bg en kaart), <naam>-bg (vlak), <naam>-ink (tekst >= 7:1).
//  5. Tints (-bg) dragen nooit alleen betekenis: altijd icoon + woord (+ vorm).

export const META = {
  naam: 'Peil',
  versie: '1.1.0',
  datum: '2026-11-09',
  omschrijving: 'Ontwerptaal van het TrueNAS Home Platform V2 (Hub, statuspagina\'s, uiterlijk van MediaGuard, MSO en my_house).',
};

// [token, licht, donker, groep, betekenis/gebruik]
export const KLEUREN = [
  // ── Oppervlakken ────────────────────────────────────────────────────────────────────────────────────────────────
  ['background', '#EEF1F5', '#0A0D12', 'oppervlak', 'Paginavlak (achter kaarten).'],
  ['card', '#FFFFFF', '#141920', 'oppervlak', 'Kaart, paneel, tabel, grafiekvlak. Grafieken staan altijd op card.'],
  ['popover', '#FFFFFF', '#1A2029', 'oppervlak', 'Popover, menu, dialoog, sheet.'],
  ['muted', '#E4E8EE', '#1E252E', 'oppervlak', 'Verzonken vlak: tabelkop, codeblok, inactieve tab. (shadcn: achtergrond, géén tekstkleur.)'],
  ['secondary', '#E4E8EE', '#232B35', 'oppervlak', 'Vlak van de secundaire knop.'],
  ['accent', '#DCE3EC', '#26303B', 'oppervlak', 'Hover- en selectievlak (shadcn-betekenis), actief zijbalkitem.'],
  ['sidebar', '#FFFFFF', '#10141A', 'oppervlak', 'Zijbalk (desktop).'],

  // ── Tekst ───────────────────────────────────────────────────────────────────────────────────────────────────────
  ['foreground', '#0B0F14', '#F2F5F8', 'tekst', 'Tekstniveau 1: koppen, waarden, lopende tekst.'],
  ['muted-foreground', '#353E4A', '#C2CAD5', 'tekst', 'Tekstniveau 2: bron, tijd, hulptekst, meta. >= 7:1 op elk oppervlak. Er is geen derde (lichtere) tekstlaag.'],
  ['disabled-foreground', '#5C6675', '#8D97A5', 'tekst', 'Tekst van een uitgeschakeld element; altijd met een zichtbare reden ernaast.'],

  // ── Randen ──────────────────────────────────────────────────────────────────────────────────────────────────────
  ['border', '#AEB8C5', '#3A4451', 'rand', 'Decoratieve rand (kaart, scheidingslijn). Draagt nooit betekenis.'],
  ['border-strong', '#5B6575', '#8E99A8', 'rand', 'Rand die informatie draagt: knoprand, stippelrand van Onbekend/Verouderd, tabkop. >= 3:1.'],
  ['input', '#5B6575', '#8E99A8', 'rand', 'Veldrand (input, select, checkbox, radio). >= 3:1 (lost Hub 1,42:1 op).'],

  // ── Merk en interactie ──────────────────────────────────────────────────────────────────────────────────────────
  ['primary', '#123DA3', '#8DB6FF', 'interactie', 'Primaire actie, actief navigatie-item, selectie. Betekent nooit "gezond".'],
  ['primary-hover', '#0C2F80', '#B0CCFF', 'interactie', 'Hover van de primaire knop.'],
  ['primary-foreground', '#FFFFFF', '#06101F', 'interactie', 'Tekst op primary.'],
  ['link', '#123DA3', '#9DC0FF', 'interactie', 'Linktekst (altijd onderstreept).'],
  ['ring', '#123DA3', '#8DB6FF', 'interactie', 'Focusring, buitenste 3 px (tweekleurig, WCAG-techniek C40).'],
  ['ring-halo', '#FFFFFF', '#0A0D12', 'interactie', 'Focusring, binnenste 2 px halo in de spleet.'],
  ['destructive', '#A8111A', '#FF9B9B', 'interactie', 'Gevaarlijke (R3-)knop en "Kritiek". Gelijk aan risk-3-solid.'],
  ['destructive-hover', '#8A0D15', '#FFB8B8', 'interactie', 'Hover van de gevaarknop.'],
  ['destructive-foreground', '#FFFFFF', '#1F0405', 'interactie', 'Tekst op destructive (in donker donkere tekst op lichtrood).'],

  // ── Gezondheid (gereserveerd; T-01) ─────────────────────────────────────────────────────────────────────────────
  ['healthy', '#0F6B33', '#6FD394', 'status', 'Gezond: icoon (circle-check). Alleen "gemeten en goed" — nooit voor actueel, verbonden, nieuw of aanbevolen.'],
  ['healthy-bg', '#DFF2E5', '#0F2B1B', 'status', 'Gezond: vlak (alleen in grote statusblokken; de StatusBadge Gezond heeft géén vlak).'],
  ['healthy-ink', '#0A4A22', '#A6EBBF', 'status', 'Gezond: tekst.'],
  ['degraded', '#8F4B00', '#F7C26A', 'status', 'Beperkt: icoon (triangle-alert) en rand.'],
  ['degraded-bg', '#FCEFD6', '#33230A', 'status', 'Beperkt: vlak.'],
  ['degraded-ink', '#5E3300', '#FBD596', 'status', 'Beperkt: tekst.'],
  ['down', '#B3141B', '#FF9B9B', 'status', 'Storing: icoon (octagon-x) en rand. Alleen gemeten falen of gevaar.'],
  ['down-bg', '#FBE4E4', '#3A1215', 'status', 'Storing: vlak.'],
  ['down-ink', '#78090F', '#FFC2C2', 'status', 'Storing: tekst.'],
  ['unknown', '#566070', '#A3ADBB', 'status', 'Onbekend: icoon (circle-help) en gestippelde rand. Altijd met reden. Nooit groen, nooit 0.'],
  ['unknown-bg', '#E9EDF2', '#222932', 'status', 'Onbekend: vlak.'],
  ['unknown-ink', '#2A313B', '#DCE2EA', 'status', 'Onbekend: tekst.'],
  ['stale', '#566070', '#A3ADBB', 'versheid', 'Verouderd: icoon (clock-alert) en gestippelde rand.'],
  ['stale-bg', '#F1F3F6', '#1A2028', 'versheid', 'Verouderd: waardevak (onder de arcering).'],
  ['stale-hatch', '#D0D6DF', '#2E3743', 'versheid', 'Verouderd: arceerlijnen (135°).'],
  ['stale-ink', '#535D6C', '#9EA8B6', 'versheid', 'Laatst bekende waarde, bewust gedempt (≈ 6:1; >= 4,5:1 op de donkerste arceerpixel). Nooit opacity.'],
  ['info', '#17469A', '#8DB6FF', 'status', 'Info en Gepauzeerd: icoon (info / circle-pause).'],
  ['info-bg', '#E3ECFA', '#132440', 'status', 'Info/Gepauzeerd: vlak; ook "wordt" in de diff.'],
  ['info-ink', '#0B3780', '#C4DAFF', 'status', 'Info/Gepauzeerd: tekst.'],

  // ── Goedkeuring / risico (T-04) ─────────────────────────────────────────────────────────────────────────────────
  ['approval', '#4F2BA6', '#C4B0FF', 'risico', 'Menselijke goedkeuring nodig (R2, teller Goedkeuringen). Violet komt nergens anders voor, ook niet in grafieken.'],
  ['approval-bg', '#EFEAFB', '#241B3D', 'risico', 'Goedkeuring: vlak.'],
  ['approval-ink', '#3B1F80', '#D9CCFF', 'risico', 'Goedkeuring: tekst.'],
  ['risk-0', '#5B6575', '#8E99A8', 'risico', 'R0 · Alleen lezen — rand/glyph (neutraal).'],
  ['risk-0-bg', '#F1F3F6', '#1A2028', 'risico', 'R0: vlak van het woorddeel.'],
  ['risk-0-ink', '#2A313B', '#DCE2EA', 'risico', 'R0: tekst.'],
  ['risk-0-solid', '#D5DBE3', '#2E3743', 'risico', 'R0: codeblok.'],
  ['risk-0-on-solid', '#0B0F14', '#F2F5F8', 'risico', 'R0: tekst op codeblok.'],
  ['risk-1', '#3B4452', '#C2CAD5', 'risico', 'R1 · Omkeerbaar — rand/glyph (neutraal-sterk; R1 loopt automatisch binnen het beleid).'],
  ['risk-1-bg', '#E4E8EE', '#222932', 'risico', 'R1: vlak van het woorddeel.'],
  ['risk-1-ink', '#0B0F14', '#F2F5F8', 'risico', 'R1: tekst.'],
  ['risk-1-solid', '#3B4452', '#C2CAD5', 'risico', 'R1: codeblok.'],
  ['risk-1-on-solid', '#FFFFFF', '#0A0D12', 'risico', 'R1: tekst op codeblok.'],
  ['risk-2', '#4F2BA6', '#C4B0FF', 'risico', 'R2 · Goedkeuring nodig — rand/glyph (= approval).'],
  ['risk-2-bg', '#EFEAFB', '#241B3D', 'risico', 'R2: vlak van het woorddeel.'],
  ['risk-2-ink', '#3B1F80', '#D9CCFF', 'risico', 'R2: tekst.'],
  ['risk-2-solid', '#4F2BA6', '#C4B0FF', 'risico', 'R2: codeblok.'],
  ['risk-2-on-solid', '#FFFFFF', '#170A38', 'risico', 'R2: tekst op codeblok.'],
  ['risk-3', '#A8111A', '#FF9B9B', 'risico', 'R3 · Destructief — rand/glyph (rol gevaar).'],
  ['risk-3-bg', '#FBE4E4', '#3A1215', 'risico', 'R3: vlak van het woorddeel.'],
  ['risk-3-ink', '#78090F', '#FFC2C2', 'risico', 'R3: tekst.'],
  ['risk-3-solid', '#A8111A', '#FF9B9B', 'risico', 'R3: codeblok.'],
  ['risk-3-on-solid', '#FFFFFF', '#1F0405', 'risico', 'R3: tekst op codeblok.'],

  // ── Gate, validatie, diff ──────────────────────────────────────────────────────────────────────────────────────
  ['gate', '#2A313B', '#DCE2EA', 'as', 'Gate dicht (wacht op voorwaarde): rand en slot-icoon. Neutraal-sterk, nooit foutrood (T-14).'],
  ['gate-bg', '#F1F3F6', '#1A2028', 'as', 'Gate dicht: vlak.'],
  ['gate-ink', '#0B0F14', '#F2F5F8', 'as', 'Gate dicht: tekst.'],
  ['validation', '#5B6575', '#8E99A8', 'as', 'Validatielabel: gestippelde rand en kolf-icoon. Nooit de stijl van "geslaagd".'],
  ['validation-bg', '#EEF1F5', '#1E252E', 'as', 'Validatielabel: vlak.'],
  ['validation-ink', '#2A313B', '#DCE2EA', 'as', 'Validatielabel: tekst (mono).'],
  ['diff-old-bg', '#E4E8EE', '#1E252E', 'as', 'Diff "was": neutraal vlak, tekst doorgestreept.'],
  ['diff-old-ink', '#353E4A', '#C2CAD5', 'as', 'Diff "was": tekst.'],
  ['diff-new-bg', '#E3ECFA', '#132440', 'as', 'Diff "wordt": info-vlak, tekst vet. Geen rood/groen.'],
  ['diff-new-ink', '#0B3780', '#C4DAFF', 'as', 'Diff "wordt": tekst.'],

  // ── Grafiek (dataviz-procedure, zie palet-validatie in contrast.json) ──────────────────────────────────────────
  ['chart-1', '#2a78d6', '#3987e5', 'grafiek', 'Reeks 1 — blauw (accentfamilie).'],
  ['chart-2', '#eb6834', '#d95926', 'grafiek', 'Reeks 2 — oranje.'],
  ['chart-3', '#00a672', '#199e70', 'grafiek', 'Reeks 3 — aqua.'],
  ['chart-4', '#c78600', '#c98500', 'grafiek', 'Reeks 4 — geel/oker.'],
  ['chart-5', '#db7099', '#d55181', 'grafiek', 'Reeks 5 — magenta. Een 6e reeks bestaat niet: vouw naar Overig of small multiples.'],
  ['chart-other', '#7D8593', '#7A8391', 'grafiek', 'Overig — grijs, altijd met arcering en label.'],
  ['chart-grid', '#E3E6EB', '#262E38', 'grafiek', 'Rasterlijn: haarlijn, solide, recessief.'],
  ['chart-axis', '#9AA3AF', '#4A5462', 'grafiek', 'As/basislijn: haarlijn.'],
  ['chart-label', '#353E4A', '#C2CAD5', 'grafiek', 'As-, legenda- en labeltekst (nooit de reekskleur).'],
  ['chart-limit', '#0B0F14', '#F2F5F8', 'grafiek', 'Grenslijn (bijv. geheugenlimiet), met direct label.'],
  ['chart-gap', '#C9D0D9', '#333C48', 'grafiek', 'Arcering van een gat ("Geen meting") of verouderd stuk in een grafiek.'],
  ['chart-meter-track', '#CDE2FB', '#0D366B', 'grafiek', 'Spoor van een meter: lichtere stap van dezelfde blauwe trap (vulling/spoor >= 3:1).'],
  ['chart-seq-100', '#cde2fb', '#0d366b', 'grafiek', 'Sequentieel blauw, stap 100 ("bijna nul"; in donker het dichtst bij het vlak).'],
  ['chart-seq-200', '#9ec5f4', '#104281', 'grafiek', 'Sequentieel blauw, stap 200.'],
  ['chart-seq-300', '#6da7ec', '#184f95', 'grafiek', 'Sequentieel blauw, stap 300 (ordinaal: lichtste toegestane stap in licht is 250/300).'],
  ['chart-seq-400', '#3987e5', '#256abf', 'grafiek', 'Sequentieel blauw, stap 400.'],
  ['chart-seq-500', '#256abf', '#3987e5', 'grafiek', 'Sequentieel blauw, stap 500.'],
  ['chart-seq-600', '#184f95', '#6da7ec', 'grafiek', 'Sequentieel blauw, stap 600.'],
  ['chart-seq-700', '#0d366b', '#9ec5f4', 'grafiek', 'Sequentieel blauw, stap 700 (maximum).'],
  ['chart-div-neg-3', '#1c5cab', '#9ec5f4', 'grafiek', 'Divergerend, blauwe arm, sterkst.'],
  ['chart-div-neg-2', '#3987e5', '#3987e5', 'grafiek', 'Divergerend, blauwe arm, midden.'],
  ['chart-div-neg-1', '#86b6ef', '#184f95', 'grafiek', 'Divergerend, blauwe arm, zwakst.'],
  ['chart-div-mid', '#E4E8EE', '#2A313B', 'grafiek', 'Divergerend, neutraal grijs midden ("niets").'],
  ['chart-div-pos-1', '#f49775', '#8a2e00', 'grafiek', 'Divergerend, oranje arm, zwakst.'],
  ['chart-div-pos-2', '#da5821', '#da5821', 'grafiek', 'Divergerend, oranje arm, midden.'],
  ['chart-div-pos-3', '#9f3600', '#ffa98a', 'grafiek', 'Divergerend, oranje arm, sterkst.'],

  // ── Domeinrollen (bestaande apps; kleur volgt de entiteit = grafiekslot) ────────────────────────────────────────
  ['domain-heat', '#eb6834', '#d95926', 'domein', 'Verwarmen (my_house) — icoon flame; = chart-2.'],
  ['domain-heat-bg', '#FDEBDD', '#3A1F10', 'domein', 'Verwarmen: vlak (modusknop actief, chip).'],
  ['domain-heat-ink', '#6E2405', '#FFD3B5', 'domein', 'Verwarmen: tekst.'],
  ['domain-heat-soft', '#F4A57E', '#9C3D14', 'domein', 'Verwarmen: decoratieve band/dial (draagt geen informatie).'],
  ['domain-cool', '#2a78d6', '#3987e5', 'domein', 'Koelen (my_house) — icoon snowflake; = chart-1.'],
  ['domain-cool-bg', '#E0EEFB', '#0F2740', 'domein', 'Koelen: vlak.'],
  ['domain-cool-ink', '#0B3B73', '#C2DDFA', 'domein', 'Koelen: tekst.'],
  ['domain-cool-soft', '#9ec5f4', '#184f95', 'domein', 'Koelen: decoratieve band/dial.'],
  ['domain-boiler', '#00a672', '#199e70', 'domein', 'Boiler (alleen meten) — icoon shower-head; = chart-3.'],
  ['domain-boiler-bg', '#E4E8EE', '#1E252E', 'domein', 'Boiler: vlak — bewust NEUTRAAL (review 1.1.0): een aqua/mint vlak was niet te onderscheiden van healthy-bg (ΔE 0,6). De boiler is alleen meten; identiteit = icoon shower-head + woord.'],
  ['domain-boiler-ink', '#0B0F14', '#F2F5F8', 'domein', 'Boiler: tekst — neutraal (groenige inkt was ΔE 2,5 van healthy-ink).'],
  ['domain-light-on', '#c78600', '#c98500', 'domein', 'Licht aan — icoon lightbulb; = chart-4.'],
  ['domain-light-on-bg', '#FDF6CF', '#3A2E0E', 'domein', 'Licht aan: tegelvlak (my_house .light-tile.on).'],
  ['domain-light-on-ink', '#5C4300', '#F7DC94', 'domein', 'Licht aan: tekst op het tegelvlak.'],
  ['domain-lane-gpu', '#2a78d6', '#3987e5', 'domein', 'MediaGuard GPU-lane (AV1); = chart-1.'],
  ['domain-lane-cpu', '#eb6834', '#d95926', 'domein', 'MediaGuard CPU-lane; = chart-2.'],
  ['domain-integrity', '#0B0F14', '#F2F5F8', 'domein', 'MediaGuard integriteitsslot (inkt, icoon lock).'],
];

// shadcn-namen die naar een ander token verwijzen (DTCG-alias). [token, verwijst naar, betekenis]
export const ALIASSEN = [
  ['card-foreground', 'foreground', 'shadcn: tekst op card.'],
  ['popover-foreground', 'foreground', 'shadcn: tekst op popover.'],
  ['secondary-foreground', 'foreground', 'shadcn: tekst op secondary.'],
  ['accent-foreground', 'foreground', 'shadcn: tekst op accent.'],
  ['sidebar-foreground', 'foreground', 'shadcn sidebar: tekst.'],
  ['sidebar-primary', 'primary', 'shadcn sidebar: actief item.'],
  ['sidebar-primary-foreground', 'primary-foreground', 'shadcn sidebar: tekst op actief item.'],
  ['sidebar-accent', 'accent', 'shadcn sidebar: hover.'],
  ['sidebar-accent-foreground', 'foreground', 'shadcn sidebar: tekst op hover.'],
  ['sidebar-border', 'border', 'shadcn sidebar: rand.'],
  ['sidebar-ring', 'ring', 'shadcn sidebar: focus.'],
  ['paused', 'info', 'Gepauzeerd (T-17): icoon circle-pause. Bewuste pauze, geen storing.'],
  ['paused-bg', 'info-bg', 'Gepauzeerd: vlak.'],
  ['paused-ink', 'info-ink', 'Gepauzeerd: tekst.'],
];

// Niet-kleur-tokens (gelijk in licht en donker). [cssnaam, waarde, $type, betekenis]
export const MATEN = [
  ['radius', '0.5rem', 'dimension', 'Basisradius 8 px: kaart, knop, veld. sm 4 (risicotag, code), md 6, lg 8, xl 12 (dialoog/sheet), statuspil volledig rond.'],
  ['touch', '2.75rem', 'dimension', 'Aanraakdoel 44 px: minimum voor elk bedienbaar element op elke breedte en elke aanwijzer.'],
  ['header-h', '4rem', 'dimension', 'Hoogte kopbalk (64 px).'],
  ['bottomnav-h', '4rem', 'dimension', 'Hoogte ondernavigatie (64 px) zonder safe area.'],
  ['sidebar-w', '16rem', 'dimension', 'Breedte zijbalk (256 px) vanaf lg (1024 px).'],
  ['content-max', '76rem', 'dimension', 'Maximale inhoudsbreedte (1216 px).'],
  ['prose-max', '65ch', 'dimension', 'Maximale regellengte lopende tekst (65 tekens; gelijk aan Tailwind max-w-prose — review 1.1.0: was 40rem, maar max-w-prose compileert altijd naar 65ch).'],
  ['focus-width', '3px', 'dimension', 'Focusring buitenrand.'],
  ['focus-offset', '2px', 'dimension', 'Focusring spleet (gevuld met ring-halo).'],
  ['z-sticky', '20', 'number', 'Sticky actiebalk, tabelkop.'],
  ['z-nav', '30', 'number', 'Kopbalk, ondernavigatie.'],
  ['z-overlay', '40', 'number', 'Dialoog, sheet, popover.'],
  ['z-toast', '50', 'number', 'Toast (Sonner).'],
  ['duration-fast', '150ms', 'duration', 'Kleur/hover, chevron.'],
  ['duration-medium', '200ms', 'duration', 'Sheet/dialoog in- en uitschuiven.'],
  ['ease-standard', 'cubic-bezier(0.2, 0, 0, 1)', 'cubicBezier', 'Standaard easing.'],
  ['ease-exit', 'cubic-bezier(0.4, 0, 1, 1)', 'cubicBezier', 'Uitgaande beweging.'],
];

export const TYPO = {
  sans: 'system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Helvetica Neue", Arial, sans-serif',
  mono: 'ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", "DejaVu Sans Mono", Menlo, Consolas, monospace',
  // Tailwind-standaardschaal blijft intact (shadcn rekent erop). Rollen (ONTWERPTAAL.md §5):
  rollen: [
    ['meta', 'text-sm', '0.875rem', '1.25rem', 400, 'Bron, tijd, hulptekst, tabelcel, badge. Ondergrens: kleiner bestaat niet (text-xs is verboden).'],
    ['body', 'text-base', '1rem', '1.5rem', 400, 'Lopende tekst, knop, veld (>= 16 px: geen iOS-zoom).'],
    ['titel', 'text-lg', '1.125rem', '1.75rem', 600, 'Kaarttitel, h3.'],
    ['sectie', 'text-xl', '1.25rem', '1.75rem', 700, 'Sectiekop, h2.'],
    ['pagina', 'text-2xl', '1.5rem', '2rem', 700, 'Paginatitel, h1 (één per pagina).'],
    ['waarde', 'text-3xl', '1.875rem', '2.25rem', 600, 'Kaartwaarde (proportionele cijfers).'],
    ['held', 'text-5xl', '3rem', '1', 600, 'Eén heldwaarde per scherm (systeemstatus op de statuspagina niet).'],
  ],
};
