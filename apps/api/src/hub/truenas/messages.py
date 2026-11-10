"""Nederlandse meldingen en advies per ``reason_code`` (UI en API tonen deze letterlijk)."""

from __future__ import annotations

REASON_CODES: tuple[str, ...] = (
    "auth_failed",
    "permission_denied",
    "method_unavailable",
    "unreachable",
    "timeout",
    "tls_untrusted",
    "key_too_privileged",
    "not_configured",
    "protocol_error",
    "stale",
    "meting_verouderd",
)

MESSAGES: dict[str, tuple[str, str]] = {
    "auth_failed": (
        "TrueNAS weigerde de API-key.",
        "Controleer in TrueNAS (Credentials → API Keys) of de key bestaat, niet verlopen of ingetrokken is en bij een "
        "gebruiker met de rol READONLY_ADMIN hoort. Vul daarna de key opnieuw in.",
    ),
    "permission_denied": (
        "De API-key heeft geen leesrechten voor dit onderdeel.",
        "Geef de TrueNAS-gebruiker van deze key de rol READONLY_ADMIN (alleen-lezen). Dit onderdeel blijft 'onbekend' "
        "tot de rechten kloppen; de Hub slaat het niet stil over.",
    ),
    "method_unavailable": (
        "Deze TrueNAS-versie biedt de benodigde API-methode niet aan.",
        "De Hub heeft de methoden per versie ontdekt (core.get_methods). Dit onderdeel blijft 'onbekend'; controleer "
        "of de NAS een ondersteunde TrueNAS-versie (24.10 of nieuwer) draait.",
    ),
    "unreachable": (
        "TrueNAS is niet bereikbaar op het ingevulde adres.",
        "Controleer het NAS-adres en de HTTPS-poort in besluit D03 en of de Hub de NAS via het LAN kan bereiken.",
    ),
    "timeout": (
        "TrueNAS reageerde niet op tijd.",
        "De NAS is mogelijk zwaar belast of het adres klopt niet. Probeer het later opnieuw; de laatst bekende "
        "gegevens worden als verouderd getoond.",
    ),
    "tls_untrusted": (
        "Het HTTPS-certificaat van TrueNAS wordt niet vertrouwd.",
        "Vergelijk de getoonde SHA-256-vingerafdruk met die in TrueNAS (System → Certificates) en bevestig hem alleen "
        "als hij exact gelijk is. Pas daarna stuurt de Hub de API-key.",
    ),
    "key_too_privileged": (
        "Deze API-key heeft schrijfrechten; de Hub gebruikt uitsluitend een alleen-lezen-key.",
        "Maak in TrueNAS een aparte gebruiker met alleen de rol READONLY_ADMIN en een API-key voor die gebruiker. "
        "De key met schrijfrechten hoort alleen op de koppelpagina van de executor (fase P2).",
    ),
    "not_configured": (
        "De TrueNAS-koppeling is nog niet ingesteld.",
        "Vul in de onboarding-wizard besluit D03 (NAS-adres) in en stel een alleen-lezen-API-key in.",
    ),
    "protocol_error": (
        "TrueNAS gaf een onverwacht antwoord.",
        "De Hub kon het antwoord niet verwerken. Het onderdeel blijft 'onbekend'; de details staan in de app-log.",
    ),
    "stale": (
        "De laatste meting is verouderd.",
        "De gegevens zijn ouder dan de ingestelde geldigheid en gelden daarom als onbekend. Vernieuw de inventaris.",
    ),
    "meting_verouderd": (
        "De laatste meting is verouderd.",
        "De gegevens zijn ouder dan hun maximale leeftijd (max_age) en gelden daarom als onbekend. Vernieuw de "
        "inventaris.",
    ),
}


def message(reason_code: str | None) -> str:
    if not reason_code:
        return ""
    return MESSAGES.get(reason_code, ("Onbekende fout.", ""))[0]


def advice(reason_code: str | None) -> str:
    if not reason_code:
        return ""
    return MESSAGES.get(reason_code, ("", "Zie de app-log."))[1]
