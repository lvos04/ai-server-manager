# PLAN AFMAKEN - eerste werk van de regisseur

Stand: 2026-11-11. Lees dit direct na 00_LEES_EERST.md. Het vervalt zodra de tabel "Plan afmaken" in VOORTGANG.md helemaal
is afgevinkt.

## 1. Waarom dit bestand er is

De gebruiker heeft om een plan gevraagd dat door meerdere agents is gecontroleerd. Dat is NIET gelukt: het plan is door
agents geschreven, maar de controle is twee keer afgebroken omdat het te lang duurde. Het plan is dus een CONCEPT. Jij maakt
het af en laat het controleren, met subagents, vóór je in een repo laat bouwen.

Tot een bestand hieronder is afgevinkt geldt: spreekt het plan `git log`, `git status` of de code in een repo tegen, dan
heeft de repo gelijk. Twijfel je of een stap klopt, start dan eerst A-VERKEN en laat hem dat uitzoeken.

## 2. Eerlijke stand per bestand

| Bestand | Geschreven | Compleet | Onafhankelijk gecontroleerd |
|---|---|---|---|
| 00_LEES_EERST.md, STARTPROMPT.md, PLAN_AFMAKEN.md | door de vorige regisseur zelf | ja | NEE |
| VOORTGANG.md | met een script uit de stapbestanden (301 rijen; klopt met dekking.py) | ja | NEE |
| AGENTEN.md | door een agent | ja (deel 0 tot en met 7) | NEE (controle afgebroken; al deels hersteld) |
| POORTEN.md, BESLUITEN_EN_BLOKKADES.md, VALKUILEN.md | door agents | lijkt compleet | NEE (controle afgebroken) |
| STAPPEN_P2.md (38 stappen) | door een agent | ja (tot en met fase-afsluiting en dekking) | NEE (controle afgebroken; al deels hersteld) |
| STAPPEN_P3.md (47 stappen) | door een agent | NEE: houdt op in de baan appstore-en-fork; fase-afsluiting en dekking ontbreken | NEE |
| STAPPEN_P4_GOLF1_2.md (35 stappen) | door een agent | NEE: fase-afsluiting en dekking ontbreken | NEE |
| STAPPEN_P4_GOLF3_4.md (73 stappen) | door een agent | waarschijnlijk NEE: geen aparte fase-afsluiting en dekking gezien | NEE |
| STAPPEN_P5.md (65 stappen) | door een agent | lijkt compleet | NEE |
| STAPPEN_P6.md (29 stappen, 14 NAS-onderdelen) | door een agent | lijkt compleet | NEE |
| dekking.py, DEKKING.tsv | door een agent (afgebroken) | draait; niet nagelopen | NEE |
| maak_voortgang.py | - | BESTAAT NIET | - |

Wat `python3 <PLANMAP>/dekking.py --voortgang` op 2026-11-11 meldt (exitcode 1):

- ONGEDEKT (geen stap, geen NAS-onderdeel, geen dekkingsrij): B09-006 en B12-002.
- "Vooraf" verwijst naar een stap die niet bestaat: S-P3-110 (S-P3-600), S-P3-130 (S-P3-742), S-P3-450 (S-P3-660 en
  S-P3-755), S-G1-16 (S-G1-15 en S-P40-12), S-P5-109 (S-G2-40 en S-G2-42).
- 39 werkpakketten staan alleen in een NAS-onderdeel en hebben geen bouwstap. Dat is terecht als het pakket in P0 of P1 al
  gebouwd is; anders ontbreekt een bouwstap. Niet nagelopen.
- VOORTGANG.md klopt met de stapbestanden (301 rijen, niets dubbel, niets te veel).

## 3. De taken (PA-1 tot en met PA-11)

De opdrachten liggen klaar in `<WERKMAP>/.lokaal/plan/afmaakopdrachten/`. Elke opdracht maakt één subagent EIGENAAR van zijn
bestand of bestanden: hij maakt af wat ontbreekt, controleert en herstelt zelf. Zo schrijven er nooit twee in hetzelfde
bestand. De opdrachten schrijven alleen in `<PLANMAP>` en in `<WERKMAP>/.lokaal/plan/afmaakrapporten/`; in de repos lezen ze
alleen.

| Taak | Opdrachtbestand | Bestand(en) waar de subagent eigenaar van is | Niveau |
|---|---|---|---|
| PA-1 | controle_p2.md | STAPPEN_P2.md | N3 |
| PA-2 | controle_agentmodel.md | AGENTEN.md | N3 |
| PA-3 | controle_poorten.md | POORTEN.md, BESLUITEN_EN_BLOKKADES.md, VALKUILEN.md | N3 |
| PA-4 | samen_dekking.md | dekking.py, DEKKING.tsv, maak_voortgang.py (nieuw) | N3 |
| PA-5 | afmaken_controle_p3.md | STAPPEN_P3.md | N3 |
| PA-6 | afmaken_controle_p4a.md | STAPPEN_P4_GOLF1_2.md | N3 |
| PA-7 | afmaken_controle_p4b.md | STAPPEN_P4_GOLF3_4.md | N3 |
| PA-8 | afmaken_controle_p5.md | STAPPEN_P5.md | N3 |
| PA-9 | afmaken_controle_p6.md | STAPPEN_P6.md | N3 |
| PA-10 | (commando, doe je zelf) | - | - |
| PA-11 | droogloop.md | geen (leest alleen) | N2 |

