"""Preview van een actie: wat er nu staat, wat er verandert en wat er blijft (B01-007, B01-003).

De preview is een pure functie van (beleid, classificatie, doel, parameters, eigen readback) — geen klok, geen
willekeur. ``preview_hash`` = SHA-256 over de canonieke JSON. Een beheerder keurt precies deze preview goed; verandert
er iets aan (andere image of digest op de NAS, ander beleid, andere risicoklasse), dan verandert de hash en vervalt de
goedkeuring (EX19).

Geheimen: waarden van omgevingsvariabelen staan nooit in de preview (alleen de namen); verwijzingen naar de kluis
(``vault://…``) worden als verwijzing getoond, nooit ingevuld.

Installeren (S-P2-040, R-VEILIG-1; ADR-0030 besluit 32): ``wijziging.waarden`` toont elk gezet veld van
``app_create.values`` mét zijn waarde, zodat een beheerder niets ongezien goedkeurt; alleen een geheim niet.
``command`` en ``entrypoint`` komen hier niet: die weigert de Hub al bij het voorstel (:func:`eigen_opdracht`, besluit
regisseur optie C) tot een installatiescherm ze veilig kan tonen.

Eén principe (S-P2-040 herstelronde 4, besluit regisseur; ADR-0030 besluit 32): :func:`bouw` stuurt de hele
``wijziging`` van elke actie door één toonfunctie (:func:`_toon`); er staat geen rauw veld in. Die toont alles,
behalve:

- onder een geheim-achtige sleutel (:func:`_geheime_naam`: ``hub.redact`` op de naam zoals hij is en genormaliseerd,
  een naam die op ``key`` of ``keys`` eindigt (niet de kale ``key`` of ``keys``), met ``pwd``, met ``auth`` als los
  deel, of met ``oauth``, ``jwt``, ``otp``, ``mnemonic``, ``salt``, ``seed`` of ``webhook``): de vorm blijft staan,
  elk tekst- en getalblad wordt ``***``. Een absoluut configuratiepad is alleen zichtbaar bij een bekende padnaam;
- in een paar (een object met ``name`` of ``key`` én ``value``, elke schrijfwijze, genormaliseerd zoals ``_nk`` in het
  beleid): de ``value`` als ``***`` bij een ``name`` (een omgevingsvariabele, ADR-0030 besluit 28) of bij een
  geheim-achtige ``key``;
- onder een sleutel met een omgevingsbetekenis (een deel van de sleutel eindigt op ``env``, ``envs``,
  ``environment(s)`` of ``environ``, of is ``omgeving``; ``venv`` niet; :func:`_is_omgeving`): alleen namen die kort en
  niet willekeurig zijn (:func:`_omgeving`, :func:`_namen`), en een absoluut pad bij ``env_file(s)``;
- elke andere tekst, ook een sleutel, gaat door ``redact_text`` (URL met wachtwoord of geheim queryveld, ``Bearer``).

Leeg (``None``, ``""``) en ja/nee blijven altijd zichtbaar, ook onder een geheim-achtige naam (S-P2-040 herstelronde
6). Ook ``huidig`` (de readback van de NAS) gaat door :func:`_toon`; alleen ``target`` en ``resource_etag`` blijven
bewust rauw (S-P2-040 herstelronde 5; de reden staat bij de bewakingstest in
``apps/api/tests/unit/test_preview_toon.py``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from asm_policy import Policy, execreq
from asm_policy.canonical import canonical_sha256
from asm_policy.engine import Classification
from asm_policy.loader import ActieDef
from asm_policy.params import IX_APP, NIET_ALFANUM_RE, expected_image, vault_refs

from hub.actions.doel import Doel
from hub.redact import LOG_SECRET_KEY_RE, REDACTED, _entropy, redact_text

SCHEMA = "asm-preview/1"
DATA_BLIJFT = "Datasets en data blijven staan; de Hub en de executor verwijderen nooit data."


def _lijst(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


# Hoe elk veld van de standaard Custom App (``asm_policy.params.IX_VALUES_KEYS``) in ``wijziging.waarden`` staat
# (S-P2-040, R-VEILIG-1). Een bewakingstest eist een regel voor elk veld dat het beleid toelaat: een nieuw veld zonder
# regel maakt hem rood (``apps/api/tests/integration/test_acties.py``).
WAARDE = "waarde"  # met zijn waarde (een geheim daarin als ***)
NAMEN = "namen"  # alleen de namen; de waarden kunnen geheimen zijn (ADR-0030 besluit 28)
GEWEIGERD = "geweigerd"  # de Hub weigert een voorstel met dit veld (501 capability_unavailable, eigen_opdracht)
IX_PREVIEWREGELS: dict[str, str] = {
    "notes": WAARDE,
    "image": WAARDE,
    "hostname": WAARDE,
    "entrypoint": GEWEIGERD,
    "command": GEWEIGERD,
    "TZ": WAARDE,
    "envs": NAMEN,
    "restart_policy": WAARDE,
    "max_retry_count": WAARDE,
    "disable_builtin_healthcheck": WAARDE,
    "tty": WAARDE,
    "stdin": WAARDE,
    "devices": WAARDE,
    "privileged": WAARDE,
    "capabilities": WAARDE,
    "run_as_custom_user": WAARDE,
    "run_as": WAARDE,
    "host_network": WAARDE,
    "ports": WAARDE,
    "networks": WAARDE,
    "dns_config": WAARDE,
    "portals": WAARDE,
    "storage": WAARDE,
    "labels": WAARDE,
    "resources": WAARDE,
}
EIGEN_OPDRACHT = tuple(sorted(k for k, regel in IX_PREVIEWREGELS.items() if regel == GEWEIGERD))
GEHEIM_DIEPTE = 24  # dieper dan de dieptegrens van het beleid (MAX_PARAMETER_DIEPTE): daar komt het nooit


def eigen_opdracht(action_id: str, parameters: Mapping[str, Any]) -> list[str]:
    """De velden ``command`` en ``entrypoint`` die in de waarden van een installatie staan (elke waarde, ook leeg).

    Besluit regisseur (S-P2-040, R-VEILIG-1 optie C): de Hub weigert zo'n voorstel met ``501 capability_unavailable``
    (``details.reden`` = ``eigen_opdracht``) tot er een installatiescherm is dat de opdracht veilig kan tonen; ook een
    open voorstel van vóór dat besluit wordt bij goedkeuren of uitvoeren geweigerd."""
    if action_id != "app.install":
        return []
    ac = parameters.get("app_create") if isinstance(parameters, Mapping) else None
    values = ac.get("values") if isinstance(ac, Mapping) else None
    if not isinstance(values, Mapping):
        return []
    return [k for k in EIGEN_OPDRACHT if k in values]


DEEL_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")  # de delen van een sleutel (``_ . -`` en camelCase)


def _delen(sleutel: Any) -> list[str]:
    """De delen van een sleutel in kleine letters, gescheiden door elk teken dat geen letter of cijfer is en door een
    hoofdletterovergang: ``additionalEnvs`` en ``ADDITIONAL_ENVS`` geven ``["additional", "envs"]``."""
    return [d.lower() for d in DEEL_RE.findall(str(sleutel))]


# Geheim-achtige woorden (S-P2-040 herstelronde 6, R-VEILIG-19; besluit regisseur), als los deel van de naam of aan
# het eind van de genormaliseerde naam (``dbsalt``, ``walletseed``). ``pin`` bewust niet: te veel valse treffers.
GEHEIME_WOORDEN = ("oauth", "jwt", "otp", "mnemonic", "salt", "seed", "webhook")
SLEUTEL_EINDES = ("key", "keys")  # niet de kale key (de naam van een labelpaar) of keys
OPENBARE_SLEUTELS = frozenset({"publickey", "publickeys"})


def _geheime_naam(naam: Any) -> bool:
    """Een geheim-achtige sleutelnaam (S-P2-040 herstelronde 5 en 6, R-VEILIG-14 en -19; besluiten regisseur):
    ``hub.redact`` op de naam zoals hij is én genormaliseerd (``api.key`` wordt ``apikey``), een naam die genormaliseerd
    op ``key`` of ``keys`` eindigt (``encryption_key``, ``ssh_keys``; de kale ``key`` en ``keys`` niet), een naam met
    ``pwd``, met ``auth`` als los deel, of met een van :data:`GEHEIME_WOORDEN` als los deel of aan het eind. Een
    expliciete openbare sleutelnaam is zichtbaar."""
    if not isinstance(naam, str):
        return False
    nk = _nk(naam)
    delen = _delen(naam)
    if naam.lower() in OPENBARE_SLEUTELS or (delen[:1] == ["public"] and nk in OPENBARE_SLEUTELS):
        return False
    return (
        bool(LOG_SECRET_KEY_RE.search(naam) or LOG_SECRET_KEY_RE.search(nk))
        or (nk.endswith(SLEUTEL_EINDES) and nk not in SLEUTEL_EINDES)
        or "pwd" in nk
        or "auth" in delen
        or any(w in delen for w in GEHEIME_WOORDEN)
        or nk.endswith(GEHEIME_WOORDEN)
        or "webhook" in nk
    )


def _verborgen(waarde: Any) -> bool:
    """Een waarde die als ``***`` verschijnt als hij geheim is: alles behalve leeg en ja/nee."""
    return waarde not in (None, "") and not isinstance(waarde, bool)


def _verberg(waarde: Any) -> Any:
    return REDACTED if _verborgen(waarde) else waarde


def _nk(sleutel: Any) -> str:
    """Een sleutel genormaliseerd voor vergelijking, zoals het beleid (``asm_policy.params._nk``): kleine letters en
    alleen letters en cijfers (``Additional-Envs``, ``additionalEnvs`` en ``additional_envs`` worden
    ``additionalenvs``)."""
    return NIET_ALFANUM_RE.sub("", str(sleutel).lower())


# Een sleutel met een omgevingsbetekenis heeft een deel (:func:`_delen`) dat een van deze woorden is, een samenstelling
# met vars/variables (S-P2-040 herstelronde 5, R-VEILIG-16), of een deel dat op een van OMGEVING_EINDES eindigt
# (herstelronde 6, R-VEILIG-18: additionalenvs, extraenv, appenv, environ, dotenv). Venv uitdrukkelijk niet; openvpn en
# envoy eindigen niet op env.
OMGEVING_WOORDEN = frozenset(
    {"env", "envs", "envconfig", "environment", "environments", "omgeving", "vars", "variables"}
)
OMGEVING_EINDES = ("env", "envs", "environment", "environments", "environ")
GEEN_OMGEVING = frozenset({"venv"})
OMGEVING_SAMENGESTELD_RE = re.compile(r"(?:env|environment|omgevings?)(?:vars?|variables?|variabelen?)")
PAAR_NAMEN = ("name", "key")  # de naam van een paar; met beide telt name (de waarde is dan altijd geheim)
PAAR_WAARDE = "value"
NAAM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")  # een variabelenaam (volledig)
SCHEIDING_RE = re.compile(r"[=:]")
KORT = 64  # een naam onder een omgevingssleutel is hooguit zo lang (R-VEILIG-17)
ENTROPIE_DREMPEL = 4.0  # dezelfde drempel als ``hub.redact._maybe_secret``
HEX_RE = re.compile(r"[0-9A-Fa-f]{16,}")
HEX_MET_STREEPJES_RE = re.compile(r"[0-9a-fA-F]+(?:-[0-9a-fA-F]+)+")
PAD_RE = re.compile(r"/[^\x00-\x1f\x7f=:]+")  # één regel, met ruimte voor echte bestandsnamen
OMGEVING_PADSLEUTELS = frozenset({"envfile", "envfiles"})
GEHEIME_PADSLEUTELS = frozenset({"clientsecretfile", "seedpath", "tlskey", "sslkey"})


def _is_omgeving(sleutel: Any) -> bool:
    return any(
        d in OMGEVING_WOORDEN
        or OMGEVING_SAMENGESTELD_RE.fullmatch(d)
        or (d.endswith(OMGEVING_EINDES) and d not in GEEN_OMGEVING)
        for d in _delen(sleutel)
    )


def _willekeurig(woord: str) -> bool:
    """Een woord dat op een geheim lijkt (R-VEILIG-17; besluit regisseur: de entropietoets van
    ``hub.redact._maybe_secret`` of gelijkwaardig). Strenger dan ``_maybe_secret``, omdat een kort woord de drempel van
    4,0 nooit haalt: met een cijfer én (hoofd- en kleine letters, of een entropie van minstens 4,0, of een hexreeks van
    minstens 16 tekens). Een woord zonder cijfer (``production``, ``DB_HOST``) is niet willekeurig."""
    hex_met_streepjes = bool(HEX_MET_STREEPJES_RE.fullmatch(woord) and HEX_RE.fullmatch(woord.replace("-", "")))
    if hex_met_streepjes:
        return True
    if not any(c.isdigit() for c in woord):
        return False
    gemengd = any(c.isupper() for c in woord) and any(c.islower() for c in woord)
    return gemengd or _entropy(woord) >= ENTROPIE_DREMPEL or bool(HEX_RE.fullmatch(woord))


def _pad(tekst: str) -> bool:
    """Een absoluut pad op één regel, alleen gebruikt bij bekende configuratievelden."""
    return bool(PAD_RE.fullmatch(tekst)) and len(tekst.splitlines()) == 1


def _naam(regel: str) -> str:
    """Eén regel in een omgevingscontext: de naam vóór het eerste ``=`` of ``:`` (zonder scheiding: de hele regel) als
    die op een variabelenaam lijkt (:data:`NAAM_RE`), kort is (:data:`KORT`) en niet willekeurig
    (:func:`_willekeurig`); anders ``***``. Ook de naam vóór een scheiding wordt zo getoetst, dus een '='-staart (de
    opvulling van base64) helpt een geheim niet. Een lege regel blijft leeg."""
    if not regel.strip():
        return ""
    naam = SCHEIDING_RE.split(regel, maxsplit=1)[0].strip()
    goed = NAAM_RE.fullmatch(naam) and len(naam) <= KORT and not _willekeurig(naam)
    return naam if goed else REDACTED


def _paarsoort(waarde: Mapping[str, Any]) -> str | None:
    """``"name"`` of ``"key"`` als het object een paar is: een naam (``name`` of ``key``) én een ``value``, in elke
    schrijfwijze. Een object met alleen een naam (zoals een portaal) of alleen een waarde is geen paar."""
    soorten = {_nk(k) for k in waarde}
    if PAAR_WAARDE not in soorten:
        return None
    return next((s for s in PAAR_NAMEN if s in soorten), None)


def _namen(tekst: str) -> str:
    """Tekst in een omgevingscontext, per regel als :func:`_naam`."""
    return "\n".join(_naam(regel) for regel in tekst.splitlines())


def _omgevingssleutel(sleutel: Any) -> str:
    """Een sleutel van een omgevingsobject volgt de naamregel (R-VEILIG-17): ``NAAM=geheim`` wordt ``NAAM``, een
    willekeurige sleutel ``***``; een sleutel die al een naam is, blijft zoals hij is (ook met spaties)."""
    tekst = str(sleutel)
    naam = _namen(tekst)
    return tekst if naam == tekst.strip() else naam


def _zet(uit: dict[str, Any], sleutel: Any, waarde: Any) -> None:
    """Een sleutel staat als tekst in de preview: ook hij gaat door ``redact_text``. Worden twee sleutels daardoor
    gelijk, dan blijven ze allebei staan (met een volgnummer), zodat er niets ongezien verdwijnt."""
    tekst = redact_text(str(sleutel))
    naam, n = tekst, 2
    while naam in uit:
        naam, n = f"{tekst} ({n})", n + 1
    uit[naam] = waarde


def _omgeving(waarde: Any, diepte: int, *, padveld: bool = False) -> Any:
    """De waarde onder een sleutel met een omgevingsbetekenis: alleen namen (S-P2-040 herstelronde 4, besluit
    regisseur; ADR-0030 besluit 28). Een tekst per regel als :func:`_namen` (een absoluut pad, zoals van ``env_file``,
    blijft zichtbaar: :func:`_pad`); een object toont zijn sleutels met elke
    waarde als ``***``, en bij een paar daarnaast de naam; een lijst elk element zo (een getal of een geneste lijst als
    ``***``). De sleutels van een object volgen de naamregel (:func:`_omgevingssleutel`). Leeg en ja/nee blijven
    zichtbaar."""
    if diepte > GEHEIM_DIEPTE:
        return REDACTED
    if isinstance(waarde, str):
        return redact_text(waarde) if padveld and _pad(waarde) else _namen(waarde)
    if isinstance(waarde, list | tuple):
        return [
            _omgeving(w, diepte + 1, padveld=padveld) if isinstance(w, str | Mapping) else _verberg(w) for w in waarde
        ]
    if isinstance(waarde, Mapping):
        soort = _paarsoort(waarde)
        uit: dict[str, Any] = {}
        for k, w in waarde.items():
            naam = soort is not None and _nk(k) == soort and isinstance(w, str)
            _zet(uit, _omgevingssleutel(k), _namen(w) if naam else _verberg(w))
        return uit
    return _verberg(waarde)


def _vormsleutel(sleutel: Any) -> str:
    """Een sleutel onder een geheim-achtige naam blijft zichtbaar, behalve als hij zelf op een geheim lijkt: met
    ``=`` of ``:`` of willekeurig volgt hij de naamregel van een omgevingsobject (:func:`_omgevingssleutel`)."""
    tekst = str(sleutel)
    return _omgevingssleutel(tekst) if SCHEIDING_RE.search(tekst) or _willekeurig(tekst) else tekst


def _vorm(waarde: Any, diepte: int, *, padveld: bool = False) -> Any:
    """De waarde onder een geheim-achtige naam (S-P2-040 herstelronde 6, R-VEILIG-20; besluit regisseur): de vorm blijft
    staan. Sleutels (:func:`_vormsleutel`), ja/nee, leeg en ``None`` zijn zichtbaar; elk tekst- en getalblad is ``***``,
    behalve een absoluut pad (:func:`_pad`). Zo ziet de beheerder dat ``basic_auth`` uit staat."""
    if diepte > GEHEIM_DIEPTE:
        return REDACTED
    if isinstance(waarde, Mapping):
        uit: dict[str, Any] = {}
        for k, w in waarde.items():
            _zet(uit, _vormsleutel(k), _vorm(w, diepte + 1))
        return uit
    if isinstance(waarde, list | tuple):
        return [_vorm(w, diepte + 1, padveld=padveld) for w in waarde]
    if padveld and isinstance(waarde, str) and _pad(waarde):
        return redact_text(waarde)
    return _verberg(waarde)


def _toon(waarde: Any, diepte: int = 0) -> Any:
    """Een waarde zoals de beheerder hem in de preview ziet: alles, behalve een geheim (zie de moduletekst). Elke
    ``wijziging`` gaat hier in zijn geheel doorheen (:func:`bouw`)."""
    if diepte > GEHEIM_DIEPTE:
        return REDACTED
    if isinstance(waarde, Mapping):
        soort = _paarsoort(waarde)
        label = next((w for k, w in waarde.items() if soort == "key" and _nk(k) == "key" and _geheime_naam(w)), None)
        uit: dict[str, Any] = {}
        for k, w in waarde.items():
            if soort == "name" and _nk(k) == PAAR_WAARDE:
                _zet(uit, k, _verberg(w))  # de waarde van een omgevingsvariabele (besluit 28): nooit de vorm
            elif k == "seed_ratio" and type(w) in (int, float):
                _zet(uit, k, w)
            elif _geheime_naam(k) or (_nk(k) == PAAR_WAARDE and label is not None):
                veld = label if _nk(k) == PAAR_WAARDE else k
                _zet(uit, k, _vorm(w, diepte + 1, padveld=_nk(veld) in GEHEIME_PADSLEUTELS))
            elif _is_omgeving(k):
                _zet(uit, k, _omgeving(w, diepte + 1, padveld=_nk(k) in OMGEVING_PADSLEUTELS))
            else:
                _zet(uit, k, _toon(w, diepte + 1))
        return uit
    if isinstance(waarde, list | tuple):
        return [_toon(w, diepte + 1) for w in waarde]
    if isinstance(waarde, str):
        return redact_text(waarde)
    return waarde


def toon_bewaarde_preview(preview: dict[str, Any]) -> dict[str, Any]:
    """Pas de huidige maskering ook toe op historische previews bij lijst en detail."""
    return {k: _toon(w) if k in {"huidig", "wijziging"} else w for k, w in preview.items()}


def idempotency_response(body: Any) -> Any:
    """Pas dezelfde weergave toe bij een herhaling van een historisch actieantwoord."""
    if isinstance(body, dict) and isinstance(getoond := body.get("preview"), dict):
        return {**body, "preview": toon_bewaarde_preview(getoond)}
    return body


def _waarden(standaard: bool, values: Mapping[str, Any]) -> dict[str, Any]:
    """Elk gezet veld van ``app_create.values`` (R-VEILIG-1), nog zonder toon: :func:`bouw` stuurt de hele wijziging
    door :func:`_toon`. Bij de standaard Custom App volgens :data:`IX_PREVIEWREGELS` (van ``envs`` komen alleen de
    namen mee; een onbekend veld laat het beleid niet toe, mocht het er toch zijn, dan met waarde); bij een
    catalogusapp de eigen waarden zoals ze zijn."""
    if not standaard:
        return dict(values)
    uit: dict[str, Any] = {}
    for k, w in values.items():
        regel = IX_PREVIEWREGELS.get(k, WAARDE)
        if regel == NAMEN:
            uit[k] = [e.get("name") for e in _lijst(w) if isinstance(e, Mapping) and e.get("name")]
        elif regel == GEWEIGERD:
            uit[k] = {"geweigerd": "eigen_opdracht"}  # komt niet voor: het voorstel wordt al geweigerd
        else:
            uit[k] = w
    return uit


def _install(target: Mapping[str, Any], parameters: Mapping[str, Any]) -> dict[str, Any]:
    ac_raw = parameters.get("app_create")
    ac: Mapping[str, Any] = ac_raw if isinstance(ac_raw, Mapping) else {}
    values_raw = ac.get("values")
    values: Mapping[str, Any] = values_raw if isinstance(values_raw, Mapping) else {}
    manifest_raw = parameters.get("manifest")
    manifest: Mapping[str, Any] = manifest_raw if isinstance(manifest_raw, Mapping) else {}
    standaard = ac.get("catalog_app") == IX_APP
    resources = values.get("resources") if isinstance(values.get("resources"), Mapping) else {}
    return {
        "soort": "installeren",
        "app": str(target.get("app_id") or ""),
        "installatiemethode": "standaard Custom App (ix-app-waarden via app.create)"
        if standaard
        else f"catalogusapp {ac.get('catalog_app')} ({ac.get('train')})",
        "custom_compose": False,
        "catalogus": {"app": ac.get("catalog_app"), "trein": ac.get("train"), "versie": ac.get("version")},
        "image": expected_image(parameters),
        "poorten": [
            {
                "host_poort": p.get("port_number"),
                "container_poort": p.get("container_port"),
                "protocol": p.get("protocol", "tcp"),
                "bind_mode": p.get("bind_mode", "published"),
            }
            for p in _lijst(values.get("ports"))
            if isinstance(p, Mapping)
        ],
        "opslag": [
            {
                "type": s.get("type"),
                "mount_path": s.get("mount_path"),
                "host_path": (s.get("host_path_config") or {}).get("path")
                if isinstance(s.get("host_path_config"), Mapping)
                else None,
                "alleen_lezen": bool(s.get("read_only", False)),
            }
            for s in _lijst(values.get("storage"))
            if isinstance(s, Mapping)
        ],
        # Alleen de namen (omgevingscontext in _toon): een waarde kan een geheim zijn en hoort nooit in een preview.
        "omgevingsvariabelen": sorted(
            str(e.get("name")) for e in _lijst(values.get("envs")) if isinstance(e, Mapping) and e.get("name")
        ),
        "kluisverwijzingen": vault_refs(parameters),
        "resources": resources,
        "gpu": bool((resources or {}).get("gpus")) or bool(manifest.get("gpu")),
        "restart_policy": values.get("restart_policy"),
        "host_network": bool(values.get("host_network", False)),
        "host_network_reden": manifest.get("host_network_reason"),
        "privileged": False,
        "manifest": {
            k: manifest.get(k) for k in ("app_id", "version", "image_digest", "manifest_sha256") if k in manifest
        },
        "reden_catalogusapp": manifest.get("install_reason"),
        "controles_na_installatie": _lijst(manifest.get("post_install_checks")),
        "waarden": _waarden(standaard, values),
    }


def _wijziging(actie: ActieDef, target: Mapping[str, Any], parameters: Mapping[str, Any], doel: Doel) -> dict[str, Any]:
    """De wijziging nog zonder toon; :func:`bouw` stuurt hem in zijn geheel door :func:`_toon` (geen rauw veld)."""
    aid = actie.action_id
    if aid == "app.install":
        return _install(target, parameters)
    if aid == "app.uninstall":
        return {
            "soort": "verwijderen",
            "app": doel.naam,
            "alleen_containers": True,
            "remove_ix_volumes": False,
            "remove_images": False,
        }
    if aid == "app.update":
        if "image" in parameters:
            return {
                "soort": "bijwerken",
                "app": doel.naam,
                "van": doel.staat.get("images"),
                "naar": expected_image(parameters),
            }
        return {
            "soort": "bijwerken",
            "app": doel.naam,
            "van": doel.staat.get("versie"),
            "naar_catalogusversie": parameters.get("catalog_version"),
        }
    if aid == "app.rollback":
        if "herstel_van" in parameters:
            return {
                "soort": "terugzetten",
                "app": doel.naam,
                "methode": "app.update met de vorige waarden die de executor bij die wijziging bewaarde",
                "herstel_van": parameters.get("herstel_van"),
            }
        return {"soort": "terugzetten", "app": doel.naam, "naar_catalogusversie": parameters.get("catalog_version")}
    if aid in ("app.restart", "app.stop", "app.start"):
        return {"soort": aid.split(".", 1)[1], "app": doel.naam, "verwacht": dict(actie.verwacht)}
    if aid == "zfs.snapshot.create":
        return {
            "soort": "snapshot_maken",
            "snapshot": f"{doel.naam}@{parameters.get('naam')}",
            "recursief": bool(parameters.get("recursief", False)),
        }
    if aid == "zfs.snapshot.clone_to_sandbox":
        return {"soort": "snapshot_klonen", "snapshot": doel.naam, "naar": parameters.get("doel_dataset")}
    if aid == "notification.send":
        return {"soort": "melding", "titel": parameters.get("titel"), "prioriteit": parameters.get("prioriteit", 2)}
    return {"soort": aid}


TERUG_STOP_CUSTOM_APP = (
    "Niet via het platform. Een gestopte Custom App toont in TrueNAS geen image meer; het platform kan dan niet zien "
    "wat erin draait en weigert app.start (doel_niet_herkenbaar). Weer starten kan daarna alleen in de TrueNAS-web-UI."
)


def _terugdraaien(aid: str, doel: Doel) -> str:
    if aid == "app.stop" and not doel.herkend_als.na_stop_herkenbaar:
        # ADR-0030 besluit 21: daarom is dit R2 en vraagt het altijd een goedkeuring van een beheerder.
        return TERUG_STOP_CUSTOM_APP
    return {
        "app.install": "Verwijderen met app.uninstall (alleen de containers); de aangemaakte data blijft staan.",
        "app.uninstall": "Opnieuw installeren met app.install en dezelfde opslag; de data is niet verwijderd.",
        "app.update": "Terugzetten met app.rollback (herstel_van = dit verzoek); data via de eigenaar of een snapshot.",
        "app.rollback": "Opnieuw bijwerken met app.update, of nogmaals terugzetten met de waarden van dit verzoek.",
        "app.stop": "Starten met app.start.",
        "app.start": "Stoppen met app.stop.",
        "app.restart": "Niet nodig: de app wordt opnieuw uitgerold met dezelfde instellingen.",
        "zfs.snapshot.create": "Een snapshot wijzigt geen data; verwijderen doet een beheerder zelf in TrueNAS.",
        "zfs.snapshot.clone_to_sandbox": "De sandbox-dataset verwijdert een beheerder zelf in TrueNAS.",
        "notification.send": "Een verstuurde melding kan niet worden teruggehaald.",
    }.get(aid, "Geen automatische weg terug bekend.")


def bouw(
    policy: Policy,
    actie: ActieDef,
    cls: Classification,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    doel: Doel,
) -> tuple[dict[str, Any], str]:
    """``(preview, preview_hash)``."""
    preview: dict[str, Any] = {
        "schema": SCHEMA,
        "action_id": actie.action_id,
        "omschrijving": actie.omschrijving,
        "target": dict(target),
        "parameters_sha256": execreq.parameters_sha256(parameters),
        "uitvoerder": actie.uitvoerder,
        "risk_class": cls.risk_class,
        "rule_ids": list(cls.rule_ids),
        "goedkeuring_nodig": cls.requires_approval,
        "requires_backup": cls.requires_backup,
        "opslagmutatie": cls.opslagmutatie,
        "herkend_als": cls.herkend_als,
        "kritiek": cls.kritiek,
        "policy_hash": policy.hash,
        "resource_etag": doel.etag,
        "huidig": _toon(doel.staat),
        "wijziging": _toon(_wijziging(actie, target, parameters, doel)),
        "dataretentie": DATA_BLIJFT,
        "terugdraaien": _terugdraaien(actie.action_id, doel),
    }
    return preview, canonical_sha256(preview)
