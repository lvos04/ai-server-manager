"""Rampenscenario (B12-007; S-P2-100): vaste stappenlijsten, alleen via de Hub en de TrueNAS-web-UI.

V-096: geen enkele stap gebruikt een terminal of shell op de NAS (de test ``test_rampenscenario`` bewaakt dat). De
oefening op de teststack (zonder de oorspronkelijke NAS) herstelt de Hub-database, de vault en de koppelingen uit de
eigen export; zie ``apps/api/tests/integration/test_hersteltest.py``. HARDE EIS: kijkgeschiedenis, hervatpunten en
MediaGuard-voortgang gaan alleen terug samen met hun eigen database, via de eigenaar, na een vóór/na-telling.
"""

from __future__ import annotations

from typing import Any

from hub.firststart import ED25519_KEYS, VAULT_KEY

# Verhuizing (R-HARDE-EIS-7): naast de export gaan precies deze bestanden uit de geheimenmap van de Hub mee, apart en
# beveiligd bewaard. Zonder de ondertekensleutels weigeren gekoppelde diensten de berichten van de nieuwe Hub.
VERHUIS_GEHEIMEN = (VAULT_KEY, *ED25519_KEYS)

REGEL = (
    "Herstel loopt alleen via de Hub en de TrueNAS-web-UI, nooit via een terminal op de NAS. Kijkgeschiedenis, "
    "hervatpunten en MediaGuard-voortgang gaan alleen terug samen met hun database, via de eigenaar, en tellen pas als "
    "de aantallen per tabel vóór en na gelijk zijn."
)