### Zo start je een taak

Eén Agent-aanroep per taak, `subagent_type` "general-purpose", `run_in_background` true, `model` en `effort` volgens het
niveau (MODELKEUZE.md). De prompt is letterlijk:

```text
Lees /home/transcode/truenas-v2/.lokaal/plan/afmaakopdrachten/<OPDRACHTBESTAND> helemaal en voer de opdracht uit. De
"AANVULLING VAN DE REGISSEUR" onderaan dat bestand gaat voor waar ze afwijkt van de rest. Start zelf geen subagents.
```

Zet elke taak in de tabel "Lopend" van VOORTGANG.md (rol: "plan-eigenaar"; ze tellen mee voor de 10 subagents, niet voor de
8 bouwketens).

### Volgorde

1. **Ronde 1:** start PA-1 tot en met PA-9 tegelijk (negen subagents). Stap S-P2-000 mag ernaast lopen (samen tien): die leest
   alleen in de repos. Lees de tekst van S-P2-000 vóór je PA-1 start, want PA-1 kan STAPPEN_P2.md wijzigen.
2. **Na elke melding:** lees het rapport in `afmaakrapporten/<naam>.md`. Controleer zelf: bestaat het bestand nog, is het
   niet korter geworden dan het was (`wc -l`; korter mag alleen als het rapport zegt wat er weg is en waarom), en geeft
   `grep -n -i 'opus\|sonnet\|fable\|haiku' <bestand>` geen modelnaam (de treffer "OPUS-MT" is een vertaalmodel en
   mag). Valt een subagent uit: start dezelfde taak opnieuw; de aanvulling in de opdracht zegt al dat een eerdere poging
   kan zijn afgebroken.
3. **Ronde 2, kruismeldingen:** elk rapport heeft een kop VOOR_ANDER_BESTAND. Verzamel de regels per doelbestand. Per
   doelbestand met meldingen start je één subagent (N3) met dezelfde prompt als hierboven, plus de zin "Je bestand is al
   gecontroleerd; verwerk nu alleen deze meldingen en schrijf je rapport in afmaakrapporten/<naam>-ronde2.md:" en daaronder
   de meldingen. Meldingen voor 00_LEES_EERST.md, STARTPROMPT.md, VOORTGANG.md of PLAN_AFMAKEN.md verwerk je zelf. Raakt
   een melding een vaste regel van de gebruiker of de HARDE EIS: leg haar voor met een keuzemenu.
4. **PA-10:** draai `python3 <PLANMAP>/dekking.py --voortgang`. Het moet eindigen zonder FOUT (exitcode 0). Wat overblijft
   geef je aan de eigenaar van het bestand (ronde 2). Is een stapbestand gewijzigd, draai dan eerst
   `python3 <PLANMAP>/maak_voortgang.py` (maak vooraf een kopie van VOORTGANG.md in /tmp en vergelijk daarna met `diff`:
   niets wat is ingevuld of afgevinkt mag weg zijn).
5. **PA-11:** start de droogloop (N2). Blokkerende bevindingen gaan naar de eigenaar van het bestand (ronde 2); de rest
   noteer je in VOORTGANG.md bij de taak.
6. **Afsluiten:** vink de tabel "Plan afmaken" in VOORTGANG.md af en werk de kopie van het plan in de repo bij
   (00_LEES_EERST.md deel 8, punt 4; alleen de eigen paden toevoegen, nooit `git add -A`). Meld de gebruiker in een paar
   regels wat de controle heeft opgeleverd en wat open bleef.

### Wat mag wanneer

- **Geen schrijver in een repo** (geen A-BOUW, geen A-HERSTEL) vóór PA-1, PA-2, PA-3 en PA-4 klaar zijn en hun
  kruismeldingen zijn verwerkt. Lezen mag wel: S-P2-000 en A-VERKEN.
- Een stapbestand moet af en gecontroleerd zijn vóór je de eerste stap uit dat bestand start.
- PA-1 tot en met PA-11 zijn allemaal klaar vóór de gate van P2 naar P3.
- Stop en vraag (keuzemenu) als een eigenaar meldt dat zijn bestand niet te herstellen is, of als twee eigenaren elkaar
  tegenspreken en de bronnen in `<DOCS>` geen uitsluitsel geven.
