"""Eigenaarsregels uit appstore-en-fork. Vernieuw deze kopie met tools/sync_asf_c12.py."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import Any, NamedTuple


BRONCOMMIT = 'a994c2a51f45b81b2c48c6533b0ccf51ba857f5a'


SECRET_WORDS: tuple[str, ...] = (
    "PASS",
    "PASSWD",
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "PRIVATEKEY",
    "CREDENTIAL",
    "AUTH_KEY",
    "SALT",
    "WACHTWOORD",
)


ACCOUNT_WORDS: tuple[str, ...] = (
    "BOOTSTRAP",
    "DEFAULTUSER",
    "DEFAULT_USER",
    "ADMIN",
    "ROOT",
    "SUPERUSER",
    "OWNER",
    "INITIAL",
    "SETUP",
    "BEHEER",
    "SERVICE_ACCOUNT",
    "SERVICEACCOUNT",
    "DIENST",
    "ADMINISTRATOR",
    "BEHEERDER",
    "DIENSTACCOUNT",
    "BEHEERACCOUNT",
    "SUPERADMIN",
    "ROOTUSER",
    "ADMINUSER",
    "INIT",
    "LOGIN",
    "BASIC_AUTH",
)


LOGIN_NAMES: frozenset[str] = frozenset({"JUPYTER_TOKEN", "PASSWORD"})


USER_LIST_KEYS = frozenset({"users", "gebruikers"})


_KEY_PARTS = re.compile(r"[.\[\]]+")


_BCRYPT = re.compile(r"2[abxy]\$+\+?[0-9]+\$+[./A-Za-z0-9]{53}")


_PHC = re.compile(r"\$(?:argon2|scrypt\$|pbkdf2)")


_JSON_ESCAPE = re.compile(r"\\(?:u([0-9A-Fa-f]{4})|([\"\\/bfnrt]))")


_SIMPLE_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


_IFS = re.compile(r"[ \t\n]+")


_SETTING = re.compile(r"([^=]+)=(.+)", re.DOTALL)


_XREF = re.compile(r"\[\s*msg\s*[.\[]", re.IGNORECASE)


_INDEX = re.compile(r"\[\s*[\"']?[0-9]+[\"']?\s*\]|\.[0-9]+(?=[.\[]|$)")


_NAME_ASSIGN = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_]+)[\"'\]]*=(?=[^ \t\n])")


_USERS_PREFIX = re.compile(r"(?<![A-Za-z0-9_])[\"']?(?:users|gebruikers)[\"']?\]?[.\[]", re.IGNORECASE)


_PATH_STOP = re.compile(r"[= \t\n]")


_ANY_WS = re.compile(r"\s*")


_JSON_WS = re.compile(r"[ \t\n\r]*")


_IFS_CHARS = " \t\n"


MAX_SECRET_TEXT = 64 * 1024


HIDDEN_KEY = "<verborgen>"


_R_HASH = "een wachtwoordhash (bcrypt of PHC-vorm)"


_R_GEHEIMNAAM = "een sleutel met een geheimnaam en een waarde"


_R_USERS = "een gebruikerslijst (users of gebruikers) met inhoud"


_R_FILE = "instellingen uit een bestand (@), buiten het zicht van de validator"


_R_XREF = "een kruisverwijzing ([msg.…]) of een index in de sleutel van een instelling"


_R_TE_LANG = f"een tekst van meer dan {MAX_SECRET_TEXT} tekens, te lang om op geheimen te toetsen (fail-closed)"


def _last_part(name: str) -> str:
    """Bij een sleutel met punten of ``[n]`` telt het laatste deel (``adminAuth.users[0].password`` → ``password``)."""
    parts = [p.strip().strip("\"'") for p in _KEY_PARTS.split(name)]
    parts = [p for p in parts if p]
    return parts[-1] if parts else ""


_SECRET_WORD_AT = tuple((word, re.compile(f"(?={re.escape(word)})", re.IGNORECASE)) for word in SECRET_WORDS)


_ACCOUNT_WORD_AT = tuple((word, re.compile(f"(?={re.escape(word)})", re.IGNORECASE)) for word in ACCOUNT_WORDS)


CACHED_NAME_MAX = 256


SHOWN_KEY_MAX = CACHED_NAME_MAX


def is_secret_name(name: str) -> bool:
    """Geheimnaam (ADR-0016 W2, ADR-0018); een korte naam komt uit de cache (ADR-0019, :data:`CACHED_NAME_MAX`)."""
    return _is_secret_name_cached(name) if len(name) <= CACHED_NAME_MAX else _is_secret_name(name)


@lru_cache(maxsize=4096)
def _is_secret_name_cached(name: str) -> bool:
    return _is_secret_name(name)


def _is_secret_name(name: str) -> bool:
    """Geheimnaam (ADR-0016 W2, ADR-0018): een van :data:`SECRET_WORDS` staat in de naam, gevolgd door het einde,
    ``_``, ``-``, ``.`` of een cijfer (``DB_PASSWORD2``, ``ADMIN_TOKEN1``), hoofdletterongevoelig, of door een
    hoofdletter na een kleine letter (camelCase: ``secretKey``, ``passwordHash``, ``apiKeyValue``; niet
    ``SECRETS_DIR``, ``TOKENS`` of ``PASSWORDLESS``). Het stuk tekst heeft precies de lengte van het woord: een teken
    dat met hoofdletters langer wordt (``ß`` → ``SS``) maakt er geen geheimwoord van (``paß``, ``Reisepaß``)."""
    part = _last_part(name)
    for word, at in _SECRET_WORD_AT:
        for m in at.finditer(part):
            start = m.start()
            end = start + len(word)
            if end > len(part) or part[start:end].upper() != word:
                continue
            if end == len(part) or part[end] in "_-." or part[end].isdigit():
                return True
            if part[end].isupper() and part[end - 1].islower():
                return True
    return False


def _part_edge(name: str, i: int) -> bool:
    """Ligt op positie ``i`` een grens tussen twee naamdelen (ADR-0019)? Het begin en het einde van de naam, naast elk
    teken dat geen letter of cijfer is (``_``, ``-``, ``.``, spatie), tussen een letter en een cijfer, op een
    camelCase-grens (``adminUser``) en vóór de laatste hoofdletter van een reeks hoofdletters (``ADMINUser``)."""
    if i <= 0 or i >= len(name):
        return True
    before, after = name[i - 1], name[i]
    if not before.isalnum() or not after.isalnum() or before.isdigit() != after.isdigit():
        return True
    if before.islower() and after.isupper():
        return True
    return before.isupper() and after.isupper() and i + 1 < len(name) and name[i + 1].islower()


def has_account_word(name: str) -> bool:
    """Staat een van :data:`ACCOUNT_WORDS` als heel naamdeel in de naam (ADR-0019, keuze van de regisseur)? Het woord
    begint en eindigt op een grens tussen naamdelen (:func:`_part_edge`), eventueel met een meervouds-``s``:
    ``admin``, ``Admin_ui``, ``adminUser``, ``root user``, ``admins``, ``admin2`` wel; ``phpmyadmin``, ``rootless``,
    ``groot``, ``administration`` niet. Hoofdletterongevoelig, zonder lengteverschil (zoals :func:`is_secret_name`)."""
    for word, at in _ACCOUNT_WORD_AT:
        for m in at.finditer(name):
            start = m.start()
            end = start + len(word)
            if end > len(name) or name[start:end].upper() != word or not _part_edge(name, start):
                continue
            if _part_edge(name, end) or (end < len(name) and name[end] in "sS" and _part_edge(name, end + 1)):
                return True
    return False


def _account_word_inside(name: str) -> bool:
    """Staat een van :data:`ACCOUNT_WORDS` ergens in de naam, ook midden in een woord (hoofdletterongevoelig)?"""
    upper = name.upper()
    return any(word in upper for word in ACCOUNT_WORDS)


def is_login_name(name: str) -> bool:
    """Is de hele naam een aanmeldnaam uit :data:`LOGIN_NAMES` (ADR-0023)? Hoofdletterongevoelig, zonder lengteverschil
    (zoals :func:`is_secret_name`)."""
    upper = name.upper()
    return len(upper) == len(name) and upper in LOGIN_NAMES


class Place(NamedTuple):
    """Een plek in ``values`` met wat zij van haar voorouders erft (ADR-0018). Een plek is een **geheimplek** als haar
    eigen naam of de naam van een voorouder een geheimnaam is (wat onder een geheimnaam ligt, erft die naam: een object
    net als een lijst), en een **accountplek** als zij een geheimplek is en haar eigen naam een accountnaam is of haar
    eigen naam of een voorouder een accountwoord als heel naamdeel heeft (``admin.password``, ``adminUser.password``,
    ``admin_password.x``; ADR-0019). De naam is een sleutel, of bij de ``value`` van een naam/waarde-paar de tekst
    onder ``name``. Elke naam wordt één keer getoetst (lineair, ook voor een naam die te lang is voor de cache;
    ADR-0019); een naam van meer dan :data:`SHOWN_KEY_MAX` tekens wordt nooit getoond (ADR-0021). ``whole``: de naam is
    de hele naam van een omgevingsvariabele (de ``name`` van een naam/waarde-paar of van ``values.envs``); dan telt ook
    een aanmeldnaam uit :data:`LOGIN_NAMES` (ADR-0023), bij een sleutel niet."""

    #: de eigen naam van de plek
    name: str = ""
    #: de naam die haar een geheimplek maakt (de eigen naam of die van de dichtstbijzijnde voorouder), of ``""``
    secret_name: str = ""
    #: de eigen naam of een voorouder heeft een accountwoord (ADR-0019: als heel naamdeel, of een accountnaam)
    account_word: bool = False
    #: ``secret_name`` zoals hij in een melding staat (:func:`shown_key`), één keer berekend
    shown_secret: str = ""

    def child(self, name: str, *, whole: bool = False) -> Place:
        secret = is_secret_name(name)
        return Place(
            name,
            name if secret else self.secret_name,
            self.account_word
            or has_account_word(name)
            or (secret and _account_word_inside(_last_part(name)))
            or (whole and is_login_name(name)),
            shown_key(name) if secret else self.shown_secret,
        )

    @property
    def secret(self) -> bool:
        return self.secret_name != ""

    @property
    def account(self) -> bool:
        return self.secret and self.account_word


def shown_key(key: str) -> str:
    """Een sleutel zoals hij in een pad of melding staat. Met een ``=`` of met iets dat T1 of T2 herkent, staat er
    :data:`HIDDEN_KEY`, want zo'n sleutel kan zelf een waarde dragen (ADR-0018). Een sleutel van meer dan
    :data:`SHOWN_KEY_MAX` tekens staat er ook als :data:`HIDDEN_KEY` (ADR-0021: één vaste vorm, zonder de sleutel te
    lezen). Elke andere sleutel komt uit de cache (ADR-0019)."""
    return _shown_key_cached(key) if len(key) <= SHOWN_KEY_MAX else HIDDEN_KEY


@lru_cache(maxsize=4096)
def _shown_key_cached(key: str) -> str:
    return HIDDEN_KEY if "=" in key or secret_text_reasons(key, settings=True) else key


def has_value(value: Any) -> bool:
    """Niet-lege waarde (ADR-0016 W2, ADR-0018): elke tekst behalve de lege tekst (ook alleen spaties, U+00A0 of
    stuurtekens: bash, ``nopt`` en de apps zien die als waarde), een getal of een niet-lege lijst of object. Ja/nee en
    ``null`` tellen niet: een geheim is nooit een boolean."""
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, list | dict):
        return len(value) > 0
    return True


def has_password_hash(text: str) -> bool:
    """T1: een wachtwoordhash in de tekst zoals hij er staat (zie :data:`_BCRYPT` en :data:`_PHC`)."""
    return bool(_BCRYPT.search(text) or _PHC.search(text))


def _unescape(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return chr(int(m.group(1), 16)) if m.group(1) else _SIMPLE_ESCAPES[m.group(2)]

    return _JSON_ESCAPE.sub(repl, text)


def _json_or_text(raw: str) -> Any:
    """Zoals ``red.js``: de waarde gaat door ``JSON.parse``; lukt dat niet, dan blijft het tekst."""
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        return raw


def _decoded_reasons(value: Any) -> list[str]:
    """T2 stap 1 op een gedecodeerde waarde: geheimnaam met waarde, gebruikerslijst met inhoud of een hash (T1)."""
    reasons: list[str] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, sub in item.items():
                text = str(key)
                if is_secret_name(text) and has_value(sub):
                    reasons.append(_R_GEHEIMNAAM)
                if _last_part(text).lower() in USER_LIST_KEYS and isinstance(sub, list | dict) and sub:
                    reasons.append(_R_USERS)
                if has_password_hash(text):
                    reasons.append(_R_HASH)
                stack.append(sub)
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and has_password_hash(item):
            reasons.append(_R_HASH)
    return reasons


def t2_setting_reasons(text: str) -> list[str]:
    """T2 stap 1 (ADR-0016 W2): de tekst splitsen zoals bash en elk woord decoderen zoals Node-RED, zonder optielijst.

    Het deel na de eerste ``=`` van een woord met ``-`` vooraan, en elk woord zonder ``-`` vooraan met een ``=``, telt
    als instelling (ook een los woord: fail-closed). Een instelling of woord dat met ``@`` begint, leest een bestand.
    Een woord zonder ``-`` en ``=`` dat met ``{`` of ``[`` begint, wordt als JSON gelezen. ADR-0017: een kruisverwijzing
    of index in de sleutel is ook een fout. Geeft de redenen, nooit de waarde."""
    reasons: list[str] = []
    for word in _IFS.split(text):
        if not word:
            continue
        candidate: str | None = None
        if word.startswith("-"):
            if "=" in word:
                candidate = word.split("=", 1)[1]
                if candidate.startswith("@"):
                    reasons.append(_R_FILE)
                    continue
        elif word.startswith("@"):
            reasons.append(_R_FILE)
            continue
        elif "=" in word:
            candidate = word
        elif word[0] in "{[":
            reasons.extend(_decoded_reasons(_json_or_text(word)))
            continue
        setting = _SETTING.fullmatch(candidate) if candidate is not None else None
        if setting is None:
            continue
        key, value = setting.group(1), _json_or_text(setting.group(2))
        if _XREF.search(key) or _INDEX.search(key):
            reasons.append(_R_XREF)
        if is_secret_name(key) and has_value(value):
            reasons.append(_R_GEHEIMNAAM)
        if _last_part(key).lower() in USER_LIST_KEYS and isinstance(value, list | dict) and value:
            reasons.append(_R_USERS)
        if has_password_hash(key):
            reasons.append(_R_HASH)
        reasons.extend(_decoded_reasons(value))
    return reasons


def _closing_quotes(text: str) -> list[int]:
    """Per positie ``p``: de positie van de ``"`` die een JSON-tekst sluit waarvan de inhoud op ``p`` begint, of -1.

    Hetzelfde als ``"((?:[^"\\]|\\.)*)"`` vanaf elke ``"`` (een ``\\`` slaat het volgende teken over, behalve een
    regeleinde), maar één keer van rechts naar links gelezen: lineair, ook als geen enkele tekst sluit (ADR-0018)."""
    n = len(text)
    close = [-1] * (n + 2)
    for p in range(n - 1, -1, -1):
        ch = text[p]
        if ch == '"':
            close[p] = p
        elif ch == "\\":
            close[p] = close[p + 2] if p + 1 < n and text[p + 1] != "\n" else -1
        else:
            close[p] = close[p + 1]
    return close


def _skip(pattern: re.Pattern[str], text: str, pos: int) -> int:
    """Positie na de witruimte die ``pattern`` vanaf ``pos`` vindt (het patroon kan leeg zijn)."""
    m = pattern.match(text, pos)
    return m.end() if m else pos


def _json_keys(text: str, close: list[int]) -> Iterator[tuple[str, int]]:
    """Elke JSON-sleutel ``"naam":`` in de tekst, met de positie van de waarde erna, in dezelfde volgorde als een
    zoektocht van links naar rechts die bij elke ``"`` opnieuw begint (ook binnen een andere tekst: fail-closed), in
    lineaire tijd."""
    n = len(text)
    after: dict[int, int] = {}
    pos = 0
    while (start := text.find('"', pos)) >= 0:
        end = close[start + 1]
        if end >= 0 and end not in after:
            colon = _skip(_ANY_WS, text, end + 1)
            after[end] = _skip(_JSON_WS, text, colon + 1) if colon < n and text[colon] == ":" else -1
        value_at = after.get(end, -1) if end >= 0 else -1
        if value_at < 0:
            pos = start + 1
            continue
        yield text[start + 1 : end], value_at
        pos = value_at


def _json_value_follows(text: str, pos: int, close: list[int], *, containers_only: bool) -> bool:
    """Staat er na een JSON-sleutel een niet-lege waarde (alleen lijst/object bij ``containers_only``)? Een tekst
    telt zodra zij niet leeg is (ADR-0018: niet strippen); een tekst die niet sluit, telt ook (fail-closed)."""
    if pos >= len(text):
        return False
    rest = text[pos]
    if rest in "[{":
        inner = _skip(_JSON_WS, text, pos + 1)
        return inner < len(text) and text[inner] != ("]" if rest == "[" else "}")
    if containers_only:
        return False
    if rest == '"':
        end = close[pos + 1]
        return end < 0 or end > pos + 1
    if text.startswith(("true", "false", "null"), pos):
        return False
    return rest not in ",}]"


def _users_path(text: str) -> bool:
    """Een pad met een deel ``users``/``gebruikers`` (ook tussen aanhalingstekens of haken) gevolgd door ``[`` of
    ``.``, vóór een ``=`` met een waarde; het pad stopt bij de eerste ``=`` of IFS-witruimte. Lineair: elk begin van
    een pad hergebruikt de eerste stop die al gevonden is."""
    stop = -1
    for m in _USERS_PREFIX.finditer(text):
        if stop < m.end():
            found = _PATH_STOP.search(text, m.end())
            if found is None:
                return False
            stop = found.start()
        if text[stop] == "=" and stop + 1 < len(text) and text[stop + 1] not in _IFS_CHARS:
            return True
    return False


def t2_safety_net_reasons(text: str) -> list[str]:
    """T2 stap 2, het vangnet (ADR-0016 W2): los van stap 1, op de tekst zelf én op dezelfde tekst met alle
    JSON-escapes opgelost. Een JSON-sleutel met een geheimnaam en een waarde, een JSON-sleutel ``users``/``gebruikers``
    met inhoud, een ``naam=`` met waarde waarin ``naam`` een geheimnaam is, een pad met een deel ``users`` of
    ``gebruikers`` vóór een ``=`` met waarde, en een hash volgens T1. Alles in lineaire tijd (ADR-0018)."""
    reasons: list[str] = []
    for variant in dict.fromkeys((text, _unescape(text))):
        if '"' in variant:
            close = _closing_quotes(variant)
            for raw_key, value_at in _json_keys(variant, close):
                key = _unescape(raw_key)
                if is_secret_name(key) and _json_value_follows(variant, value_at, close, containers_only=False):
                    reasons.append(_R_GEHEIMNAAM)
                if _last_part(key).lower() in USER_LIST_KEYS and _json_value_follows(
                    variant, value_at, close, containers_only=True
                ):
                    reasons.append(_R_USERS)
        if any(is_secret_name(m.group(1)) for m in _NAME_ASSIGN.finditer(variant)):
            reasons.append(_R_GEHEIMNAAM)
        if _users_path(variant):
            reasons.append(_R_USERS)
        if has_password_hash(variant):
            reasons.append(_R_HASH)
    return reasons


def secret_text_reasons(text: str, *, settings: bool) -> list[str]:
    """Tekstregels van ADR-0016 W2: T1 op elke tekst; met ``settings`` ook T2 (stap 1 en het vangnet). Elke reden
    één keer, in vaste volgorde. Een tekst langer dan :data:`MAX_SECRET_TEXT` wordt niet getoetst maar geweigerd
    (ADR-0018, fail-closed)."""
    if len(text) > MAX_SECRET_TEXT:
        return [_R_TE_LANG]
    reasons = t2_setting_reasons(text) + t2_safety_net_reasons(text) if settings else []
    if has_password_hash(text):
        reasons.append(_R_HASH)
    return list(dict.fromkeys(reasons))