NOODSTOP = "Leg alle uitvoering stil met de noodstop van de Hub (beheerder; Hub-API PUT /api/v1/actions/noodstop)."
_NATEST_HUB = [
    "Hub → Backups: de nieuwste eigen export is geverifieerd (checksum en inhoudsopgave).",
    "Hub-API GET /api/v1/backups/restore-tests: de hersteltest-robot meldt per app 'geslaagd' (kloon, database, "
    "productie).",
    "Hub → Backups: de back-upgate is weer open.",
]

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "poolverlies",
        "titel": "Pool verloren of defect",
        "wanneer": "TrueNAS meldt de pool als FAULTED of hij is weg; de Hub toont de poolgate dicht.",
        "stappen": [
            NOODSTOP,
            "Laat de oorspronkelijke schijven van de pool onaangeroerd als terugval: niet wissen, niet opnieuw "
            "gebruiken en geen nieuwe pool erop aanmaken. Haal ze er alleen uit en bewaar ze apart.",
            "Bevestig eerst een apart doel: nieuwe schijven (TrueNAS-web-UI, Storage → Disks) met genoeg ruimte, los "
            "van de oorspronkelijke.",
            "Bevestig daarna een bruikbare back-up met de appgegevens: in de TrueNAS-web-UI (Data Protection → Cloud "
            "Sync Tasks) staat een geslaagde externe back-up van de appdata én van de Hub-export (met .sha256 en "
            ".json), van na de laatste wijziging die je wilt houden.",
            "STOP als een van beide ontbreekt of twijfelachtig is: doe dan niets meer aan de pool en de schijven en "
            "vraag hulp. Een nieuwe pool zonder bevestigde back-up kan de laatste kopie kosten.",
            "Maak pas daarna op het aparte doel een nieuwe pool aan (TrueNAS-web-UI, Storage).",
            "Zet de externe back-up terug via de TrueNAS-web-UI (Data Protection → Cloud Sync Tasks, richting PULL "
            "naar een nieuwe dataset), nooit over een bestaande dataset heen.",
            "Installeer de Hub en de executor opnieuw als Custom App (zie CUSTOM_APP.md) met de teruggezette datamap.",
            "Laat de hersteltest-robot per app een herstelpunt toetsen vóórdat een app weer wordt bijgewerkt. Pas als "
            "alles weer werkt, mogen de oorspronkelijke schijven een andere bestemming krijgen.",
        ],
        "natest": _NATEST_HUB,
    },
    {
        "id": "credential_lek",
        "titel": "Sleutel of wachtwoord uitgelekt",
        "wanneer": "Een API-sleutel, koppelcode of wachtwoord is mogelijk bij iemand anders terechtgekomen.",
        "stappen": [
            NOODSTOP,
            "Maak in de TrueNAS-web-UI (Credentials → API Keys) een nieuwe sleutel en trek de oude in.",
            "Vul de nieuwe sleutel in op de statuspagina van de executor of in de Hub-koppeling met TrueNAS.",
            "Vervang in de Hub de geheimen in de vault die met de lekkende sleutel te maken hadden.",
            "Bekijk Hub → Problemen en het auditspoor op acties tussen het lek en het intrekken.",
        ],
        "natest": [
            "De oude sleutel werkt niet meer (de Hub meldt een geweigerde sleutel bij een test met de oude).",
            "Hub → Onboarding: de TrueNAS-koppeling werkt met de nieuwe sleutel.",
        ],
    },
    {
        "id": "foutieve_appmigratie",
        "titel": "Een app-update heeft de gegevens beschadigd",
        "wanneer": "Na een update start de app niet of toont hij verkeerde gegevens; de Hub meldt een migratie.",
        "stappen": [
            "Zet de app niet zomaar terug op de oude image: na een databasemigratie blokkeert de Hub dat "
            "(database_herstel_vereist).",
            "Kies in de Hub het herstelpunt van vóór de update (GET /api/v1/backups/herstelpunten) en laat de robot "
            "het toetsen in de zandbak.",
            "Zet image en database samen terug via de eigenaar van de app (eigen herstelfunctie van de app).",
        ],
        "natest": [
            "De app draait weer met de vorige versie; de aantallen per tabel zijn gelijk aan het herstelpunt.",
            *_NATEST_HUB[1:],
        ],
    },
    {
        "id": "mediaguard_terugzetten",
        "titel": "MediaGuard terugzetten",
        "wanneer": "Een MediaGuard-update of -migratie ging mis.",
        "stappen": [
            "Laat MediaGuard en de mediaserver draaien; de Hub schrijft nooit in hun databases.",
            "Kies een herstelpunt van MediaGuard mét database-export; zonder database telt het niet (HARDE EIS).",
            "Laat de robot het herstelpunt toetsen: de voortgang moet in de herstelde kopie volledig zijn "
            "(aantallen per tabel vóór en na gelijk).",
            "Zet terug via de eigen herstelfunctie van MediaGuard; de oude installatie blijft terugval.",
        ],
        "natest": [
            "MediaGuard toont dezelfde voortgang als vóór de update; de mediaserver toont dezelfde kijkgeschiedenis.",
        ],
    },
    {
        "id": "verhuizing",
        "titel": "Verhuizen naar andere hardware",
        "wanneer": "De NAS wordt vervangen of de Hub moet op een andere machine verder.",
        "stappen": [
            "Maak in de Hub een verse eigen export (Hub-API POST /api/v1/backups/self) en bewaar de export en de "
            "herstelbestanden (.sha256 en .json) apart van de NAS.",
            "Bewaar ook de geheimenbestanden van de Hub apart en beveiligd (versleutelde opslag, niet op de NAS, niet "
            "in de export): " + ", ".join(VERHUIS_GEHEIMEN) + ". De vault-sleutel opent de geheimen; de drie "
            "ondertekensleutels zijn de identiteit van de Hub die elke gekoppelde dienst heeft vastgepind.",
            "Installeer op de nieuwe machine de Hub als Custom App (zie CUSTOM_APP.md) en zet vóór de eerste start "
            "precies die bestanden terug in de geheimenmap van de nieuwe Hub; de Hub zet de rechten zelf strak. Een "
            "knop om in de nieuwe Hub een export als database te gebruiken is er in deze versie nog niet "
            "(capability_unavailable); de oefening hiervan loopt alleen op de teststack. Gebruik tot dan de oude "
            "installatie als terugval.",
            "Ontbreken de ondertekensleutels, dan weigeren gekoppelde diensten de nieuwe Hub (unknown_key): koppel "
            "dan elke dienst gecontroleerd opnieuw met een nieuwe koppelcode in de Hub, één voor één, en controleer "
            "per dienst de natest. Gebruik nooit nieuwe sleutels onder de oude naam.",
            "Koppel de executor opnieuw met een nieuwe koppelcode en stel de TrueNAS-sleutel opnieuw in.",
        ],
        "natest": [
            "De teruggezette export heeft dezelfde checksum als in het .sha256-bestand.",
            "De vault opent de opgeslagen geheimen; de TrueNAS- en executorkoppeling staan er weer.",
            "Elke gekoppelde dienst aanvaardt een nieuw ondertekend bericht van de nieuwe Hub (geen unknown_key bij "
            "die dienst).",
        ],
    },
]
