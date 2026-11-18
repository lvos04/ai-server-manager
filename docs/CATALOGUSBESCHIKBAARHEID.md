# Catalogusbeschikbaarheid

`GET /api/v1/catalog/availability` volgt [Platformcontract §4.4 (M3)](platform-v2/PLATFORM_CONTRACTEN.md#catalogusbeschikbaarheid-m3).
De ingeschreven diensten jelly-leon-platform en home-control-hub gebruiken hun Bearer-service-token om één exacte
combinatie van `train`, `app` en `version` op te vragen. Het antwoord bevat die combinatie, `beschikbaar` en
`gemeten_op`. De planner blokkeert bij een verse `nee` met `version_unavailable` en houdt de oorspronkelijke pin aan.

De Hub-worker leest maximaal eens per vijf minuten de TrueNAS-catalogusindex via `catalog.apps` met `cache_only`.
Via `catalog.get_app_details` meet hij ook de volledige versielijst voor `stable/ix-app` en maximaal drie andere
apps per ronde. Die apps rouleren op trein en naam. Een geldige index bewijst de exacte nieuwste versie en
de afwezigheid van een app uit een gemeten trein. Voor een andere versie van een aanwezige app is de volledige
versielijst van de app nodig. Bij ontbrekende dekking, een mislukte meting of een niet-actueel meettijdstip geeft de
route `onbekend` met `gemeten_op: null`. De meettijd zegt wanneer de Hub de lokale TrueNAS-catalogus heeft gelezen.

De Hub houdt één momentopname bij. Een meetpoging verwerkt hoogstens 8 MiB en 50.000 versiecombinaties binnen
15 seconden. Leesverzoeken plannen geen metingen. Per geregistreerde dienst geldt een venster van 60 verzoeken
per voortschrijdende minuut, ook tijdens tokenrotatie. Bij overschrijding geeft de Hub `429 rate_limited` en
`Retry-After`. Bij een onleesbare Hub-meetvoorraad geeft de route `503 dependency_unavailable` en `Retry-After`.

De lokale integratieproef gebruikt de echte Hub met PostgreSQL en de TrueNAS-simulator. De interopproef laadt
`HubLezer` en de planner uit jelly-leon-platform-commit `26746920e643cdbb5f9dc31b90cbcc29b65c1f1e` en controleert
zowel het verdwijnen van een catalogusappversie als dat van de vastgezette `ix-app`-versie. CI draait beide proeven.
Installeer voor de lokale proeven de ontwikkelafhankelijkheden met `make venv`.

```sh
.venv/bin/python -m pytest -q apps/api/tests/integration/test_catalog_availability.py
JLP_SOURCE=../jelly-leon-platform .venv/bin/python -m pytest -q tests/interop/test_catalog_availability.py
```
