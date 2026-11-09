# ADR-0019 — Optionele model-apps: buiten de image, één producent per soort (B03)

Status: aangenomen · 2026-11-09 · overgenomen uit ADR-B03-13 van het goedgekeurde B03 2.0-plan (`docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` §10.16) · contractkant (Δ-CONTRACT-MT, Δ-CONTRACT-MODEL) in deze repo; gebruik in jelly-leon.
Contractwijzigingen die hieruit volgen (Δ-…, hoofdstuk 18 van het bouwplan) zijn nog niet in `PLATFORM_CONTRACTEN.md`
doorgevoerd; dat gebeurt als eigen stap met review.
Herkomst: Contractpunt (Δ-CONTRACT-MT, Δ-CONTRACT-MODEL) voor ai-server-manager;

  uitvoering in jelly-leon. Jurypunten J-HAALB A-10, F3-blokkerend (vertaalmotor), J-BESCH F2-I5.
- **Werkpakketten:** B03-038, B03-044, B03-059, B03-079; testen JLT-18, JLT-21, JLT-27, JLT-32.

## Context

- Contract 1.1/1.2: lokale modellen (Ollama, faster-whisper, Piper, lokaal embeddingmodel) zijn optionele apps, standaard
  uit, met een werkende klassieke terugval; geen betaalde API.
- De omzetting van OPUS-MT naar CTranslate2 liep via torch (≈ 828 MB) en transformers; de inferentie zelf heeft alleen
  ctranslate2 + sentencepiece nodig (F3-meting).
- Spraakherkenning is dubbel gepland (B03-008 en B07-004); zoeken maakt al embeddings van de bron "jellyfin".
- De A310 is van MediaGuard-AV1 en live-transcodes.

## Besluit

1. **Vertaling:** een aparte optionele app **`mt`** (standaard uit) met OPUS-MT en→nl via CTranslate2. Het model wordt
   **eenmalig buiten de NAS** omgezet (ontwikkelmachine of CI onder `docker-build.lock`) met herkomst (HF-revisie,
   converterversie, commando) en sha256, en meegeleverd in de mt-image of door de beheerder geüpload. Nooit omzetten of
   downloaden op de NAS; geen torch/transformers/ctranslate2 in de jelly-leon-image.
2. **LLM-route** (Ollama) alleen experimenteel, met Apache-2.0/MIT-modellen en een gemeten budget; anders vervalt ze.
3. **Eén producent per soort** (Δ-CONTRACT-MODEL): één spraakproducent voor B03-008, B07, F4 (taal) en F6 (transcripten);
   één embeddingproducent (voorlopig geen embeddings; komen ze er, dan maakt Jelly Leon ze en leest zoeken ze — BG-06).
4. Model-apps draaien **standaard zonder GPU of alleen op de UHD 770, nooit op de A310**, en vallen buiten de planner van
   Jelly Leon; Jelly Leon behandelt ze als afhankelijkheid met time-out en terugval (503 `engine_unavailable`, nooit
   gesimuleerd succes).
5. Adressen van model-apps alleen loopback, RFC 1918 of ULA (niet `100.64.0.0/10`), met een IP-controle per verbinding en
   zonder redirects; het geheim van de app staat in de geheimenmap.

## Gevolgen

- Zonder de apps werken sync, kwaliteitscontrole, segmentdetectie en aanbevelingen gewoon klassiek; vertalen en
  STT-taalcontrole zijn dan niet beschikbaar (eerlijk "onbekend").

## Verificatie

JLT-27 (motor uit/onbereikbaar/injectie), JLT-18 (embeddings uit/aan/onbereikbaar), JLT-21 (kwaliteit met motor), JLT-32
(taal met en zonder STT); SBOM-controle van de jelly-leon-image.
