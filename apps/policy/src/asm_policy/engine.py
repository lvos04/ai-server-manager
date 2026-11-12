"""Deterministische risicoclassificatie (B02-005, contract 1.3 §8, 03_RISICO_AUTONOMIE; ADR-0030).

``classify`` is een pure functie van (beleid, action_id, herkend doel, doel, parameters, soort actor): geen AI, geen
klok, geen netwerk. De Hub en de executor gebruiken dezelfde functie op hun eigen read-only kopie van het beleid; de
executor herkent het doel zelf uit zijn eigen TrueNAS-readback.

Regels (in deze volgorde, de strengste wint):
1. ``risk_claim`` van AI/flow wordt **nooit** gelezen (EX18): deze functie krijgt hem niet eens.
2. Verboden patronen (shell, destructief, beveiligingsbeleid, betaald, rechtstreekse database, netwerk) → R3 en
   geweigerd. Een LLM die "R0" claimt voor ``pool.dataset.delete`` krijgt dus R3 en een weigering.
3. Boiler in action_id, doel of parameters → R3 en geweigerd (EX27). Dieper genest dan de scangrens
   (:data:`asm_policy.canonical.MAX_DIEPTE`) telt als boiler: niet te zien is niet uit te sluiten (dicht bij twijfel).
4. Gereserveerde acties (MediaGuard tot BG-05/P3-02; my_house/MSO tot P3) → ``capability_unavailable``.
5. Onbekende action_id (niet in de allowlist) → ``known=False``: Hub en executor geven 403 ``actie_niet_toegestaan``
   en voeren niets uit.
6. Basisklasse uit ``acties.yaml``; kritieke apps (``apps.yaml``) → ``klasse_kritiek``. Nooit lager.
7. Beschermde apps (Emby altijd; Hub/executor niet stoppen; MediaGuard en de mediaserver geen update zonder bewijs)
   → geweigerd. Is van een bestaande app niet vast te stellen wat erin draait (geen image te zien, zoals bij een
   gestopte app, en geen catalogusapp), dan kan het een beschermde app zijn → elke actie op die app geweigerd.
8. Een actie met ``ai_mag_voorstellen: false`` van een AI- of flow-actor → geweigerd.
9. R2/R3 vragen menselijke goedkeuring per gebonden diff; R0/R1 mogen automatisch (allowlist, cooldown, anti-flap
   controleert de Hub dynamisch).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from asm_policy.canonical import MAX_DIEPTE, TeDiepGenest
from asm_policy.etag import app_images, catalogus_app
from asm_policy.loader import RISK_RANK, Policy

ACTOR_TYPES = ("user", "ai", "flow", "voice", "service", "system")
NIET_MENSELIJK = frozenset({"ai", "flow", "voice", "service", "system"})


@dataclass(frozen=True)
class Blokkade:
    id: str
    code: str
    reden_nl: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "code": self.code, "reden": self.reden_nl}


@dataclass(frozen=True)
class Classification:
    action_id: str
    known: bool
    risk_class: str
    rule_ids: tuple[str, ...]
    blokkades: tuple[Blokkade, ...] = ()
    gereserveerd: Blokkade | None = None
    requires_approval: bool = False
    requires_backup: bool = False
    opslagmutatie: bool = False
    uitvoerder: str | None = None
    herkend_als: str | None = None
    kritiek: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def geweigerd(self) -> bool:
        """Statisch geweigerd: geen goedkeuring kan dit openen."""
        return bool(self.blokkades)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "bekend": self.known,
            "risk_class": self.risk_class,
            "rule_ids": list(self.rule_ids),
            "blokkades": [b.as_dict() for b in self.blokkades],
            "gereserveerd": self.gereserveerd.as_dict() if self.gereserveerd else None,
            "goedkeuring_nodig": self.requires_approval,
            "requires_backup": self.requires_backup,
            "opslagmutatie": self.opslagmutatie,
            "uitvoerder": self.uitvoerder,
            "herkend_als": self.herkend_als,
            "kritiek": self.kritiek,
        }


@dataclass(frozen=True)
class Herkenning:
    """Herkenning van de app die het doel is, uit de eigen readback (:func:`herken_app`).

    ``volledig`` is onwaar als de app bestaat maar niet vast te stellen is wát erin draait: geen image te zien (TrueNAS
    geeft bij een gestopte app lege ``active_workloads``) en geen catalogusapp die het zegt. Dan kan het Emby,
    MediaGuard of de mediaserver zijn onder een andere naam, en weigert :func:`classify` elke actie op die app."""

    apps: tuple[str, ...]
    volledig: bool
    # Blijft de app na ``app.stop`` herkenbaar? Alleen een catalogusapp: zijn catalogusnaam zegt ook zonder image wat
    # erin draait. Een Custom App (ix-app of compose) toont gestopt geen image meer; het platform kan hem dan niet
    # meer starten (``DOEL_ONHERKENBAAR``). Daarom is ``app.stop`` daar R2 (``STOP_EENRICHTING``). Bewust zonder
    # standaardwaarde (dicht bij twijfel): wie een Herkenning maakt, moet het zeggen (S-P2-010).
    na_stop_herkenbaar: bool


DOEL_ONHERKENBAAR = Blokkade(
    "DOEL-ONHERKENBAAR",
    "doel_niet_herkenbaar",
    "Van deze app is nu niet te zien welke image erin draait (TrueNAS toont dat niet bij een gestopte app). Het "
    "platform kan dan niet uitsluiten dat het Emby, MediaGuard of de mediaserver is en weigert elke actie op deze "
    "app, ook met goedkeuring.",
)
# Besluit van de gebruiker (2026-11-11; ADR-0030 besluit 21): een Custom App die het platform stopt, kan het daarna
# niet meer starten. Stoppen is daar dus eenrichtingsverkeer: altijd R2 (goedkeuring van een beheerder), nooit
# automatisch, ook niet op voorstel van de AI, een flow of een runbook. Een catalogusapp blijft R1.
STOP_EENRICHTING = "STOP-EENRICHTING"
STOP_EENRICHTING_REDEN = (
    "Een Custom App die het platform stopt, kan het daarna niet meer starten: van een gestopte Custom App is niet te "
    "zien wat erin draait (doel_niet_herkenbaar). Daarom vraagt stoppen van een Custom App altijd de goedkeuring van "
    "een beheerder (R2) en gebeurt het nooit automatisch; een catalogusapp blijft R1."
)


def max_class(*classes: str) -> str:
    return max(classes, key=lambda c: RISK_RANK[c])


def class_at_least(value: str, minimum: str) -> bool:
    return value in RISK_RANK and RISK_RANK[value] >= RISK_RANK[minimum]


def _image_basenames(images: Iterable[str]) -> list[str]:
    out = []
    for ref in images:
        base = str(ref).lower().split("@", 1)[0].rsplit("/", 1)[-1]
        out.append(base.split(":", 1)[0])
    return out


def recognize_all(
    policy: Policy, name: str | None, images: Iterable[str] = (), *, catalogus: str | None = None
) -> tuple[str, ...]:
    """Alle herkenningen van een app: eerst op de appnaam, dan op de catalogusapp (``metadata.name``), dan per
    image-basisnaam. Per naam telt de exacte treffer, anders het langste voorvoegsel + ``-``/``_``.

    Naam, catalogusapp en image kunnen naar verschillende apps wijzen (een app die ``emby`` heet met een andere image,
    of andersom). Dan gelden de regels van **allemaal**: een herkenning is er alleen om strenger te zijn en opent nooit
    iets."""
    gevonden: list[str] = []
    sleutels = [n.lower() for n in (name, catalogus) if n]
    for h in sleutels + _image_basenames(images):
        treffer = next((app for app, needles in policy.herkenning.items() if h in needles), None)
        if treffer is None:
            best: tuple[int, str] | None = None
            for app, needles in policy.herkenning.items():
                for n in needles:
                    if (h.startswith(n + "-") or h.startswith(n + "_")) and (best is None or len(n) > best[0]):
                        best = (len(n), app)
            treffer = best[1] if best else None
        if treffer is not None and treffer not in gevonden:
            gevonden.append(treffer)
    return tuple(gevonden)


def herken_app(
    policy: Policy,
    name: str | None,
    app: Mapping[str, Any] | None,
    verwachte_images: Iterable[str] = (),
    *,
    catalogus: str | None = None,
) -> Herkenning:
    """Herkenning van het doel uit de ruwe readback (``app.query``), voor Hub én executor.

    Bestaat de app (``app``), dan tellen de naam, de catalogusapp en de images die TrueNAS toont, én de image(s) ná
    de actie (``verwachte_images``: de nieuwe image bij ``app.update``, de bewaarde vorige image bij ``app.rollback``):
    een bestaande app omzetten naar een Emby-image maakt er een tweede Emby van (S-P2-010, R-VEILIG-2). Volledig is
    de herkenning alleen als er nu een image te zien is of als de catalogusapp zegt wat er draait; een verwachte
    image maakt haar niet volledig (dicht bij twijfel). Na een stop blijft alleen een catalogusapp herkenbaar
    (``na_stop_herkenbaar``). Bestaat de app nog niet (installeren), dan tellen de naam, de image die geïnstalleerd
    gaat worden en de catalogusapp uit het voorstel (``catalogus``, zie :func:`asm_policy.params.verwachte_catalogus`):
    een tweede Emby onder een andere naam is ook Emby. Een herkenning maakt alleen strenger."""
    verwacht = [i for i in verwachte_images if i]
    cat = (catalogus or "").strip().lower() or None
    if app is None:
        return Herkenning(recognize_all(policy, name, verwacht, catalogus=cat), True, bool(cat))
    images = app_images(app)
    eigen = catalogus_app(app)
    gevonden = recognize_all(policy, name, images + verwacht, catalogus=eigen or None)
    if cat:
        gevonden += tuple(a for a in recognize_all(policy, None, catalogus=cat) if a not in gevonden)
    return Herkenning(gevonden, bool(images or eigen), bool(eigen))


def recognize(policy: Policy, name: str | None, images: Iterable[str] = ()) -> str | None:
    """De eerste herkenning (de appnaam gaat voor de image). Voor weergave; regels gebruiken :func:`recognize_all`."""
    alle = recognize_all(policy, name, images)
    return alle[0] if alle else None


def _strings(value: Any, depth: int = 0) -> Iterable[str]:
    """Alle sleutels en tekstwaarden (recursief) voor de boilercontrole. Dieper dan
    :data:`asm_policy.canonical.MAX_DIEPTE`: :class:`TeDiepGenest` (nooit stil stoppen; S-P2-010, R-VEILIG-1)."""
    if depth > MAX_DIEPTE:
        raise TeDiepGenest(f"dieper genest dan {MAX_DIEPTE} niveaus")
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k)
            yield from _strings(v, depth + 1)
    elif isinstance(value, list | tuple):
        for v in value:
            yield from _strings(v, depth + 1)


def mentions_boiler(policy: Policy, *values: Any) -> bool:
    """Noemt een sleutel of tekst de boiler? Te diep genest om alles te zien telt als ja (dicht bij twijfel)."""
    try:
        return any(p.search(s) for v in values for s in _strings(v) for p in policy.boiler_patronen)
    except TeDiepGenest:
        return True


def classify(
    policy: Policy,
    *,
    action_id: str,
    target: Mapping[str, Any] | None,
    parameters: Mapping[str, Any] | None,
    actor_type: str,
    herkend_als: str | Iterable[str] | Herkenning | None = None,
    requires_backup_claim: bool | None = None,
) -> Classification:
    """Zie de moduletekst. ``herkend_als`` = :func:`herken_app` (of :func:`recognize_all`) op het doel (de aanroeper
    leest het doel zelf uit); bij meer herkenningen gelden de regels van allemaal. Een onvolledige
    :class:`Herkenning` weigert elke actie op die app. ``requires_backup_claim`` uit het voorstel kan alleen
    **verhogen** (``true``), nooit verlagen."""
    onvolledig = isinstance(herkend_als, Herkenning) and not herkend_als.volledig
    if isinstance(herkend_als, Herkenning):
        herkend: tuple[str, ...] = herkend_als.apps
    else:
        herkend = (herkend_als,) if isinstance(herkend_als, str) else tuple(herkend_als or ())
    eerste = herkend[0] if herkend else None
    aid = action_id.strip().lower()
    target = target or {}
    parameters = parameters or {}
    rules: list[str] = []
    blocks: list[Blokkade] = []

    for v in policy.verboden:
        if v.patroon.fullmatch(aid):
            rules.append(v.id)
            blocks.append(Blokkade(v.id, v.code, v.reden_nl))
    # Vrije meldingstekst is geen doel: een melding óver de boiler (bewaking) schakelt niets. Bij elke andere actie
    # tellen ook de parameters mee (EX27).
    gezocht: tuple[Any, ...] = (aid, target) if aid == "notification.send" else (aid, target, parameters)
    if mentions_boiler(policy, *gezocht):
        rules.append(policy.boiler_id)
        blocks.append(Blokkade(policy.boiler_id, policy.boiler_code, policy.boiler_reden))
    if blocks:
        return Classification(aid, True, "R3", tuple(rules), tuple(blocks), requires_approval=True)

    for g in policy.gereserveerd:
        if g.patroon.fullmatch(aid):
            return Classification(
                aid, True, "R3", (g.id,), (), Blokkade(g.id, g.code, g.reden_nl), requires_approval=True
            )

    actie = policy.actie(aid)
    if actie is None:
        return Classification(aid, False, "R3", ("ONBEKEND",), requires_approval=True)

    rules.append(f"ACT:{aid}")
    klasse = actie.klasse
    kritieke = [h for h in herkend if h in policy.kritiek]
    kritiek = bool(kritieke)
    if kritiek and actie.klasse_kritiek:
        klasse = max_class(klasse, actie.klasse_kritiek)
        rules.append(f"KRITIEK:{kritieke[0]}")
    # Zonder Herkenning is niet bekend of de app na een stop herkenbaar blijft: dan ook R2 (dicht bij twijfel;
    # S-P2-010, R-VEILIG-4). Alleen een Herkenning die het zegt (een catalogusapp) houdt app.stop op R1.
    if (
        aid == "app.stop"
        and actie.doel == "app"
        and not (isinstance(herkend_als, Herkenning) and herkend_als.na_stop_herkenbaar)
    ):
        klasse = max_class(klasse, "R2")
        rules.append(STOP_EENRICHTING)
    for b in policy.beschermd:
        if b.app in herkend and (b.acties is None or aid in b.acties):
            rules.append(b.id)
            blocks.append(Blokkade(b.id, b.code, b.reden_nl))
    if onvolledig and actie.doel == "app":
        rules.append(DOEL_ONHERKENBAAR.id)
        blocks.append(DOEL_ONHERKENBAAR)
    if actor_type in NIET_MENSELIJK and not actie.ai_mag_voorstellen:
        rules.append("ACTOR:alleen_mens")
        blocks.append(
            Blokkade(
                "ACTOR-MENS",
                "alleen_beheerder",
                "Deze actie kan alleen een beheerder voorstellen; AI, flows en spraak niet.",
            )
        )
    if actor_type not in ACTOR_TYPES:
        blocks.append(Blokkade("ACTOR-ONBEKEND", "actor_onbekend", "Onbekende soort actor; de actie is geweigerd."))
    requires_backup = actie.requires_backup or bool(requires_backup_claim)
    if requires_backup and not actie.requires_backup:
        rules.append("BACKUP:voorstel")
    return Classification(
        aid,
        True,
        klasse,
        tuple(rules),
        tuple(blocks),
        requires_approval=class_at_least(klasse, "R2"),
        requires_backup=requires_backup,
        opslagmutatie=actie.opslagmutatie,
        uitvoerder=actie.uitvoerder,
        herkend_als=kritieke[0] if kritieke else eerste,
        kritiek=kritiek,
    )
