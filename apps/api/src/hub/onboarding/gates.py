"""Gates: afgeleid uit besluiten D01–D18 + gemeten toestand. Wat niet aantoonbaar groen is, is dicht.

Status per gate: ``toegestaan`` | ``geblokkeerd`` | ``unknown``. ``unknown`` (bv. verouderde meting) telt nooit als
groen.
Een gate kan in deze fase niet door een gebruiker worden 'weggeklikt' (B12-006): er is geen override-endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hub.timeutil import iso, utcnow

_RANK = {"Open": 0, "Geblokkeerd": 0, "N.v.t.": 0, "Ingevuld": 1, "Getest": 2}


@dataclass(frozen=True)
class GateDef:
    id: str
    naam: str
    besluiten: tuple[tuple[str, str], ...] = ()  # (besluit, minimale status)
    checks: tuple[str, ...] = ()  # executor | pools_gezond | eigen_backup
    gates: tuple[str, ...] = ()  # afhankelijke gates


GATES: tuple[GateDef, ...] = (
    GateDef("connector_bouw", "Connectoren bouwen tegen de echte NAS", (("D01", "Getest"),)),
    GateDef("mount_backup", "Mounts en back-upconfiguratie", (("D02", "Getest"),)),
    GateDef(
        "deployment",
        "Apps installeren (deploy)",
        (("D01", "Getest"), ("D02", "Getest"), ("D03", "Getest")),
        ("executor",),
    ),
    GateDef(
        "backup_gate", "Back-upgate", (("D04", "Ingevuld"), ("D05", "Getest"), ("D16", "Ingevuld")), ("eigen_backup",)
    ),
    GateDef(
        "data_mutatie",
        "Data-mutaties (opslag, datasets, massamedia)",
        (("D06", "Getest"),),
        ("pools_gezond",),
        ("backup_gate",),
    ),
    GateDef(
        "bestaande_app_updates",
        "Updates van bestaande apps",
        (("D05", "Getest"), ("D07", "Getest")),
        (),
        ("backup_gate",),
    ),
    GateDef(
        "upgrades",
        "Upgrades (nieuwe versies uitrollen)",
        (("D07", "Getest"),),
        (),
        ("backup_gate", "data_mutatie", "deployment"),
    ),
    GateDef("gpu_transcode", "GPU-transcode en mediaserverfork", (("D08", "Getest"),)),
    GateDef("ai_cloud", "AI-agent met cloudmodel (alleen inbegrepen tegoed)", (("D09", "Getest"),)),
    GateDef("dns_cutover", "DNS-cutover (AdGuard)", (("D11", "Getest"),)),
    GateDef("gree_aansturing", "Gree-airco aansturen", (("D12", "Getest"),)),
    GateDef("zigbee_installatie", "Zigbee installeren", (("D13", "Getest"),)),
    GateDef("energie_dashboard_exact", "Exact energiedashboard", (("D14", "Getest"),)),
    GateDef("mediaserver_cutover", "Mediaserver-cutover", (("D15", "Getest"),)),
    GateDef("restore_policy", "Herstelbeleid (RPO/RTO)", (("D16", "Ingevuld"),)),
    GateDef("authentik", "Authentik/OIDC", (("D17", "Getest"),)),
    GateDef("navidrome", "Navidrome (optioneel)", (("D18", "Ingevuld"),)),
    GateDef("r2_r3_acties", "R2/R3-acties (met goedkeuring)", (), ("executor",), ("backup_gate", "data_mutatie")),
)


@dataclass
class GateInputs:
    decisions: dict[str, tuple[str, Any]]  # id -> (status, waarde)
    pools_state: dict[str, Any]  # kind_state("pools")
    eigen_backup: dict[str, Any] | None  # laatste geverifieerde eigen back-up {finished_at, sha256} of None
    eigen_backup_max_age_seconds: int
    executor_gekoppeld: bool = False
    now: datetime = field(default_factory=utcnow)


def _decision_reason(did: str, status: str, needed: str) -> dict[str, Any] | None:
    if _RANK.get(status, 0) >= _RANK[needed]:
        return None
    extra = {"N.v.t.": " (N.v.t. opent nooit een gate)", "Geblokkeerd": " (geblokkeerd)"}.get(status, "")
    return {
        "soort": "besluit",
        "id": did,
        "status": "geblokkeerd",
        "tekst": f"{did} is {status}; nodig: {needed}{extra}.",
    }


def _check(name: str, inp: GateInputs) -> dict[str, Any] | None:
    if name == "executor":
        if inp.executor_gekoppeld:
            return None
        return {
            "soort": "executor",
            "id": "executor",
            "status": "geblokkeerd",
            "tekst": "De executor is nog niet gekoppeld (koppelen volgt in fase P2).",
        }
    if name == "pools_gezond":
        st = inp.pools_state
        if st.get("status") != "ok":
            return {
                "soort": "meting",
                "id": "pools",
                "status": "unknown",
                "tekst": f"Poolstatus onbekend ({st.get('reason_code') or 'onbekend'}); "
                "onbekend telt nooit als gezond.",
            }
        pools = st.get("data") or []
        if not pools:
            return {"soort": "meting", "id": "pools", "status": "unknown", "tekst": "Geen pools gemeten."}
        bad = [str(p.get("naam")) for p in pools if p.get("gezond") is not True]
        if bad:
            return {
                "soort": "meting",
                "id": "pools",
                "status": "geblokkeerd",
                "tekst": f"Pool niet gezond: {', '.join(bad)} (EX11: geen opslag-/datamutaties).",
            }
        return None
    if name == "eigen_backup":
        b = inp.eigen_backup
        if not b or not b.get("finished_at"):
            return {
                "soort": "meting",
                "id": "eigen_backup",
                "status": "geblokkeerd",
                "tekst": "Er is nog geen geverifieerde back-up van de Hub-database.",
            }
        finished: datetime = b["finished_at"]
        if (inp.now - finished).total_seconds() > inp.eigen_backup_max_age_seconds:
            return {
                "soort": "meting",
                "id": "eigen_backup",
                "status": "geblokkeerd",
                "tekst": f"Laatste geverifieerde Hub-back-up is te oud ({iso(finished)}).",
            }
        return None
    raise ValueError(name)


def evaluate(inp: GateInputs) -> list[dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for g in GATES:  # volgorde zorgt dat afhankelijke gates al berekend zijn
        reasons: list[dict[str, Any]] = []
        for did, needed in g.besluiten:
            status, _ = inp.decisions.get(did, ("Open", None))
            r = _decision_reason(did, status, needed)
            if r:
                reasons.append(r)
        for c in g.checks:
            r = _check(c, inp)
            if r:
                reasons.append(r)
        for dep in g.gates:
            dres = results[dep]
            if dres["status"] != "toegestaan":
                reasons.append(
                    {
                        "soort": "gate",
                        "id": dep,
                        "status": dres["status"],
                        "tekst": f"Afhankelijke gate '{dep}' is {dres['status']}.",
                    }
                )
        if any(r["status"] == "geblokkeerd" for r in reasons):
            status = "geblokkeerd"
        elif reasons:
            status = "unknown"
        else:
            status = "toegestaan"
        results[g.id] = {
            "id": g.id,
            "naam": g.naam,
            "status": status,
            "toegestaan": status == "toegestaan",
            "redenen": reasons,
            "vereist": {
                "besluiten": [{"id": d, "minimaal": s} for d, s in g.besluiten],
                "metingen": list(g.checks),
                "gates": list(g.gates),
            },
            "afgeleid_op": iso(inp.now),
        }
    return [results[g.id] for g in GATES]
