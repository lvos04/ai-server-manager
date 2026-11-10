// Statuspagina-prototypes (fictieve gegevens) uit hetzelfde sjabloon. De gegevens staan apart in DATA, zodat
// bouw/test-sjabloon.mjs de JS- en de Python-renderer op precies deze invoer kan vergelijken.
import fs from 'node:fs';
import { render } from './sjabloon.mjs';

const T = (tijd, iso) => ({ tijd, iso: `2026-11-09T${iso || tijd}:00+01:00` });
const VAST = { voorbeeld: true, versie: '0.1.0', bijgewerkt: '9 nov 2026, 11:56', bijgewerkt_iso: '2026-11-09T11:56:00+01:00' };

export const DATA = {
  // Executor: nog nooit gekoppeld, koppelen mislukt (vaste melding van dít verzoek → role=alert), veldfout bij de koppelcode.
  statuspagina: {
    ...VAST,
    dienst_naam: 'Executor', dienst_omschrijving: 'Voert alleen door de Hub ondertekende acties uit op TrueNAS. Enige dienst met een schrijfsleutel.',
    titel_toestand: 'niet gekoppeld (koppelen mislukt)',
    spring_doel: 'koppelcode', spring_tekst: 'Naar de koppelcode (fout)',
    melding: true, melding_rol: 'alert', melding_toon: 'fout', melding_icoon: 'storing', melding_titel: 'Koppelen is mislukt',
    melding_tekst: 'De Hub weigerde de koppelcode: verlopen, al gebruikt of ongeldig. Maak in de Hub een nieuwe koppelcode en probeer het opnieuw.',
    melding_link: true, melding_link_doel: 'koppelcode', melding_link_tekst: 'Naar het veld Koppelcode',
    melding_code: 'hub_weigerde_code', trace_id: '3d8a1f4e-6b2c-4e95-a7d0-91c5b8e2f364',
    totaal_toon: 'onbekend', totaal_label: 'Niet gereed', totaal_toelichting: 'Deels onbekend — wacht op koppeling met de Hub.',
    checks: [
      { naam: 'Proces', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Eigen database', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Koppeling met de Hub', toon: 'niet-gekoppeld', label: 'Niet gekoppeld', ...T('11:56'), reden: 'Zonder koppeling weet de executor niet welke acties zijn ondertekend.' },
      { naam: 'TrueNAS-schrijfsleutel', toon: 'onbekend', label: 'Niet ingesteld', ...T('11:56'), reden: 'Wordt gevraagd zodra de executor gekoppeld is.' },
    ],
    gereed: 'Nee — wacht op koppeling',
    gekoppeld: false, koppelformulier: true, koppelcode_geldig: '30 minuten', csrf_token: 'voorbeeld-csrf',
    fout_koppelcode: 'Deze koppelcode is verlopen of al gebruikt. Maak een nieuwe in de Hub.',
    dienst_blok_titel: 'Wat deze versie uitvoert',
    dienst_blok: [{ naam: 'Toegestane acties', toon: 'nog-niet', label: 'Nog niet beschikbaar', reden: 'Volgt in fase P2. Tot dan is de lijst met toegestane acties leeg en voert de executor niets uit.' }],
  },

  // Gewone dienst, gekoppeld (net bevestigd → info met role=status), één controle beperkt en één onbekend; het dienstblok
  // toont alle tonen van 1.1.1. Totaal = slechtste van de controles en de verse metingen in het dienstblok (§13.2):
  // Beperkt. Niet beschikbaar telt als onbekend; verouderd, nog niet, gate, beleid en feit tellen niet mee.
  'statuspagina-gekoppeld': {
    ...VAST,
    dienst_naam: 'Voorbeelddienst', dienst_omschrijving: 'Voorbeeld van een nieuwe dienst met alleen een statuspagina; alle schermen staan in de Hub.',
    titel_toestand: 'gekoppeld, beperkt', spring_doel: 'inhoud', spring_tekst: 'Naar inhoud',
    melding: true, melding_rol: 'status', melding_toon: 'info', melding_icoon: 'info', melding_titel: 'Gekoppeld met de Hub',
    melding_tekst: 'De Hub heeft de koppeling bevestigd. Alle schermen van deze dienst staan nu in de Hub.',
    totaal_toon: 'beperkt', totaal_label: 'Beperkt', totaal_toelichting: 'Gereed. Eén controle is beperkt en één is onbekend; één functie is niet beschikbaar.',
    checks: [
      { naam: 'Proces', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Eigen database', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Bron Voorbeeld-API', toon: 'beperkt', label: 'Beperkt', ...T('11:55'), reden: 'Antwoordt traag (8 s); de dienst probeert het met wachttijd opnieuw.', reden_code: 'upstream_timeout' },
      { naam: 'Gebeurtenissen naar de Hub', toon: 'onbekend', label: 'Onbekend', ...T('11:50'), reden: 'Laatste levering 11:50; nieuwere stand nog niet bevestigd.' },
    ],
    gereed: 'Ja', bron: 'Eigen controles (/readyz, /healthz) en de gezondheid van de koppeling met de Voorbeeld-API.',
    gekoppeld: true, gekoppeld_sinds: '8 nov 2026, 20:14', hub_adres: 'http://voorbeeld-nas.invalid:30400', hub_vingerafdruk: 'MEGG-8GFG-2E4Y-K2RQ',
    dienst_blok_titel: 'Wat deze dienst doet',
    dienst_blok: [
      { naam: 'Voorbeeldfunctie', toon: 'gate', label: 'Wacht op besluit', reden: 'Gaat pas aan na besluit D99 in de Hub (voorbeeld). Dit is geen storing; er wacht een voorwaarde.' },
      { naam: 'Import uit de bron', toon: 'niet-beschikbaar', label: 'Niet beschikbaar', reden: 'De Voorbeeld-API levert deze gegevens niet. We tonen geen schatting.', reden_code: 'capability_unavailable' },
      { naam: 'Energiemeting', toon: 'verouderd', label: 'Verouderd · laatst bekend 10:12', reden: 'De bron reageert niet sinds 10:12.' },
      { naam: 'Boiler schakelen', toon: 'beleid', label: 'Alleen meten', reden: 'Schakelen is altijd uitgeschakeld (beleid). Er is bewust geen schakelaar.' },
      { naam: 'Zoekindex', toon: 'nog-niet', label: 'Nog niet beschikbaar', reden: 'Volgt in fase P3.' },
      { naam: 'Catalogus', toon: 'feit', label: '2 apps', reden: 'Gelezen uit de eigen database om 11:56.' },
    ],
  },

  // 1.1.1 (E01): koppelbestand onleesbaar → fail-closed, geen formulier. De melding beschrijft een toestand die bij het
  // laden al bestond: geen live-rol, geen trace-ID, wel de code en het pad in mono.
  'statuspagina-onleesbaar': {
    ...VAST,
    dienst_naam: 'Voorbeelddienst', dienst_omschrijving: 'Voorbeeld van een nieuwe dienst met alleen een statuspagina; alle schermen staan in de Hub.',
    titel_toestand: 'niet gereed, koppelstatus onleesbaar', spring_doel: 'inhoud', spring_tekst: 'Naar inhoud',
    melding: true, melding_toon: 'fout', melding_icoon: 'storing', melding_titel: 'De koppelstatus is onleesbaar',
    melding_tekst: 'Deze dienst kon zijn koppelbestand niet lezen en voert daarom niets uit. Het bestand:',
    melding_pad: '/appdata/secrets/hub-link.json', melding_code: 'koppelstatus_onleesbaar',
    melding_link: false,
    totaal_toon: 'storing', totaal_label: 'Niet gereed', totaal_toelichting: 'Storing — de koppelstatus is onleesbaar.',
    checks: [
      { naam: 'Proces', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Eigen database', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Koppeling met de Hub', toon: 'storing', label: 'Onleesbaar', ...T('11:56'), reden: 'Het koppelbestand is geen geldig bestand van deze dienst. Herstel staat hieronder bij Koppeling met de Hub.', reden_code: 'koppelstatus_onleesbaar' },
    ],
    gereed: 'Nee — koppelstatus onleesbaar',
    koppelstatus_onleesbaar: true,
    dienst_blok_titel: 'Wat deze dienst doet',
    dienst_blok: [{ naam: 'Voorbeeldfunctie', toon: 'gate', label: 'Wacht op koppeling', reden: 'Zonder geldige koppeling voert de dienst niets uit. Dit is geen storing van de functie zelf.' }],
  },

  // 1.1.1 (E02): nog nooit gekoppeld en er loopt een poging (pending ≠ null) → geen formulier, neutrale pil met zandloper.
  'statuspagina-bezig': {
    ...VAST,
    dienst_naam: 'Voorbeelddienst', dienst_omschrijving: 'Voorbeeld van een nieuwe dienst met alleen een statuspagina; alle schermen staan in de Hub.',
    titel_toestand: 'niet gereed, koppelen bezig', spring_doel: 'inhoud', spring_tekst: 'Naar inhoud',
    totaal_toon: 'onbekend', totaal_label: 'Niet gereed', totaal_toelichting: 'Deels onbekend — er loopt een koppelpoging.',
    checks: [
      { naam: 'Proces', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Eigen database', toon: 'gezond', label: 'Gezond', ...T('11:56') },
      { naam: 'Koppeling met de Hub', toon: 'niet-gekoppeld', label: 'Niet gekoppeld', ...T('11:56'), reden: 'Er loopt een koppelpoging sinds 11:54.' },
    ],
    gereed: 'Nee — wacht op koppeling',
    koppelformulier: true, koppelen_bezig: true, koppelen_bezig_sinds: '11:54', koppelen_bezig_iso: '2026-11-09T11:54:00+01:00',
    koppelcode_geldig: '60 minuten', csrf_token: 'voorbeeld-csrf',
    dienst_blok_titel: 'Wat deze dienst doet',
    dienst_blok: [{ naam: 'Voorbeeldfunctie', toon: 'gate', label: 'Wacht op koppeling', reden: 'Gaat aan zodra de dienst met de Hub gekoppeld is.' }],
  },
};

const sjabloon = () => fs.readFileSync(new URL('../statuspagina.html', import.meta.url), 'utf8');
export const statuspagina = () => render(sjabloon(), DATA.statuspagina);
export const statuspaginaGekoppeld = () => render(sjabloon(), DATA['statuspagina-gekoppeld']);
export const statuspaginaOnleesbaar = () => render(sjabloon(), DATA['statuspagina-onleesbaar']);
export const statuspaginaBezig = () => render(sjabloon(), DATA['statuspagina-bezig']);
