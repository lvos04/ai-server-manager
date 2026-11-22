"""Uitvoeren van een ondertekend ``ExecutionRequest`` (contract 1.3 §8, ADR-0030, ``docs/EXECUTION_REQUEST.md``).

De executor vertrouwt de Hub niet op zijn woord. Volgorde (elke weigering heeft een stabiele code; er is dan niets
uitgevoerd):

1. vorm, handtekening (gepinde policy-sleutel), tijden, policy-hash;
2. nonce van het verzoek (eenmalig, eigen SQLite);
3. toestand "gestopt" (na een eerdere afwijking);
4. allowlist, blokkades, doel- en parameterschema (zonder NAS);
5. schrijfsleutel aanwezig → verbinding met de vastgelegde vingerafdruk → ``core.get_methods``;
6. **eigen readback** van het doel → herkenning (naam, catalogusapp, images; niet vast te stellen wat er in een
   bestaande app draait → geweigerd; ook de image ná de actie: de nieuwe image bij ``app.update``, de bewaarde vorige
   image bij ``app.rollback``) → risicoklasse en goedkeuring opnieuw;
7. nonce van de goedkeuring (EX20), ETag van het doel (EX19), pools gezond bij een opslagmutatie (EX11);
8. methode kiezen die deze TrueNAS-versie kent (anders ``capability_unavailable``);
9. uitvoeren → readback → vergelijken met de verwachting. **Afwijking → de executor stopt** en meldt ``afwijking``;
   de Hub legt een incident vast. Ná de schrijfaanroep is elke fout die niet aantoonbaar een weigering van TrueNAS is
   een onbekende uitkomst (ook een fout bij het opvragen van de jobstatus, een onverwachte uitzondering of een
   journaal dat wegvalt): stop. De stop is duurzaam (``executor.journal``): stop en einde van de rij in één
   transactie, anders in het geheugen, en een onafgemaakte rij telt bij het starten en vóór elke uitvoering als stop.

Nooit ``custom_compose_config``, nooit een methode buiten het beleid, nooit data verwijderen
(``app.delete`` met ``remove_ix_volumes: false``).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from asm_policy import checkpoint as cpmod
from asm_policy import etag as etags
from asm_policy.canonical import canonical_sha256
from asm_policy.catalogbinding import readback_digest_afwijking
from asm_policy.engine import herken_app, recognize_all
from asm_policy.execreq import iso
from asm_policy.loader import ActieDef, Policy
from asm_policy.params import IX_APP, expected_image, validate_parameters, vault_refs, verwachte_catalogus
from asm_policy.verify import Weigering, check_decision, check_envelope
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from executor import kluis as kluismod
from executor.journal import Journal, JournalUnavailable
from executor.naslink import NasLinkOnleesbaar, NasLinkStore
from executor.truenas import NasClient, NasFout

log = logging.getLogger("executor.uitvoeren")
HERCONTROLE_WAARSCHUWING = "herstelwaarden_buiten_beleid"
CHECKPOINT_NIET_VASTGELEGD = "checkpoint_niet_vastgelegd"
_HERCONTROLE_VELDEN = "parameters.app_create.values"
GEEN: tuple[None, None] = (None, None)

NAS_MELDINGEN = {
    "truenas_onbereikbaar": (503, "TrueNAS is niet bereikbaar; er is niets uitgevoerd."),
    "truenas_timeout": (503, "TrueNAS antwoordt niet op tijd; er is niets uitgevoerd."),
    "certificaat_gewijzigd": (
        503,
        "Het TLS-certificaat van TrueNAS is anders dan het vastgelegde; de sleutel is niet verstuurd en er is niets "
        "uitgevoerd.",
    ),
    "sleutel_geweigerd": (503, "TrueNAS weigert de schrijfsleutel; er is niets uitgevoerd."),
    "truenas_geen_toegang": (503, "De schrijfsleutel heeft hiervoor geen rechten; er is niets uitgevoerd."),
    "truenas_fout": (502, "TrueNAS gaf een fout bij het lezen; er is niets uitgevoerd."),
    "methode_niet_toegestaan": (500, "Interne fout: methode buiten het beleid; er is niets uitgevoerd."),
}


@dataclass(frozen=True)
class Uitkomst:
    status: int
    body: dict[str, Any]


def fout(status: int, code: str, melding: str, details: Mapping[str, Any] | None = None) -> Uitkomst:
    return Uitkomst(
        status, {"code": code, "message": melding, "details": dict(details or {}), "trace_id": str(uuid.uuid4())}
    )


def _weiger(w: Weigering) -> Uitkomst:
    return fout(w.status, w.code, w.melding, w.details)


def _nas_fout(exc: NasFout) -> Uitkomst:
    status, melding = NAS_MELDINGEN.get(exc.code, (502, "TrueNAS gaf een fout; er is niets uitgevoerd."))
    return fout(status, exc.code, melding)


# Na de schrijfaanroep: deze codes betekenen dat de uitkomst onbekend is (geen aantoonbare weigering van TrueNAS).
ONBEKENDE_UITKOMST = frozenset({"job_timeout", "job_status_onbekend", "truenas_timeout", "truenas_onbereikbaar"})


def journaal_detail(exc: NasFout) -> str:
    """Wat het journaal over een fout van TrueNAS bewaart: alleen de stabiele code en de foutnaam (``errname`` of de
    jobstatus), nooit de vrije fouttekst; die kan waarden uit de aanroep bevatten (S-P2-030, R-VEILIG-4)."""
    return f"{exc.code} [{exc.errname}]" if exc.errname else exc.code


def hercontrole_herstelwaarden(policy: Policy, naam: str, waarden: Mapping[str, Any]) -> list[str]:
    """Hercontrole van bewaarde vorige waarden bij ``app.rollback`` met ``herstel_van`` (KLEIN-85; besluit van de
    gebruiker 2026-11-14: alleen melden). De waarden gaan door dezelfde ``validate_parameters`` als een installatie
    van de standaard Custom App; alleen de fouten in de waarden zelf tellen (en grootte of diepte). Het install-manifest
    kent de executor niet, dus de uitzonderingen daaruit (digest buiten de tag, ``host_network_reason``, GPU) tellen
    hier niet mee. Geeft de gesorteerde codes (één per fout, dubbelen mogelijk), nooit een waarde."""
    actie = policy.acties.get("app.install")
    if actie is None:  # pragma: no cover - het beleid heeft altijd app.install
        return ["hercontrole_niet_mogelijk"]
    params = {
        "app_create": {
            "app_name": naam,
            "custom_app": False,
            "catalog_app": IX_APP,
            "train": "stable",
            "version": "1.0.0",
            "values": dict(waarden),
        },
        "manifest": {"app_id": naam},
    }
    try:
        fouten = validate_parameters(policy, actie, {"app_id": naam}, params)
    except Exception:  # de hercontrole mag het terugzetten nooit tegenhouden (HARDE EIS)
        return ["hercontrole_niet_mogelijk"]
    return sorted(
        f.code
        for f in fouten
        if f.veld == "parameters" or f.veld == _HERCONTROLE_VELDEN or f.veld.startswith(f"{_HERCONTROLE_VELDEN}.")
    )


def _migratie(params: Mapping[str, Any]) -> bool:
    """Of de update volgens zijn eigen upgradecontext (§9) een migratie of een onveilige tag-terugval heeft."""
    up = params.get("upgrade")
    return isinstance(up, Mapping) and (up.get("migrations") is True or up.get("tag_only_rollback_safe") is False)


def strip_ix(values: Mapping[str, Any]) -> dict[str, Any]:
    """Waarden uit ``app.config`` zonder de velden die TrueNAS zelf toevoegt (``ix_*``)."""
    return {k: v for k, v in values.items() if not str(k).startswith("ix_")}


def _dataset_exists(tree: Any, name: str) -> bool:
    for node in tree if isinstance(tree, list) else []:
        if not isinstance(node, dict):
            continue
        if node.get("id") == name or node.get("name") == name:
            return True
        if _dataset_exists(node.get("children"), name):
            return True
    return False


def pools_gezond(pools: Any) -> tuple[bool, list[dict[str, Any]]]:
    """Alle pools ``ONLINE`` en ``healthy``. Geen pools of een onverwacht antwoord = onbekend = niet gezond (EX11).

    Positieve witte lijst per rij (R-VEILIG-1): een onleesbare, naamloze of onvolledige rij maakt alles ongezond."""
    rows = pools if isinstance(pools, list) else []
    beeld = [
        {"pool": str(p.get("name")), "status": str(p.get("status")), "healthy": p.get("healthy")}
        if isinstance(p, dict)
        else {"pool": None, "status": "onleesbaar", "healthy": None}
        for p in rows
    ]
    ok = bool(rows) and all(
        isinstance(p, dict)
        and isinstance(p.get("name"), str)
        and bool(p["name"])
        and p.get("status") == "ONLINE"
        and p.get("healthy") is True
        for p in rows
    )
    return ok, beeld


class Geweigerd(Exception):
    """Vóór de schrijfaanroep geweigerd in :meth:`Uitvoerder._voer_uit` (de dekking veranderde tussentijds)."""

    def __init__(self, uitkomst: Uitkomst) -> None:
        super().__init__(uitkomst.body.get("code"))
        self.uitkomst = uitkomst


@dataclass
class Doel:
    """Eigen readback van het doel, vlak vóór of na de uitvoering."""

    soort: str
    naam: str
    etag: str
    bestaat: bool
    hash: str
    app: dict[str, Any] | None = None
    images: list[dict[str, Any]] = field(default_factory=list)
    readback: dict[str, Any] = field(default_factory=dict)
    extra_bestaat: bool = False  # clone: bestaat de doeldataset


class Uitvoerder:
    def __init__(
        self,
        *,
        policy: Policy,
        journal: Journal,
        naslink: NasLinkStore,
        settle_seconds: float = 60.0,
        poll_seconds: float = 1.0,
        timeout: float = 15.0,
        kluis: kluismod.Kluis | None = None,
    ) -> None:
        self.policy, self.journal, self.naslink, self.kluis = policy, journal, naslink, kluis
        self.settle_seconds, self.poll_seconds, self.timeout = settle_seconds, poll_seconds, timeout
        self.write_methods = frozenset(
            m for a in policy.acties.values() if a.uitvoerder == "executor" for m in a.truenas
        )
        # Eén uitvoering tegelijk: twee goedgekeurde verzoeken op hetzelfde doel mogen elkaars readback niet kruisen.
        self._bezig = threading.Lock()

    # ------------------------------------------------------------------ readback
    def _snapshot_rijen(self, nas: NasClient, methods: frozenset[str], dataset: str) -> dict[str, str]:
        """Snapshotnaam → ``createtxg`` (leeg als TrueNAS hem niet geeft) van precies deze dataset."""
        method = next((m for m in ("pool.snapshot.query", "zfs.snapshot.query") if m in methods), None)
        if method is None:
            raise NasFout("capability_unavailable", "snapshot.query")
        rows = nas.call(method, [["dataset", "=", dataset]])
        return {
            str(r.get("name")): str(r.get("createtxg") or "")
            for r in rows or []
            if isinstance(r, dict) and str(r.get("name")).split("@", 1)[0] == dataset
        }

    def _snapshot_query(self, nas: NasClient, methods: frozenset[str], dataset: str) -> list[str]:
        return sorted(self._snapshot_rijen(nas, methods, dataset))

    def _checkpoint_leden(
        self, nas: NasClient, methods: frozenset[str], dataset: str, prop: Mapping[str, Any], txg: str
    ) -> tuple[dict[str, str], bool]:
        """Per dataset de teruggelezen eigen snapshot van deze actie. Een recursieve ZFS-snapshot ontstaat in één
        transactiegroep: alleen een kindsnapshot met dezelfde ``createtxg`` is van deze actie (een oudere met dezelfde
        naam telt niet). ``recursief`` komt uit dit teruglezen: waar als elk aangekoppeld kind zijn snapshot heeft."""
        leden = {dataset: txg}
        if not prop["parameters"].get("recursief"):
            return leden, False
        naam = str(prop["parameters"]["naam"])
        kinderen = sorted({n for _mp, n in cpmod.mounts_uit_boom(nas.call("pool.dataset.query"))
                           if n.startswith(dataset + "/")})  # fmt: skip
        for kind in kinderen:
            if self._snapshot_rijen(nas, methods, kind).get(f"{kind}@{naam}") == txg:
                leden[kind] = txg
        return leden, all(k in leden for k in kinderen)

    def _lees(self, nas: NasClient, methods: frozenset[str], actie: ActieDef, prop: Mapping[str, Any]) -> Doel:
        target = prop["target"]
        if actie.doel in ("app", "app_nieuw"):
            name = str(target["app_id"])
            apps = nas.call("app.query")
            images = [i for i in (nas.call("app.image.query") or []) if isinstance(i, dict)]
            app = next((a for a in apps or [] if isinstance(a, dict) and a.get("name") == name), None)
            tag = etags.app_etag(app, images)
            state = etags.app_state(app, images) if app is not None else {"naam": name, "afwezig": True}
            return Doel(
                actie.doel,
                name,
                tag,
                app is not None,
                tag if app is not None else canonical_sha256(state),
                app,
                images,
                state,
            )
        tree = nas.call("pool.dataset.query")
        if actie.doel == "dataset":
            ds = str(target["dataset"])
            rijen = self._snapshot_rijen(nas, methods, ds)
            snaps = sorted(rijen)
            full = f"{ds}@{prop['parameters'].get('naam')}"
            return Doel(
                "dataset",
                ds,
                etags.dataset_etag(ds),
                _dataset_exists(tree, ds),
                canonical_sha256({"dataset": ds, "snapshots": snaps}),
                readback={"snapshot": full, "aanwezig": full in snaps, "createtxg": rijen.get(full) or None},
                extra_bestaat=full in snaps,
            )
        snap = str(target["snapshot"])
        ds = snap.split("@", 1)[0]
        dst = str(prop["parameters"].get("doel_dataset"))
        dst_exists = _dataset_exists(tree, dst)
        return Doel(
            "snapshot",
            snap,
            etags.snapshot_etag(snap),
            snap in self._snapshot_query(nas, methods, ds),
            canonical_sha256({"snapshot": snap, "doel_dataset": dst, "bestaat": dst_exists}),
            readback={"dataset": dst, "aanwezig": dst_exists},
            extra_bestaat=dst_exists,
        )

    # ------------------------------------------------------------------ methode en plan
    def _plan(
        self, actie: ActieDef, prop: Mapping[str, Any], doel: Doel, methods: frozenset[str]
    ) -> tuple[str, Uitkomst | None]:
        """De TrueNAS-methode voor deze actie op deze versie, of een weigering."""
        params = prop["parameters"]
        aid = actie.action_id
        kandidaten: Iterable[str] = actie.truenas
        meta = (doel.app or {}).get("metadata")
        is_ix = isinstance(meta, dict) and meta.get("name") == IX_APP
        is_compose = bool((doel.app or {}).get("custom_app"))
        wil_ix = "image" in params or "herstel_van" in params
        if aid == "app.update":
            kandidaten = ("app.update",) if "image" in params else ("app.upgrade",)
        elif aid == "app.rollback":
            kandidaten = ("app.update",) if "herstel_van" in params else ("app.rollback",)
        if aid in ("app.update", "app.rollback"):
            if is_compose:
                return "", fout(
                    409,
                    "doel_past_niet",
                    "Deze app is met een eigen compose-configuratie geïnstalleerd; die wijzigt de executor nooit.",
                )
            if wil_ix != is_ix:
                return "", fout(
                    409,
                    "doel_past_niet",
                    "Deze app is geen standaard Custom App (ix-app); een image wijzigen kan alleen daar."
                    if wil_ix
                    else "Deze app is een Custom App; een catalogusversie kiezen kan alleen bij een catalogusapp.",
                )
        if aid == "app.install" and vault_refs(params) and "catalog_binding" not in params:
            # Zonder binding geen kluisplekken; met binding toetst catalogbinding ze tegen de eigen regel (§8.3).
            return "", fout(
                501,
                "capability_unavailable",
                "Geheimen uit de kluis invullen bij een installatie is in deze versie niet beschikbaar; er is niets "
                "geïnstalleerd.",
                {"reden": "vault_verwijzingen"},
            )
        nodig = [m for m in kandidaten if m in methods]
        if not nodig or (aid in ("app.update", "app.rollback") and "app.config" not in methods and wil_ix):
            return "", fout(
                501,
                "capability_unavailable",
                "Deze TrueNAS-versie kent de methode voor deze actie niet; er is niets uitgevoerd.",
                {"methoden": list(kandidaten)},
            )
        return nodig[0], None

    # ------------------------------------------------------------------ checkpoint en herkomst (S-P2-050f)
    def _checkpoint_gate(
        self, nas: NasClient, methods: frozenset[str], app: str, cp_id: str, werklast: Any, recept: Any
    ) -> tuple[Uitkomst | None, Callable[[], Any] | None, list[str] | None]:
        """Het gebonden checkpoint is van een voltooide eigen snapshotactie van deze executor, vers, en heeft voor elke
        dataset met data van de app (huidige configuratie, werklast, datasetboom en de te herstellen waarden) een eigen
        snapshot met dezelfde ``createtxg``. Geeft ook de hercontrole voor vlak vóór de schrijfaanroep en de datasets
        van de huidige configuratie (die van het recept dat deze actie bewaart; de Hub toetst ze bij terugzetten)."""

        def weiger(code: str, reden: str, **details: Any) -> Uitkomst:
            return fout(
                409,
                code,
                f"{reden} Er is niets bijgewerkt of teruggezet; maak eerst een nieuwe snapshot van de appdata en keur "
                "opnieuw goed.",
                {"checkpoint_id": cp_id or None, **details},
            )

        cp = self.journal.checkpoint(cp_id) if cp_id else None
        if cp is None:
            reden = "Deze executor heeft dit checkpoint niet zelf gemaakt en vastgelegd."
            return weiger("checkpoint_ontbreekt", reden), *GEEN
        leeftijd = int(time.time()) - int(cp["created_at"])
        if not -300 <= leeftijd <= cpmod.CHECKPOINT_MAX_SECONDEN or self.journal.gewijzigd_na(app, int(cp["grens"])):
            return weiger(
                "checkpoint_verlopen",
                "Het checkpoint is ouder dan een uur, of de app is daarna al bijgewerkt of teruggezet.",
                leeftijd_seconden=leeftijd,
            ), *GEEN
        naam = str(cp["snapshot"]).split("@", 1)[-1]
        # De gebonden basissnapshot telt altijd mee, ook als de app geen datasets heeft (R-HARDE-EIS-2).
        leden: Mapping[str, str] = {**cp["leden"], str(cp["dataset"]): str(cp["createtxg"])}

        eigen: list[str] | None = None

        def dekking() -> tuple[Uitkomst | None, str, Any]:
            nonlocal eigen
            try:
                config, boom = nas.call("app.config", app), nas.call("pool.dataset.query")
                nodig = cpmod.app_datasets(config, boom, app, werklast, ook=recept)
                eigen = cpmod.app_datasets(config, boom, app, werklast)
                if nodig is None or not set(nodig) <= set(leden):
                    return (
                        weiger(
                            "checkpoint_dekt_niet",
                            "Het checkpoint heeft niet voor elke dataset met data van deze app een eigen snapshot "
                            "(of de opslag is niet vast te stellen).",
                            datasets=nodig,
                        ),
                        "",
                        config,
                    )
                te_lezen = sorted({*nodig, str(cp["dataset"])})
                gelezen = {d: self._snapshot_rijen(nas, methods, d).get(f"{d}@{naam}") for d in te_lezen}
            except NasFout as exc:
                return _nas_fout(exc), "", None
            afwijkend = sorted(d for d in te_lezen if not leden[d] or gelezen[d] != leden[d])
            if afwijkend:
                return (
                    weiger(
                        "checkpoint_afwijkend",
                        "Een snapshot van het checkpoint bestaat niet meer of is een andere (createtxg wijkt af).",
                        datasets=afwijkend,
                    ),
                    "",
                    config,
                )
            return None, canonical_sha256({"config": config, "nodig": nodig, "snapshots": gelezen}), config

        eerst, gecontroleerd, _config = dekking()
        if eerst is not None:
            return eerst, *GEEN

        def hercontrole() -> Any:
            # shortcut: TrueNAS biedt via deze adapter geen snapshot-hold en geen voorwaardelijke schrijfaanroep; de
            # executor leest opslag en snapshots vlak vóór de schrijfaanroep opnieuw en weigert bij elk verschil. Een
            # wijziging binnen dat laatste venster blijft mogelijk; upgraden zodra hold of een ETag-voorwaarde bestaat.
            nu, staat, config = dekking()
            if nu is None and staat != gecontroleerd:
                nu = fout(
                    409,
                    "doel_gewijzigd",
                    "De opslag of de snapshots van de app zijn veranderd sinds de controle; er is niets bijgewerkt of "
                    "teruggezet. Maak een nieuwe preview en keur opnieuw goed.",
                )
            if nu is not None:
                raise Geweigerd(nu)
            return config

        return None, hercontrole, eigen

    def _vertrek(self, app: str, request_id: str, h: Mapping[str, Any]) -> set[str]:
        """Wat er vóór die eigen wijziging draaide: de vastgelegde ``van``, de catalogusversie en de image uit het eigen
        recept van die wijziging (een registratie van vóór ``van``, R-HARDE-EIS-5)."""
        ids = cpmod.normaliseer(h.get("van") or [])
        if v := h.get("van_versie"):
            ids.add(f"versie:{v}")
        recept = self.journal.load_values(request_id)
        image = recept[1].get("image") if recept is not None and recept[0] == app else None
        if isinstance(image, Mapping):
            ids |= cpmod.doel_identiteiten(image)
        return ids

    def _herkomst_gate(
        self, params: Mapping[str, Any], app: str, aid: str, doel_ids: set[str]
    ) -> tuple[str | None, Uitkomst | None]:
        """EX15 met optie 3 (ADR-0032 besluit 8): de herkomst komt uit het eigen journaal, nooit uit het verzoek.
        Geeft de vaste melding (``oud`` of ``buiten_keten``) of een weigering. Bij elke bijwerking en terugzetting: een
        doel (image, digest of catalogusversie) dat vóór een vastgelegde migratie draaide, vereist databaseherstel,
        ongeacht de actienaam (R-HARDE-EIS-5); een onvolledige historie is onbekend (R-HARDE-EIS-6)."""
        try:
            oud: set[tuple[str, str, int]] | None = self.journal.oud_vastlegging()
        except JournalUnavailable:
            oud = None  # verlies raakt alleen recepten zonder eigen herkomst
        onbekend = fout(
            409,
            "herkomst_onbekend",
            "De executor kan de herkomst of de migratiegeschiedenis van deze app niet vaststellen (geen eigen "
            "vastlegging, onleesbaar, onvolledig of tegenstrijdig); er is niets bijgewerkt of teruggezet.",
            {"herstel_van": params.get("herstel_van")},
        )
        try:
            rijen = self.journal.herkomsten(app)
        except JournalUnavailable:
            return None, onbekend  # een onleesbare eigen herkomst wordt nooit alsnog "oud"

        def migratie(vanaf: list[tuple[int, str, dict[str, Any]]]) -> Uitkomst | None:
            if not any(h.get("migratie") for _i, _r, h in vanaf):
                return None
            return fout(
                409,
                "database_herstel_vereist",
                "Na deze versie liep een databasemigratie (of de tag-terugval is onveilig): alleen de image "
                "terugzetten kan de data beschadigen. Terugzetten kan alleen samen met de database, uit het "
                "checkpoint van die update, via de eigenaar; er is niets teruggezet.",
                {"checkpoints": sorted({str(h.get("checkpoint_id")) for _i, _r, h in vanaf if h.get("migratie")})},
            )

        try:
            historie = [(bool(h.get("migratie")), self._vertrek(app, rid, h)) for _n, rid, h in rijen]
        except JournalUnavailable:
            return None, onbekend
        terug = cpmod.terug_voor_migratie(historie, doel_ids)
        if terug is None:
            return None, onbekend  # de vertrekversie van een wijziging tot en met de migratie is niet te herleiden
        if terug:
            return None, migratie(rijen)
        if aid != "app.rollback":
            return None, None
        if "herstel_van" not in params:
            # Catalogusrollback: vanaf de laatste update die van deze versie vertrok (of alles als die er niet is).
            doel = str(params.get("catalog_version"))
            idx = max((i for i, (_n, _r, h) in enumerate(rijen) if h.get("van_versie") == doel), default=0)
            return None, migratie(rijen[idx:])
        r = str(params["herstel_van"])
        eigen = next((i for i, (_n, rid, _h) in enumerate(rijen) if rid == r), None)
        tijd = self.journal.recept_tijd(r)
        in_oud = oud is not None and tijd is not None and (r, tijd[0], tijd[1]) in oud
        if (eigen is None) == (not in_oud):  # geen van beide, of tegenstrijdig allebei
            return None, onbekend
        return ("buiten_keten" if eigen is not None else "oud"), migratie(rijen[eigen:] if eigen is not None else rijen)

    def _voer_uit(
        self,
        nas: NasClient,
        methode: str,
        actie: ActieDef,
        prop: Mapping[str, Any],
        doel: Doel,
        request_id: str,
        gevuld: Mapping[str, Any] | None = None,
        herkomst: Mapping[str, Any] | None = None,
        hercontrole_dekking: Callable[[], Any] | None = None,
    ) -> None:
        params, name = prop["parameters"], doel.naam
        t = float(actie.timeout_seconden)
        aid = actie.action_id
        if aid in ("app.restart", "app.stop", "app.start"):
            nas.job(methode, name, timeout=t, poll=self.poll_seconds)
        elif aid == "app.install":
            ac = params["app_create"]
            # Altijd expliciet opgebouwd: custom_app is false en er gaat nooit een compose-veld mee (EX47).
            body = {
                "app_name": name,
                "custom_app": False,
                "catalog_app": ac["catalog_app"],
                "train": ac["train"],
                "version": ac["version"],
                # De ingevulde tijdelijke kopie (§8.3) gaat alleen hierheen, nooit naar log of journaal.
                "values": ac["values"] if gevuld is None else gevuld,
            }
            nas.job(methode, body, timeout=t, poll=self.poll_seconds)
        elif aid == "app.uninstall":
            # Container-only: datasets, ix-volumes en images blijven (B01-003; nooit data verwijderen).
            nas.job(
                methode, name, {"remove_images": False, "remove_ix_volumes": False}, timeout=t, poll=self.poll_seconds
            )
        elif aid in ("app.update", "app.rollback") and hercontrole_dekking is None:
            raise Geweigerd(fout(409, "checkpoint_ontbreekt", "Geen gecontroleerd checkpoint; er is niets uitgevoerd."))
        elif aid in ("app.update", "app.rollback") and methode == "app.update" and hercontrole_dekking:
            # Vlak vóór bewaren en schrijfaanroep: dezelfde opslag en snapshots als gecontroleerd (R-HARDE-EIS-3).
            vorige = hercontrole_dekking()
            vorige = strip_ix(vorige) if isinstance(vorige, dict) else {}
            if aid == "app.update":
                oud_image = vorige.get("image")
                image = dict(oud_image) if isinstance(oud_image, dict) else {}
                image.update(repository=params["image"]["repository"], tag=params["image"]["tag"])
                if "pull_policy" in params["image"]:
                    image["pull_policy"] = params["image"]["pull_policy"]
                values: dict[str, Any] = {"image": image}
            else:
                bewaard = self.journal.load_values(str(params["herstel_van"]))
                values = bewaard[1] if bewaard else {}
            # De huidige waarden eerst (versleuteld) bewaren: daarmee kan deze wijziging worden teruggezet.
            self.journal.save_values(request_id, name, vorige, dict(herkomst) if herkomst else None)
            nas.job(methode, name, {"values": values}, timeout=t, poll=self.poll_seconds)
        elif aid == "app.update" and hercontrole_dekking:
            hercontrole_dekking()
            if herkomst:  # zonder recept: de herkomst apart, ook vóór de schrijfaanroep
                self.journal.leg_herkomst_vast(request_id, name, dict(herkomst))
            nas.job(methode, name, {"app_version": params["catalog_version"]}, timeout=t, poll=self.poll_seconds)
        elif aid == "app.rollback" and hercontrole_dekking:
            hercontrole_dekking()
            if herkomst:
                self.journal.leg_herkomst_vast(request_id, name, dict(herkomst))
            nas.job(
                methode,
                name,
                {"app_version": params["catalog_version"], "rollback_snapshot": False},
                timeout=t,
                poll=self.poll_seconds,
            )
        elif aid == "zfs.snapshot.create":
            nas.call(
                methode,
                {"dataset": name, "name": params["naam"], "recursive": bool(params.get("recursief", False))},
                timeout=t,
            )
        elif aid == "zfs.snapshot.clone_to_sandbox":
            nas.call(methode, {"snapshot": name, "dataset_dst": params["doel_dataset"]}, timeout=t)
        else:  # pragma: no cover - een actie in het beleid zonder uitvoering hier
            raise NasFout("methode_niet_toegestaan", aid)

    # ------------------------------------------------------------------ vergelijken
    def _afwijkingen(
        self, actie: ActieDef, prop: Mapping[str, Any], na: Doel, verwachte_image: Mapping[str, Any] | None
    ) -> tuple[list[dict[str, Any]], list[str]]:
        afw: list[dict[str, Any]] = []
        waarsch: list[str] = []
        verwacht = actie.verwacht
        if na.soort in ("app", "app_nieuw"):
            if verwacht.get("afwezig"):
                if na.bestaat:
                    afw.append({"code": "nog_aanwezig", "verwacht": "afwezig", "gevonden": "aanwezig"})
                return afw, waarsch
            if not na.bestaat or na.app is None:
                return [{"code": "niet_aanwezig", "verwacht": "aanwezig", "gevonden": "afwezig"}], waarsch
            staat = verwacht.get("staat")
            if staat and na.app.get("state") != staat:
                afw.append({"code": "staat_verschilt", "verwacht": staat, "gevonden": str(na.app.get("state"))})
            if (
                "catalog_version" in prop["parameters"]
                and na.app.get("version") != prop["parameters"]["catalog_version"]
            ):
                afw.append(
                    {
                        "code": "versie_verschilt",
                        "verwacht": prop["parameters"]["catalog_version"],
                        "gevonden": str(na.app.get("version")),
                    }
                )
            if verwachte_image and verwachte_image.get("repository"):
                repo, tag = str(verwachte_image["repository"]), str(verwachte_image.get("tag") or "")
                versie, digest = str(verwachte_image.get("versie") or ""), verwachte_image.get("digest")
                if f"{repo}:{tag}" not in etags.app_images(na.app):
                    afw.append(
                        {"code": "image_verschilt", "verwacht": f"{repo}:{tag}", "gevonden": etags.app_images(na.app)}
                    )
                elif digest:
                    rijen = [
                        i
                        for i in na.images
                        if {f"{repo}:{versie}", f"{repo}:{tag}"} & {str(x) for x in i.get("repo_tags") or []}
                    ]
                    gevonden = sorted({str(d) for i in rijen for d in i.get("repo_digests") or []})
                    if rijen and f"{repo}@{digest}" not in gevonden:
                        afw.append({"code": "digest_verschilt", "verwacht": f"{repo}@{digest}", "gevonden": gevonden})
                    elif not rijen and "@sha256:" not in tag:
                        waarsch.append("digest_niet_bevestigd")
            # Met een catalogusbinding (§8.1) telt alleen een digest uit app.image.query die in de release staat.
            binding = readback_digest_afwijking(prop["parameters"], etags.app_images(na.app), na.images)
            if binding is not None:
                afw.append(binding)
            return afw, waarsch
        if not na.extra_bestaat:
            afw.append({"code": "niet_aanwezig", "verwacht": "aanwezig", "gevonden": "afwezig"})
        return afw, waarsch

    def _settle(
        self, nas: NasClient, methods: frozenset[str], actie: ActieDef, prop: Mapping[str, Any], verwachte_image: Any
    ) -> tuple[Doel, list[dict[str, Any]], list[str]]:
        """Readback; een app die nog onderweg is (DEPLOYING, STOPPING) krijgt ``settle_seconds`` om aan te komen."""
        deadline = time.monotonic() + self.settle_seconds
        while True:
            na = self._lees(nas, methods, actie, prop)
            afw, waarsch = self._afwijkingen(actie, prop, na, verwachte_image)
            if not afw or time.monotonic() >= deadline:
                return na, afw, waarsch
            time.sleep(self.poll_seconds)

    # ------------------------------------------------------------------ hoofdlijn
    def run(self, request: Any, keys: Iterable[Ed25519PublicKey], *, now: datetime | None = None) -> Uitkomst:
        now = now or datetime.now(UTC)
        policy = self.policy
        if (w := check_envelope(policy, request, list(keys), now=now)) is not None:
            return _weiger(w)
        if not self._bezig.acquire(blocking=False):
            # De nonce is nog niet verbruikt: hetzelfde verzoek mag straks opnieuw worden aangeboden.
            return fout(
                409,
                "executor_bezet",
                "De executor voert al een actie uit; er is niets uitgevoerd. Probeer het zo opnieuw.",
            )
        try:
            return self._beoordeel(request, now)
        except JournalUnavailable:
            return fout(
                503,
                "journaal_niet_beschikbaar",
                "Het journaal van de executor is niet beschikbaar; er is niets uitgevoerd. Controleer de opslag in "
                "/appdata.",
            )
        finally:
            self._bezig.release()

    def _beoordeel(self, request: Mapping[str, Any], now: datetime) -> Uitkomst:
        policy = self.policy
        prop, approval, nonce = request["proposal"], request.get("approval"), str(request["nonce"])
        request_id = str(approval["request_id"]) if isinstance(approval, Mapping) else str(prop["idempotency_key"])
        if self.journal.bezet():
            # Een andere instantie in dit proces voert op dit journaal nog een actie uit (de nonce blijft bruikbaar).
            return fout(
                409,
                "executor_bezet",
                "De executor voert al een actie uit; er is niets uitgevoerd. Probeer het zo opnieuw.",
            )
        if not self.journal.claim_request_nonce(nonce):
            return fout(
                409, "nonce_al_gebruikt", "Dit uitvoeringsverzoek is al eens aangeboden; er is niets uitgevoerd."
            )
        # Ook een onafgemaakte uitvoering (rij "gestart" zonder einde) of een afwijking zonder vrijgave telt als stop
        # (Journal.stopped, R-VEILIG-1 en R-VEILIG-2).
        if (gestopt := self.journal.stopped()) is not None:
            return fout(
                409,
                "executor_gestopt",
                "De executor is gestopt na een afwijking en voert niets uit tot een beheerder hem op de "
                "executorpagina vrijgeeft met de TrueNAS-schrijfsleutel.",
                {"sinds": gestopt.get("at"), "reden": gestopt.get("code"), "request_id": gestopt.get("request_id")},
            )
        # Zonder NAS: herkenning alleen op de naam uit het voorstel. Wat hier al geweigerd wordt (bv. een app die
        # "emby" heet), bereikt TrueNAS niet eens; de herkenning op de image uit de eigen readback volgt hierna en
        # kan alleen strenger zijn.
        doelnaam = prop["target"].get("app_id") if isinstance(prop.get("target"), Mapping) else None
        op_naam = recognize_all(policy, doelnaam if isinstance(doelnaam, str) else None)
        actie, _eigen, w = check_decision(policy, request, now=now, herkend_als=op_naam, uitvoerder="executor")
        if w is not None and w.code in (
            "actie_geweigerd",
            "capability_unavailable",
            "actie_niet_toegestaan",
            "parameters_ongeldig",
        ):
            return _weiger(w)
        if actie is None:  # pragma: no cover - check_decision geeft dan altijd een weigering
            return fout(403, "actie_niet_toegestaan", "Deze actie staat niet op de allowlist.")
        params = prop["parameters"]
        if (actie.action_id == "app.update" and "image" in params) or (
            actie.action_id == "app.rollback" and "herstel_van" in params
        ):
            try:
                gemarkeerd = self.journal.kluis_gemarkeerd(str(doelnaam))
            except JournalUnavailable:
                gemarkeerd = True  # een onleesbare lijst weigert elke actie over dit pad (§8.3)
            if gemarkeerd:
                return fout(
                    409,
                    "kluisplekken_recept_ontbreekt",
                    "Deze app kreeg bij de installatie geheimen uit de kluis. Bijwerken of terugzetten via de waarden "
                    "kan pas met het recept met alleen verwijzingen; er is niets uitgevoerd.",
                )
        link = self.naslink.read()
        if link.get("_onleesbaar"):
            # Onleesbare sleutelopslag (rechten, eigenaar, symlink, schema): dezelfde code als een sleutel die niet te
            # openen is (ADR-0030 besluit 13, docs/EXECUTION_REQUEST.md), nooit "niet ingesteld" (R-TECH-3).
            return fout(
                503,
                "schrijfsleutel_onleesbaar",
                "De opgeslagen schrijfsleutel is onleesbaar; er is niets uitgevoerd.",
            )
        if link.get("key") is None:
            return fout(
                501,
                "capability_unavailable",
                "De TrueNAS-schrijfsleutel is niet ingesteld op de executorpagina; er is niets uitgevoerd.",
                {"reden": "schrijfsleutel_ontbreekt"},
            )
        try:
            api_key = self.naslink.api_key()
        except NasLinkOnleesbaar:
            return fout(
                503,
                "schrijfsleutel_onleesbaar",
                "De opgeslagen schrijfsleutel is onleesbaar; er is niets uitgevoerd.",
            )
        return self._met_nas(request, actie, request_id, nonce, link, api_key, now)

    def _met_nas(
        self,
        request: Mapping[str, Any],
        actie: ActieDef,
        request_id: str,
        nonce: str,
        link: Mapping[str, Any],
        api_key: str,
        now: datetime,
    ) -> Uitkomst:
        policy, prop, approval = self.policy, request["proposal"], request.get("approval")
        try:
            nas = NasClient(
                str(link["host"]),
                int(link["port"]),
                str(link["fingerprint"]),
                allowed=self.write_methods,
                timeout=self.timeout,
            )
            nas.open()
        except NasFout as exc:
            return _nas_fout(exc)
        try:
            try:
                nas.login(api_key)
                methods = nas.methods()
                doel = self._lees(nas, methods, actie, prop)
            except NasFout as exc:
                if exc.code == "capability_unavailable":
                    return fout(
                        501, "capability_unavailable", "Deze TrueNAS-versie kent de leesmethode voor dit doel niet."
                    )
                return _nas_fout(exc)
            verwachte_image = expected_image(prop["parameters"])
            # Ook de image ná de actie telt voor de herkenning (S-P2-010, R-VEILIG-2): de nieuwe image bij app.update,
            # de bewaarde vorige image bij app.rollback. Een herkenning maakt alleen strenger.
            na_actie = [str((verwachte_image or {}).get("repository") or "")]
            bewaard = (
                self.journal.load_values(str(prop["parameters"]["herstel_van"]))
                if actie.action_id == "app.rollback" and "herstel_van" in prop["parameters"]
                else None
            )
            vorig_image = bewaard[1].get("image") if bewaard is not None and bewaard[0] == doel.naam else None
            if isinstance(vorig_image, dict):
                na_actie.append(str(vorig_image.get("repository") or ""))
            herkend = (
                herken_app(
                    policy,
                    doel.naam,
                    doel.app,
                    na_actie,
                    catalogus=verwachte_catalogus(prop["parameters"]),
                )
                if doel.soort.startswith("app")
                else None
            )
            _a, eigen, w = check_decision(policy, request, now=now, herkend_als=herkend, uitvoerder="executor")
            if w is not None or eigen is None:
                return _weiger(w) if w else fout(403, "actie_niet_toegestaan", "Deze actie staat niet op de allowlist.")
            if isinstance(approval, Mapping) and self.journal.approval_used(str(approval["one_time_nonce"])):
                return fout(409, "goedkeuring_al_gebruikt", "Deze goedkeuring is al eens gebruikt; keur opnieuw goed.")
            # Precondities uit de eigen readback (EX19): het doel is nog wat de beheerder zag.
            if doel.soort == "app_nieuw":
                if doel.bestaat:
                    return fout(
                        409, "doel_gewijzigd", "Er bestaat al een app met deze naam; er is niets geïnstalleerd."
                    )
            elif not doel.bestaat:
                return fout(409, "doel_bestaat_niet", "Het doel bestaat niet (meer); er is niets uitgevoerd.")
            if doel.etag != prop["expected_version"]:
                return fout(
                    409,
                    "doel_gewijzigd",
                    "Het doel is veranderd sinds de preview; maak een nieuwe preview en keur opnieuw goed.",
                    {"verwacht": prop["expected_version"], "gevonden": doel.etag},
                )
            if doel.soort in ("dataset", "snapshot") and doel.extra_bestaat:
                return fout(
                    409, "doel_bestaat_al", "De snapshot of sandbox-dataset bestaat al; er is niets uitgevoerd."
                )
            if eigen.opslagmutatie:
                try:
                    ok, beeld = pools_gezond(nas.call("pool.query"))
                except NasFout as exc:
                    return _nas_fout(exc)
                if not ok:
                    return fout(
                        409,
                        "pool_niet_gezond",
                        "Een pool is niet gezond of de toestand is onbekend; opslagmutaties zijn geblokkeerd (EX11).",
                        {"pools": beeld},
                    )
            methode, geweigerd = self._plan(actie, prop, doel, methods)
            if geweigerd is not None:
                return geweigerd
            hercontrole: dict[str, Any] | None = None
            if actie.action_id == "app.rollback" and "herstel_van" in prop["parameters"]:
                if bewaard is None or bewaard[0] != doel.naam:
                    return fout(
                        409,
                        "herstelpunt_onbekend",
                        "De executor heeft geen vorige waarden van deze app bij die wijziging; er is niets teruggezet.",
                    )
                # Hercontrole (KLEIN-85): alleen melden; het terugzetten gaat altijd door met dezelfde waarden.
                codes = hercontrole_herstelwaarden(policy, doel.naam, bewaard[1])
                if codes:
                    hercontrole = {"overtredingen": len(codes), "codes": sorted(set(codes))}
                oud = bewaard[1].get("image") if isinstance(bewaard[1].get("image"), dict) else None
                if oud:
                    versie, _s, in_tag = str(oud.get("tag") or "").partition("@")
                    verwachte_image = {
                        "repository": str(oud.get("repository") or ""),
                        "tag": str(oud.get("tag") or ""),
                        "versie": versie,
                        "digest": in_tag or None,
                    }
            herkomst: dict[str, Any] | None = None
            gemeld: str | None = None
            hercontrole_dekking: Callable[[], Any] | None = None
            if actie.action_id in ("app.update", "app.rollback"):
                # Pre-update-gate (contract §8, S-P2-050f): fail-closed vóór elke schrijfaanroep. Bij terugzetten telt
                # ook de opslag in de bewaarde waarden die geschreven gaan worden (R-HARDE-EIS-4).
                cp_id = str(approval.get("backup_checkpoint_id") or "") if isinstance(approval, Mapping) else ""
                werklast = (doel.app or {}).get("active_workloads")
                recept = bewaard[1] if bewaard is not None else None
                cp_fout, hercontrole_dekking, herstel_datasets = self._checkpoint_gate(
                    nas, methods, doel.naam, cp_id, werklast, recept
                )
                if cp_fout is not None:
                    return cp_fout
                doel_ids = cpmod.doel_identiteiten(verwachte_image, prop["parameters"].get("catalog_version"))
                gemeld, ex15 = self._herkomst_gate(prop["parameters"], doel.naam, actie.action_id, doel_ids)
                if ex15 is not None:
                    return ex15
                if gemeld is not None:
                    log.warning("herkomst_%s: terugzetten gaat door met melding: request_id=%s", gemeld, request_id)
                herkomst = {
                    "herkomst": "buiten_keten",
                    "soort": actie.action_id,
                    "migratie": _migratie(prop["parameters"]),
                    "van_versie": str(doel.readback.get("versie") or ""),
                    "van": sorted(cpmod.identiteiten(doel.readback)),
                    "checkpoint_id": cp_id,
                    "herstel_datasets": herstel_datasets,
                }
            if isinstance(approval, Mapping) and not self.journal.claim_approval_nonce(
                str(approval["one_time_nonce"]), str(approval["approval_id"])
            ):
                return fout(409, "goedkeuring_al_gebruikt", "Deze goedkeuring is al eens gebruikt; keur opnieuw goed.")
            gevuld: dict[str, Any] | None = None
            regel = kluismod.regel_van(policy, prop["parameters"]) if actie.action_id == "app.install" else None
            if regel is not None:
                try:
                    if self.kluis is None:
                        melding = "Deze executor kan geen geheimen ophalen; er is niets geïnstalleerd."
                        raise kluismod.KluisFout(503, "kluis_afgifte_mislukt", melding)
                    gevuld = self.kluis.vul(regel, request)
                except kluismod.KluisFout as exc:
                    return fout(exc.status, exc.code, exc.melding)
                # Vóór de schrijfaanroep: ook een onderbroken installatie blijft gemarkeerd (fail-closed).
                self.journal.markeer_kluis(
                    request_id,
                    doel.naam,
                    str(link["fingerprint"]),
                    kluismod.markering(regel, prop["parameters"]["catalog_binding"]),
                )
            # Lopend vanaf vóór de rij "gestart" tot na het einde ervan: zolang telt de rij niet als onafgemaakt.
            with self.journal.lopend(nonce):
                self.journal.begin(
                    request_id=request_id,
                    nonce=nonce,
                    action_id=actie.action_id,
                    target=dict(prop["target"]),
                    methode=methode,
                    before_hash=doel.hash,
                )
                if hercontrole is not None:
                    log.warning(
                        "%s: terugzetten gaat door met de bewaarde waarden (alleen gemeld): request_id=%s "
                        "herstel_van=%s overtredingen=%d codes=%s",
                        HERCONTROLE_WAARSCHUWING,
                        request_id,
                        prop["parameters"]["herstel_van"],
                        hercontrole["overtredingen"],
                        ",".join(hercontrole["codes"]),
                    )
                return self._uitvoeren_en_teruglezen(
                    nas, methods, methode, actie, prop, doel, request_id, nonce, verwachte_image, hercontrole, gevuld,
                    herkomst, gemeld, hercontrole_dekking,
                )  # fmt: skip
        finally:
            nas.close()

    def _stop(
        self, request_id: str, nonce: str, actie: ActieDef, methode: str, doel: Doel, na: Doel | None, code: str,
        afwijkingen: list[dict[str, Any]],
    ) -> Uitkomst:  # fmt: skip
        """Stop na een afwijking of onbekende uitkomst. Stop en einde van de rij in één transactie (de stop eerst);
        lukt dat niet, dan blijft de stop in het geheugen tot het journaal weer werkt (R-VEILIG-1). Nooit een
        uitzondering: ná de schrijfaanroep is dit altijd het antwoord."""
        after = na.hash if na else None
        # Een journaal dat wegviel ná de aanroep: de uitkomst is niet vastgelegd, dus onbekend. De stop krijgt die code
        # (de statuspagina toont dan de vrijgave-uitleg; "journaal_niet_beschikbaar" betekent daar "nu onleesbaar").
        stopcode = "uitkomst_onbekend" if code == "journaal_niet_beschikbaar" else code
        reden = {
            "code": stopcode,
            "request_id": request_id,
            "action_id": actie.action_id,
            "at": iso(datetime.now(UTC)),
        }
        try:
            self.journal.stop(reden, nonce=nonce, after_hash=after, detail=code)
        except JournalUnavailable:
            self.journal.stop_in_geheugen(reden, nonce=nonce, after_hash=after, detail=code)
        if code == "journaal_niet_beschikbaar":
            melding = (
                "De actie is naar TrueNAS gestuurd, maar het journaal van de executor is niet beschikbaar: de uitkomst "
                "is niet vastgelegd. De executor is gestopt en voert niets meer uit tot een beheerder hem vrijgeeft."
            )
        else:
            melding = (
                "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt en "
                "voert niets meer uit tot een beheerder hem vrijgeeft."
            )
        return fout(
            409,
            "afwijking",
            melding,
            {
                "reden": code,
                "afwijkingen": afwijkingen,
                "request_id": request_id,
                "action_id": actie.action_id,
                "methode": methode,
                "before_hash": doel.hash,
                "after_hash": after,
                "gestopt": True,
            },
        )

    def _uitvoeren_en_teruglezen(
        self,
        nas: NasClient,
        methods: frozenset[str],
        methode: str,
        actie: ActieDef,
        prop: Mapping[str, Any],
        doel: Doel,
        request_id: str,
        nonce: str,
        verwachte_image: Mapping[str, Any] | None,
        hercontrole: Mapping[str, Any] | None = None,
        gevuld: Mapping[str, Any] | None = None,
        herkomst: Mapping[str, Any] | None = None,
        gemeld: str | None = None,
        hercontrole_dekking: Callable[[], Any] | None = None,
    ) -> Uitkomst:
        mislukt: NasFout | None = None
        try:
            self._voer_uit(nas, methode, actie, prop, doel, request_id, gevuld, herkomst, hercontrole_dekking)
        except NasFout as exc:
            mislukt = exc
        except Geweigerd as g:
            # Vóór de schrijfaanroep (alleen leesaanroepen verstuurd): niets uitgevoerd, de rij krijgt "mislukt".
            code = str(g.uitkomst.body.get("code"))
            try:
                self.journal.finish(nonce, status="mislukt", after_hash=doel.hash, detail=code)
            except JournalUnavailable:
                self.journal.einde_in_geheugen(nonce, status="mislukt", after_hash=doel.hash, detail=code)
            log.warning("vlak vóór de schrijfaanroep geweigerd: request_id=%s code=%s", request_id, code)
            return g.uitkomst
        except Exception as exc:
            if not nas.schrijfaanroep_verstuurd:
                # Vóór de schrijfaanroep (bv. het journaal of vault.key bij het bewaren van de vorige waarden): er is
                # aantoonbaar niets naar TrueNAS gestuurd. De rij krijgt het einde "mislukt", zodat hij niet als
                # onafgemaakte uitvoering telt; werkt het journaal nu niet, dan zodra het terug is (R-VEILIG-H2).
                try:
                    self.journal.finish(nonce, status="mislukt", after_hash=doel.hash, detail=type(exc).__name__)
                except JournalUnavailable:
                    self.journal.einde_in_geheugen(
                        nonce, status="mislukt", after_hash=doel.hash, detail=type(exc).__name__
                    )
                raise
            # Ná de schrijfaanroep is elke onverwachte fout een onbekende uitkomst (R-VEILIG-2).
            log.warning("uitkomst onbekend na de schrijfaanroep: request_id=%s fout=%s", request_id, type(exc).__name__)
            return self._stop(request_id, nonce, actie, methode, doel, None, "uitkomst_onbekend", [])
        try:
            return self._teruglezen(
                nas, methods, methode, actie, prop, doel, request_id, nonce, verwachte_image, mislukt, hercontrole,
                gemeld, herkomst,
            )  # fmt: skip
        except JournalUnavailable:
            # Na de aanroep bij TrueNAS kan "er is niets uitgevoerd" niet meer worden beloofd: stop (in het geheugen
            # zolang het journaal niet werkt).
            return self._stop(request_id, nonce, actie, methode, doel, None, "journaal_niet_beschikbaar", [])
        except Exception as exc:
            log.warning("uitkomst onbekend na de schrijfaanroep: request_id=%s fout=%s", request_id, type(exc).__name__)
            return self._stop(request_id, nonce, actie, methode, doel, None, "uitkomst_onbekend", [])

    def _teruglezen(
        self,
        nas: NasClient,
        methods: frozenset[str],
        methode: str,
        actie: ActieDef,
        prop: Mapping[str, Any],
        doel: Doel,
        request_id: str,
        nonce: str,
        verwachte_image: Mapping[str, Any] | None,
        mislukt: NasFout | None,
        hercontrole: Mapping[str, Any] | None = None,
        gemeld: str | None = None,
        herkomst: Mapping[str, Any] | None = None,
    ) -> Uitkomst:
        try:
            if mislukt is not None:
                na = self._lees(nas, methods, actie, prop)
                afw: list[dict[str, Any]] = []
                waarsch: list[str] = []
            else:
                na, afw, waarsch = self._settle(nas, methods, actie, prop, verwachte_image)
        except Exception:  # NasFout of een onverwacht antwoord bij het teruglezen: uitkomst onbekend
            return self._stop(request_id, nonce, actie, methode, doel, None, "uitkomst_onbekend", [])
        if mislukt is not None:
            # 502 alleen als TrueNAS de aanroep zelf weigerde of de job FAILED/ABORTED meldde, en het doel aantoonbaar
            # onveranderd is (R-TECH-1).
            if mislukt.code in ONBEKENDE_UITKOMST or na.hash != doel.hash:
                return self._stop(request_id, nonce, actie, methode, doel, na, "uitkomst_onbekend", [])
            self.journal.finish(nonce, status="mislukt", after_hash=na.hash, detail=journaal_detail(mislukt))
            return fout(
                502,
                "uitvoering_mislukt",
                "TrueNAS heeft de actie niet uitgevoerd; de toestand van het doel is onveranderd.",
                {
                    "reden": mislukt.code,
                    "request_id": request_id,
                    "methode": methode,
                    "before_hash": doel.hash,
                    "after_hash": na.hash,
                },
            )
        if afw:
            return self._stop(request_id, nonce, actie, methode, doel, na, str(afw[0]["code"]), afw)
        extra: dict[str, Any] = {}
        if herkomst is not None and methode == "app.update":
            # De datasets van het recept dat deze actie bewaarde: de Hub vraagt bij het terugzetten ook daarvoor een
            # snapshot (R-HARDE-EIS-4). Alleen namen van datasets, nooit een waarde uit de configuratie.
            na.readback = {**na.readback, "herstel_datasets": herkomst.get("herstel_datasets")}
        if gemeld is not None:
            extra["herkomst"] = gemeld  # oud of buiten_keten: zichtbaar, het terugzetten ging door (ADR-0032 besluit 8)
        if actie.action_id == "zfs.snapshot.create":
            # Een geslaagde, teruggelezen snapshot is een checkpoint (S-P2-050f). Lukt vastleggen niet, dan blijft de
            # snapshot gewoon staan, maar telt hij niet als checkpoint (zichtbaar als waarschuwing).
            txg = na.readback.get("createtxg")
            try:
                if not txg or not na.readback.get("aanwezig"):
                    raise JournalUnavailable("createtxg")
                leden, recursief = self._checkpoint_leden(nas, methods, doel.naam, prop, str(txg))
                self.journal.leg_checkpoint_vast(
                    request_id, doel.naam, str(na.readback["snapshot"]), str(txg), recursief, leden
                )
                na.readback = {**na.readback, "leden": leden, "recursief": recursief}
            except (JournalUnavailable, NasFout):
                waarsch = [*waarsch, CHECKPOINT_NIET_VASTGELEGD]
        if hercontrole is not None:
            # Alleen melden (KLEIN-85): codes en aantal, nooit een waarde; zonder overtreding verandert er niets.
            waarsch = [*waarsch, HERCONTROLE_WAARSCHUWING]
            extra["hercontrole"] = dict(hercontrole)
            self.journal.finish(
                nonce,
                status="uitgevoerd",
                after_hash=na.hash,
                detail=f"{HERCONTROLE_WAARSCHUWING}: {','.join(hercontrole['codes'])}",
            )
        else:
            self.journal.finish(nonce, status="uitgevoerd", after_hash=na.hash)
        return Uitkomst(
            200,
            {
                "status": "uitgevoerd",
                "request_id": request_id,
                "nonce": nonce,
                "action_id": actie.action_id,
                "target": dict(prop["target"]),
                "methode": methode,
                "before_hash": doel.hash,
                "after_hash": na.hash,
                "resource_etag": na.etag,
                "readback": na.readback,
                "waarschuwingen": waarsch,
                "policy_hash": self.policy.hash,
                "uitgevoerd_op": iso(datetime.now(UTC)),
                **extra,
            },
        )
