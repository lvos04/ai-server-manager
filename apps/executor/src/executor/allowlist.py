"""Allowlist van de executor. Fase P0: **leeg** — elke actie wordt geweigerd.

De allowlist v1 uit contract §8 (``app.restart``, ``app.install``, ``zfs.snapshot.create`` …) wordt pas in fase P2
toegevoegd, samen met handtekening-, nonce-, policy-hash- en readbackcontroles. Er bestaat nooit een ``shell.exec``,
``sudo`` of ``docker.*``-actie.
"""

from __future__ import annotations

from dataclasses import dataclass

ALLOWLIST: frozenset[str] = frozenset()
NEVER_ALLOWED_PREFIXES: tuple[str, ...] = ("shell.", "sudo", "docker.", "exec", "system.shell")


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    code: str
    message: str


def check(action_id: str) -> Verdict:
    if any(action_id.lower().startswith(p) for p in NEVER_ALLOWED_PREFIXES):
        return Verdict(False, "action_forbidden", f"'{action_id}' is nooit toegestaan (geen shell, sudo of Docker).")
    if action_id not in ALLOWLIST:
        return Verdict(
            False,
            "action_not_allowed",
            f"'{action_id}' staat niet op de allowlist. In deze versie is de allowlist leeg: de executor is nog niet "
            "gekoppeld en voert niets uit.",
        )
    return Verdict(True, "allowed", "")  # pragma: no cover — onbereikbaar zolang ALLOWLIST leeg is
