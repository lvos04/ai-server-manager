"""Runbooks als Markdown (``docs/RUNBOOKS.md``) uit de getypeerde catalogus; ``--check`` faalt bij drift."""

from __future__ import annotations

import sys
from pathlib import Path

from hub.runbooks.catalogus import FASEN, NA_STOP_GEWEIGERD, RUNBOOKS, runbook_hash

FASE_TITEL = {
    "observeren": "Observeren",
    "isoleren": "Isoleren",
    "mitigeren": "Mitigeren",
    "terugdraaien": "Terugdraaien",
    "bewijs": "Bewijs verzamelen",
    "oorzaak": "Oorzaak vastleggen",
}
SOORT = {"lezen": "Hub toont", "handmatig": "Zelf doen", "voorstel": "Voorstel"}


def render() -> str:
    lines = [
        "# Stappenplannen (B09-006)",
        "",
        "Gegenereerd uit `apps/api/src/hub/runbooks/catalogus.py` (`python -m hub export-runbooks`); niet met de hand",
        f"bewerken. `runbook_hash`: `{runbook_hash()}`.",
        "",
        "Elke stap is getypeerd: **Hub toont** (alleen lezen), **Zelf doen** (in een bestaande UI, nooit een",
        "terminal) of **Voorstel** (een actie uit de lijst met toegestane acties van de executor, contract §8, met",
        "minimale risicoklasse; de Hub voert niets zelf uit — uitvoering via policy-engine, goedkeuring en executor",
        "volgt in P2). Veilige modus: faalt een incident telkens opnieuw, dan stelt de Hub geen herstart meer voor.",
        "",
    ]
    for r in RUNBOOKS:
        vm = r.veilige_modus
        lines += [f"## {r.titel} (`{r.id}`)", "", r.scenario, ""]
        for fase in FASEN:
            lines.append(f"**{FASE_TITEL[fase]}**")
            lines.append("")
            for s in r.stappen()[fase]:
                extra = ""
                if s.action_id:
                    klasse = f"minimaal {s.risico}"
                    if s.custom_app == NA_STOP_GEWEIGERD:
                        klasse += "; het platform weigert dit bij een gestopte Custom App"
                    elif s.custom_app is not None:
                        klasse += f"; Custom App: {s.custom_app}"
                    extra = f" — `{s.action_id}` ({klasse})"
                elif s.bron:
                    extra = f" — `{s.bron}`"
                lines.append(f"- {SOORT[s.soort]}: {s.tekst}{extra}")
            lines.append("")
        lines.append("**Test na herstel** (niet alleen 'poort open')")
        lines.append("")
        lines += [f"- {t}" for t in r.test_na_herstel]
        lines += ["", f"Veilige modus na {vm.max_herhalingen}× opnieuw falen binnen {vm.venster_s // 60} min.", ""]
    return "\n".join(lines).rstrip() + "\n"


def export(out: Path, *, check: bool = False) -> int:
    text = render()
    if check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print(
                f"Runbook-drift: {out} is niet actueel. Draai `make runbooks` en commit het resultaat.", file=sys.stderr
            )
            return 1
        print(f"{out} is actueel")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"geschreven: {out}")
    return 0
