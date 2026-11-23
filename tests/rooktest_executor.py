"""HTTP-proef in de tijdelijke executor als Custom User 568, zonder netwerkverbinding of NAS-schrijfsleutel."""

from __future__ import annotations

import json
import uuid
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

from asm_policy import load_policy
from executorhub import Hub
from policyhelpers import HOST, approval_for, execution_request, install_params, proposal


def weigering(hub: Hub, verzoek: dict[str, Any], status: int, code: str) -> dict[str, Any]:
    verbinding = HTTPConnection("localhost", hub.settings.port, timeout=10)
    try:
        verbinding.request(
            "POST",
            "/api/v1/execute",
            json.dumps(verzoek),
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {hub.jwt()}",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        antwoord = verbinding.getresponse()
        inhoud = json.load(antwoord)
    finally:
        verbinding.close()
    if antwoord.status != status or inhoud.get("code") != code:
        raise SystemExit(f"FOUT: verwacht HTTP {status} met {code}, ontvangen HTTP {antwoord.status}")
    return inhoud["details"]


def main() -> None:
    hub = Hub(Path("/appdata"))
    beleid = load_policy().hash
    voorstel = proposal("app.install", {"host_id": HOST, "app_id": "demo-app"}, install_params(privileged=True))
    akkoord = approval_for(voorstel, policy_hash=beleid, risk_class="R2")
    verzoek = execution_request(hub.policy_key, voorstel, risk_class="R2", policy_hash=beleid, approval=akkoord)
    zonder = verzoek.copy()
    del zonder["signature"]
    fouten = weigering(hub, zonder, 422, "execution_request_ongeldig")["fouten"]
    if {f["veld"] for f in fouten} != {"signature"}:
        raise SystemExit("FOUT: de executor wees niet uitsluitend het ontbrekende handtekeningveld af")
    print("ok: executor weigert een aangemeld uitvoeringsverzoek zonder handtekening (HTTP 422, veld signature)")
    weigering(hub, {**verzoek, "signature": ""}, 403, "handtekening_ongeldig")
    fouten = weigering(hub, verzoek, 422, "parameters_ongeldig")["fouten"]
    if "privileged_verboden" not in {f["code"] for f in fouten}:
        raise SystemExit("FOUT: de executor herkent de verboden installatieoptie niet")
    print("ok: ook met geldige handtekening en gebonden goedkeuring weigert de executor privileged (EX47)")


if __name__ == "__main__":
    main()
