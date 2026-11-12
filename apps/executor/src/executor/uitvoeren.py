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
   de Hub legt een incident vast.

Nooit ``custom_compose_config``, nooit een methode buiten het beleid, nooit data verwijderen
(``app.delete`` met ``remove_ix_volumes: false``).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from asm_policy import etag as etags
from asm_policy.canonical import canonical_sha256
from asm_policy.engine import herken_app, recognize_all
from asm_policy.execreq import iso
from asm_policy.loader import ActieDef, Policy
from asm_policy.params import IX_APP, expected_image, vault_refs, verwachte_catalogus
from asm_policy.verify import Weigering, check_decision, check_envelope
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from executor.journal import Journal, JournalUnavailable
from executor.naslink import NasLinkOnleesbaar, NasLinkStore
from executor.truenas import NasClient, NasFout

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
    """Alle pools ``ONLINE`` en ``healthy``. Geen pools of een onverwacht antwoord = onbekend = niet gezond (EX11)."""
    rows = [p for p in pools if isinstance(p, dict)] if isinstance(pools, list) else []
    beeld = [{"pool": str(p.get("name")), "status": str(p.get("status")), "healthy": p.get("healthy")} for p in rows]
    ok = bool(rows) and all(p.get("status") == "ONLINE" and p.get("healthy") is True for p in rows)
    return ok, beeld


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
    ) -> None:
        self.policy, self.journal, self.naslink = policy, journal, naslink
        self.settle_seconds, self.poll_seconds, self.timeout = settle_seconds, poll_seconds, timeout
        self.write_methods = frozenset(
            m for a in policy.acties.values() if a.uitvoerder == "executor" for m in a.truenas
        )
        # Eén uitvoering tegelijk: twee goedgekeurde verzoeken op hetzelfde doel mogen elkaars readback niet kruisen.
        self._bezig = threading.Lock()

    # ------------------------------------------------------------------ readback
    def _snapshot_query(self, nas: NasClient, methods: frozenset[str], dataset: str) -> list[str]:
        method = next((m for m in ("pool.snapshot.query", "zfs.snapshot.query") if m in methods), None)
        if method is None:
            raise NasFout("capability_unavailable", "snapshot.query")
        rows = nas.call(method, [["dataset", "=", dataset]])
        names = [str(r.get("name")) for r in rows or [] if isinstance(r, dict)]
        return sorted(n for n in names if n.split("@", 1)[0] == dataset)

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
            snaps = self._snapshot_query(nas, methods, ds)
            full = f"{ds}@{prop['parameters'].get('naam')}"
            return Doel(
                "dataset",
                ds,
                etags.dataset_etag(ds),
                _dataset_exists(tree, ds),
                canonical_sha256({"dataset": ds, "snapshots": snaps}),
                readback={"snapshot": full, "aanwezig": full in snaps},
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
        if aid == "app.install" and vault_refs(params):
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

    def _voer_uit(
        self, nas: NasClient, methode: str, actie: ActieDef, prop: Mapping[str, Any], doel: Doel, request_id: str
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
                "values": ac["values"],
            }
            nas.job(methode, body, timeout=t, poll=self.poll_seconds)
        elif aid == "app.uninstall":
            # Container-only: datasets, ix-volumes en images blijven (B01-003; nooit data verwijderen).
            nas.job(
                methode, name, {"remove_images": False, "remove_ix_volumes": False}, timeout=t, poll=self.poll_seconds
            )
        elif aid in ("app.update", "app.rollback") and methode == "app.update":
            vorige = nas.call("app.config", name)
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
            self.journal.save_values(request_id, name, vorige)
            nas.job(methode, name, {"values": values}, timeout=t, poll=self.poll_seconds)
        elif aid == "app.update":
            nas.job(methode, name, {"app_version": params["catalog_version"]}, timeout=t, poll=self.poll_seconds)
        elif aid == "app.rollback":
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
        if not self.journal.claim_request_nonce(nonce):
            return fout(
                409, "nonce_al_gebruikt", "Dit uitvoeringsverzoek is al eens aangeboden; er is niets uitgevoerd."
            )
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
            if actie.action_id == "app.rollback" and "herstel_van" in prop["parameters"]:
                if bewaard is None or bewaard[0] != doel.naam:
                    return fout(
                        409,
                        "herstelpunt_onbekend",
                        "De executor heeft geen vorige waarden van deze app bij die wijziging; er is niets teruggezet.",
                    )
                oud = bewaard[1].get("image") if isinstance(bewaard[1].get("image"), dict) else None
                if oud:
                    versie, _s, in_tag = str(oud.get("tag") or "").partition("@")
                    verwachte_image = {
                        "repository": str(oud.get("repository") or ""),
                        "tag": str(oud.get("tag") or ""),
                        "versie": versie,
                        "digest": in_tag or None,
                    }
            if isinstance(approval, Mapping) and not self.journal.claim_approval_nonce(
                str(approval["one_time_nonce"]), str(approval["approval_id"])
            ):
                return fout(409, "goedkeuring_al_gebruikt", "Deze goedkeuring is al eens gebruikt; keur opnieuw goed.")
            self.journal.begin(
                request_id=request_id,
                nonce=nonce,
                action_id=actie.action_id,
                target=dict(prop["target"]),
                methode=methode,
                before_hash=doel.hash,
            )
            return self._uitvoeren_en_teruglezen(
                nas, methods, methode, actie, prop, doel, request_id, nonce, verwachte_image
            )
        finally:
            nas.close()

    def _stop(
        self, request_id: str, nonce: str, actie: ActieDef, methode: str, doel: Doel, na: Doel | None, code: str,
        afwijkingen: list[dict[str, Any]],
    ) -> Uitkomst:  # fmt: skip
        after = na.hash if na else None
        self.journal.finish(nonce, status="afwijking", after_hash=after, detail=code)
        self.journal.stop(
            {"code": code, "request_id": request_id, "action_id": actie.action_id, "at": iso(datetime.now(UTC))}
        )
        return fout(
            409,
            "afwijking",
            "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt en voert "
            "niets meer uit tot een beheerder hem vrijgeeft.",
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
    ) -> Uitkomst:
        mislukt: NasFout | None = None
        try:
            self._voer_uit(nas, methode, actie, prop, doel, request_id)
        except NasFout as exc:
            mislukt = exc
        try:
            return self._teruglezen(
                nas, methods, methode, actie, prop, doel, request_id, nonce, verwachte_image, mislukt
            )
        except JournalUnavailable:
            # Na de aanroep bij TrueNAS kan "er is niets uitgevoerd" niet meer worden beloofd.
            return fout(
                409,
                "afwijking",
                "De actie is naar TrueNAS gestuurd, maar het journaal van de executor is niet beschikbaar: de uitkomst "
                "is niet vastgelegd. De executor voert niets meer uit tot het journaal weer werkt.",
                {
                    "reden": "journaal_niet_beschikbaar",
                    "afwijkingen": [],
                    "request_id": request_id,
                    "action_id": actie.action_id,
                    "methode": methode,
                    "before_hash": doel.hash,
                    "after_hash": None,
                    "gestopt": False,
                },
            )

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
    ) -> Uitkomst:
        try:
            if mislukt is not None:
                na = self._lees(nas, methods, actie, prop)
                afw: list[dict[str, Any]] = []
                waarsch: list[str] = []
            else:
                na, afw, waarsch = self._settle(nas, methods, actie, prop, verwachte_image)
        except NasFout:
            return self._stop(request_id, nonce, actie, methode, doel, None, "uitkomst_onbekend", [])
        if mislukt is not None:
            if mislukt.code in ("job_timeout", "truenas_timeout", "truenas_onbereikbaar") or na.hash != doel.hash:
                return self._stop(request_id, nonce, actie, methode, doel, na, "uitkomst_onbekend", [])
            self.journal.finish(nonce, status="mislukt", after_hash=na.hash, detail=f"{mislukt.code}: {mislukt.detail}")
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
            },
        )
