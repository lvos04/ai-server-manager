# ADR-0005 — AI-runner als aparte gebruiker 569

Status: aangenomen · 2026-11-09 · fase P0 · **contractpunt gemeld**

## Context
Contract §8: de AI-runner draait als aparte gebruiker zonder toegang tot signing keys of vault. Contract §10: "daarna
alle processen als 568:568". Die twee regels botsen.

## Besluit (veiligste interpretatie)
- Alle Hub-processen draaien als 568; alleen de AI-runner draait als **569 (`asm-ai`)**. `/appdata/secrets` (0700) en
  de databasesocket (`/tmp/asm-pg`, 0700) zijn van 568; 569 kan er niet bij (gemeten in de container:
  `Permission denied` voor `vault.key`, de socketmap en `psql`).
- De runner controleert bij de start zelf dat hij geen geheimen kan lezen en **weigert te starten** als dat wel kan.
- De bewaker start de runner vóór hij zelf naar 568 wisselt, met een parent-death-signaal (de bewaker mag 569 als 568
  geen signaal sturen).
- Draait de container niet als root, dan is een aparte gebruiker onmogelijk: de runner start dan niet (AI staat in P0
  toch uit). In P0 doet de runner niets: geen model, geen externe of betaalde aanroepen.
