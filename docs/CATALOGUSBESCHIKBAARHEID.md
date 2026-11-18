# Catalogusbeschikbaarheid

`GET /api/v1/catalog/availability` volgt [Platformcontract §4.4 (M3)](platform-v2/PLATFORM_CONTRACTEN.md#catalogusbeschikbaarheid-m3).
De ingeschreven diensten jelly-leon-platform en home-control-hub gebruiken hun Bearer-service-token om één exacte
combinatie van `train`, `app` en `version` op te vragen. Het antwoord bevat die combinatie, `beschikbaar` en
`gemeten_op`. De planner blokkeert bij een verse `nee` met `version_unavailable` en houdt de oorspronkelijke pin aan.

De Hub-worker leest maximaal eens per vijf minuten de TrueNAS-catalogusindex via `catalog.apps` met `cache_only`.
Via `catalog.get_app_details` meet hij ook de volledige versielijst voor `stable/ix-app` en maximaal drie andere
apps per ronde. Die apps rouleren op trein en naam. De index bepaalt welke apps aan de beurt zijn.
Alleen de volledige, gemeten versielijst van de gevraagde trein en app kan een `ja` of `nee` opleveren, ook voor de
nieuwste versie. Bij ontbrekende dekking, een mislukte meting of een niet-actueel meettijdstip geeft de
route `onbekend` met `gemeten_op: null`. De meettijd zegt wanneer de Hub de lokale TrueNAS-catalogus heeft gelezen.

De Hub houdt één momentopname bij. Een meetpoging verwerkt hoogstens 8 MiB en 50.000 versiecombinaties binnen
15 seconden, inclusief kluislezing en publicatie in PostgreSQL. De worker legt de start in een eigen korte
transactie vast, onafhankelijk van de momentopname. Pas nadat PostgreSQL de momentopname heeft gecommit,
legt de worker de bevestigingstijd vast. De leesroute vergelijkt beide tijden. Een mislukte poging, een late
publicatie of een poging die na 15 seconden nog geen bevestiging heeft, geeft `onbekend` met `gemeten_op: null`.
Tijdens een nog lopende poging mag de vorige geldige meting binnen haar versheidstermijn worden gelezen.
Na een workerherstart gelden dezelfde regels. Voor een momentopname uit schema 0015 is een nieuwe meting nodig. Leesverzoeken plannen geen metingen. Per geregistreerde dienst geldt een venster
van 60 verzoeken per voortschrijdende minuut, ook tijdens tokenrotatie. Bij overschrijding geeft de Hub
`429 rate_limited` en `Retry-After`. Bij een onleesbare Hub-meetvoorraad geeft de route `503 dependency_unavailable`
en `Retry-After`.

De lokale integratieproef gebruikt de echte Hub met PostgreSQL en de TrueNAS-simulator. De interopproef laadt
`HubLezer` en de planner uit jelly-leon-platform-commit `26746920e643cdbb5f9dc31b90cbcc29b65c1f1e` en controleert
zowel het verdwijnen van een catalogusappversie als dat van de vastgezette `ix-app`-versie. CI draait beide proeven.
Installeer voor de lokale proeven de ontwikkelafhankelijkheden met `make venv`.

```sh
.venv/bin/python -m pytest -q apps/api/tests/integration/test_catalog_availability.py
JLP_SOURCE=../jelly-leon-platform .venv/bin/python -m pytest -q tests/interop/test_catalog_availability.py
```
