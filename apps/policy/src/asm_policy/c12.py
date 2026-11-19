"""Pas de gepinde eigenaarsregels voor accounts en geheimen toe op installatiewaarden."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ._asf_c12 import USER_LIST_KEYS, Place, has_value, secret_text_reasons


def installatiecodes(values: Mapping[str, Any], *, ix_app: bool, vault_ref: re.Pattern[str]) -> set[str]:
    """Toets ook geërfde accountcontext en naam/waarde-paren. Geef uitsluitend vaste foutcodes terug."""
    codes: set[str] = set()

    def ingevuld(value: Any, plek: Place, *, instellingen: bool, toets_geheimnaam: bool) -> None:
        if (plek.account and has_value(value)) or (
            isinstance(value, str) and secret_text_reasons(value, settings=instellingen)
        ):
            codes.add("account_gegevens_verboden")
        elif toets_geheimnaam and has_value(value):
            verwijzing = isinstance(value, str) and vault_ref.fullmatch(value) is not None
            if (plek.secret and not verwijzing) or (ix_app and verwijzing and not plek.secret):
                codes.add("secret_in_form")

    def bezoek(value: Any, plek: Place, *, instellingen: bool) -> None:
        if isinstance(value, Mapping):
            naam = value.get("name")
            for key, child in value.items():
                if (str(key).lower() in USER_LIST_KEYS and has_value(child)) or secret_text_reasons(
                    str(key), settings=True
                ):
                    codes.add("account_gegevens_verboden")
                if key == "value" and isinstance(naam, str):
                    bezoek(child, plek.child(naam, whole=True), instellingen=True)
                else:
                    bezoek(child, plek.child(str(key)), instellingen=instellingen)
        elif isinstance(value, list):
            for child in value:
                bezoek(child, plek, instellingen=instellingen)
        else:
            ingevuld(value, plek, instellingen=instellingen, toets_geheimnaam=not ix_app)

    bezoek(values, Place(), instellingen=not ix_app)
    # De gepinde eigenaar toetst bij een standaard Custom App de geheimnaam van de omgevingsvariabele.
    envs = values.get("envs")
    if ix_app and isinstance(envs, list):
        for env in envs:
            if not isinstance(env, Mapping):
                continue
            naam, value = env.get("name"), env.get("value")
            if isinstance(naam, str):
                ingevuld(value, Place().child(naam, whole=True), instellingen=True, toets_geheimnaam=True)
    return codes
